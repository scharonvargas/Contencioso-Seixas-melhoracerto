"""
src/services/process_service.py
Serviço orquestrador do ciclo de vida de Processos Judiciais, Avaliação e Auditoria.
Executa a esteira documental real e avalia contra as regras da norma ativa no banco.
"""

import re
from typing import Dict, Any, Optional, List
import fitz
from sqlalchemy.orm import Session
from src.models.entities import Process, DocumentPage, ExtractedFact, Evidence, Evaluation, PolicyVersion, generate_uuid
from src.ingestion.quality_assessor import PageQualityAssessor
from src.ocr.cascade_engine import OCRCascadeEngine
from src.segmentation.segmenter import DocumentSegmenter
from src.extraction.evidence_grounding import EvidenceGroundingValidator
from src.extraction.llm_client import OpenRouterExtractionClient
from src.rule_engine.deterministic_engine import DeterministicRuleEngine
from src.validators.brazilian_validators import BrazilianDomainValidator
from src.core.storage import storage_service

class ProcessExecutionService:
    """
    Executa a esteira completa para um processo judicial e persiste todos os artefatos no banco.
    """

    def __init__(self, db: Session):
        self.db = db
        self.ocr_engine = OCRCascadeEngine()

    def process_and_evaluate(
        self,
        tenant_id: str,
        process_id: str,
        pdf_bytes: bytes,
        filename: str = "autos.pdf"
    ) -> Dict[str, Any]:
        return self.process_and_evaluate_multi(
            tenant_id=tenant_id,
            process_id=process_id,
            pdf_files=[{"bytes": pdf_bytes, "filename": filename}]
        )

    def process_and_evaluate_multi(
        self,
        tenant_id: str,
        process_id: str,
        pdf_files: List[Dict[str, Any]]
    ) -> Dict[str, Any]:
        """
        Recebe múltiplos arquivos PDF que compõem o processo judicial,
        processa todas as páginas em um fluxo unificado e cruza as evidências extraídas.
        """
        # Limpa páginas e avaliações antigas se este processo já tiver sido processado antes
        self.db.query(DocumentPage).filter(DocumentPage.process_id == process_id).delete()
        self.db.query(Evaluation).filter(Evaluation.process_id == process_id).delete()
        fact_ids = [f.id for f in self.db.query(ExtractedFact).filter(ExtractedFact.process_id == process_id).all()]
        if fact_ids:
            self.db.query(Evidence).filter(Evidence.fact_id.in_(fact_ids)).delete(synchronize_session=False)
        self.db.query(ExtractedFact).filter(ExtractedFact.process_id == process_id).delete()
        self.db.commit()

        processed_pages = []
        documents_summary = []
        global_page_num = 0

        from src.core.trace_logger import ProcessTraceLogger
        trace = ProcessTraceLogger(tenant_id=tenant_id, process_id=process_id)
        trace.log("FASE_1_INGESTAO_OCR", f"Iniciando ingestão de {len(pdf_files)} arquivo(s) PDF para o processo {process_id}.")

        for doc_idx, file_item in enumerate(pdf_files):
            pdf_bytes = file_item["bytes"]
            filename = file_item.get("filename", f"documento_{doc_idx + 1}.pdf")

            # 1. Salva cada PDF no storage
            storage_path = storage_service.save_process_pdf(tenant_id, process_id, pdf_bytes, filename)
            doc_size_kb = len(pdf_bytes) / 1024

            # 2. Ingestão e OCR de cada página do documento
            doc = fitz.open(stream=pdf_bytes, filetype="pdf")
            doc_page_count = len(doc)
            documents_summary.append({
                "document_index": doc_idx + 1,
                "filename": filename,
                "pages_count": doc_page_count
            })
            trace.log("FASE_1_INGESTAO_OCR", f"Arquivo [{doc_idx + 1}/{len(pdf_files)}] '{filename}' carregado ({doc_size_kb:.1f} KB, {doc_page_count} páginas).")

            for page_in_doc_idx, page in enumerate(doc):
                global_page_num += 1
                page_in_doc = page_in_doc_idx + 1
                res = self.ocr_engine.process_page(page, page_number=global_page_num)
                res["document_name"] = filename
                res["page_in_document"] = page_in_doc
                
                # Classifica a peça processual da página
                seg_type = DocumentSegmenter.classify_page(res.get("raw_text", ""))
                res["segment_type"] = seg_type.value if hasattr(seg_type, "value") else str(seg_type)
                processed_pages.append(res)

                trace.log(
                    "FASE_1_INGESTAO_OCR",
                    f"Pág {global_page_num} ({filename} p.{page_in_doc}): OCR {res['tier']} (Confiança: {res['mean_confidence']:.2f}, {len(res.get('raw_text', ''))} caracteres extraídos).",
                    details={"tier": res["tier"], "quality_score": res["mean_confidence"], "segment": res["segment_type"]}
                )

                # Persiste os dados e texto completo de cada página no banco
                page_record = DocumentPage(
                    id=generate_uuid(),
                    tenant_id=tenant_id,
                    process_id=process_id,
                    page_number=global_page_num,
                    document_name=filename,
                    page_in_document=page_in_doc,
                    segment_type=res["segment_type"],
                    raw_text=res.get("raw_text", ""),
                    words_data=res.get("words_data", []),
                    has_native_text=(res["tier"] == "TIER_0_NATIVE"),
                    quality_score=res["mean_confidence"],
                    image_storage_path=f"pages/{tenant_id}/{process_id}/page_{global_page_num}.png"
                )
                self.db.add(page_record)

        total_pages = len(processed_pages)
        trace.complete_phase("FASE_1_INGESTAO_OCR", "COMPLETED", {"total_pages": total_pages, "total_files": len(pdf_files)})

        # 3. Segmentação Unificada de Documentos
        trace.log("FASE_2_SEGMENTACAO_PECAS", f"Segmentando {total_pages} páginas em peças processuais...")
        segments = DocumentSegmenter.segment_process_pages(processed_pages)
        seg_counts = {}
        for p in processed_pages:
            st = p.get("segment_type", "OUTROS")
            seg_counts[st] = seg_counts.get(st, 0) + 1
        trace.complete_phase("FASE_2_SEGMENTACAO_PECAS", "COMPLETED", {"segments_distribution": seg_counts})

        # 4. Recupera a Norma ACTIVE exclusivamente para este tenant no banco
        active_policy_version = (
            self.db.query(PolicyVersion)
            .filter(PolicyVersion.tenant_id == tenant_id, PolicyVersion.status == "ACTIVE")
            .order_by(PolicyVersion.activated_at.desc(), PolicyVersion.created_at.desc())
            .first()
        )

        if not active_policy_version:
            trace.log("FASE_4_CLASSIFICACAO_TEMA", f"Erro crítico: Nenhuma norma ativa cadastrada para o tenant '{tenant_id}'.", level="ERROR")
            raise ValueError(f"Nenhuma norma ou manual de acordos ativo cadastrado para o tenant '{tenant_id}'.")

        trace.log("FASE_4_CLASSIFICACAO_TEMA", f"Norma Ativa Carregada: {active_policy_version.version} (ID: {active_policy_version.id}).")

        # 5. Extração e Cruzamento Profundo de Fatos entre todos os PDFs baseada na norma ativa
        case_facts = self._extract_facts(processed_pages, tenant_id, process_id, structured_rules=active_policy_version.structured_rules, trace=trace)

        # 5.1 Persiste fatos estruturados e evidências no banco de dados para rastreabilidade forense
        theme_fact_id = generate_uuid()
        self.db.add(ExtractedFact(
            id=theme_fact_id,
            tenant_id=tenant_id,
            process_id=process_id,
            fact_category="ADMINISTRATIVE",
            fact_key="identified_theme",
            fact_value={"theme": case_facts.get("identified_theme", "Geral"), "applicable_topic_num": case_facts.get("applicable_topic_num")},
            normalized_value=str(case_facts.get("identified_theme", "Geral")),
            extraction_confidence=1.0
        ))

        fin_fact_id = generate_uuid()
        self.db.add(ExtractedFact(
            id=fin_fact_id,
            tenant_id=tenant_id,
            process_id=process_id,
            fact_category="FINANCIAL",
            fact_key="requested_amount",
            fact_value=case_facts.get("financial", {}),
            normalized_value=str(case_facts.get("financial", {}).get("requested_amount", 0.0)),
            extraction_confidence=1.0
        ))

        treat_fact_id = generate_uuid()
        self.db.add(ExtractedFact(
            id=treat_fact_id,
            tenant_id=tenant_id,
            process_id=process_id,
            fact_category="MEDICAL",
            fact_key="treatment",
            fact_value=case_facts.get("treatment", {}),
            normalized_value=str(case_facts.get("treatment", {}).get("cid_10") or "SEM_CID"),
            extraction_confidence=1.0
        ))

        admin_fact_id = generate_uuid()
        self.db.add(ExtractedFact(
            id=admin_fact_id,
            tenant_id=tenant_id,
            process_id=process_id,
            fact_category="ADMINISTRATIVE",
            fact_key="administrative_denial",
            fact_value=case_facts.get("administrative_denial", {}),
            normalized_value=str(case_facts.get("administrative_denial", {}).get("has_administrative_denial", False)),
            extraction_confidence=1.0
        ))

        # Adiciona evidências vinculadas reais
        for fact_item_id, fact_info in [
            (fin_fact_id, case_facts.get("financial", {})),
            (treat_fact_id, case_facts.get("treatment", {})),
            (admin_fact_id, case_facts.get("administrative_denial", {}))
        ]:
            ev_data = fact_info.get("evidence")
            if ev_data and isinstance(ev_data, dict) and ev_data.get("page_number"):
                self.db.add(Evidence(
                    id=generate_uuid(),
                    tenant_id=tenant_id,
                    fact_id=fact_item_id,
                    page_number=ev_data["page_number"],
                    bounding_box=ev_data.get("bounding_box", [0.0, 0.0, 1.0, 1.0]),
                    exact_text_snippet=ev_data.get("exact_text_snippet", "") or ev_data.get("text_snippet", ""),
                    ocr_engine_used=ev_data.get("ocr_engine_used", "TIER_0_NATIVE"),
                    confidence_score=ev_data.get("confidence_score", 1.0)
                ))

        # 6. Avaliação Determinística (JSON-Logic Rule Engine)
        trace.log("FASE_5_AVALIACAO_REGRAS", f"Iniciando avaliação determinística no motor JSON-Logic contra {len(active_policy_version.structured_rules.get('rules', []))} regras da norma...")
        rule_engine = DeterministicRuleEngine(active_policy_version.structured_rules)
        decision_result = rule_engine.evaluate(process_id=process_id, case_fact_data=case_facts)

        for rr in decision_result.rule_results:
            lvl = "SUCCESS" if rr.status == "PASS" else ("ERROR" if rr.status == "FAIL" else "WARNING")
            trace.log(
                "FASE_5_AVALIACAO_REGRAS",
                f"Regra [{rr.rule_code}] '{rr.title}' -> {rr.status}" + (f" | Motivo: {rr.failure_reason}" if rr.failure_reason else ""),
                level=lvl,
                details={"rule_code": rr.rule_code, "status": rr.status, "failure_reason": rr.failure_reason}
            )

        trace.complete_phase("FASE_5_AVALIACAO_REGRAS", "COMPLETED", {
            "total_rules": len(decision_result.rule_results),
            "passed": sum(1 for r in decision_result.rule_results if r.status == "PASS"),
            "failed": sum(1 for r in decision_result.rule_results if r.status == "FAIL"),
            "unknown": sum(1 for r in decision_result.rule_results if r.status == "UNKNOWN")
        })

        # 7. Persiste a Avaliação e Decisão Final
        trace.log("FASE_6_VEREDITO_FINAL", f"Veredito Final Consolidado: {decision_result.overall_verdict} — {decision_result.summary}")
        trace.complete_phase("FASE_6_VEREDITO_FINAL", "COMPLETED", {
            "verdict": decision_result.overall_verdict,
            "summary": decision_result.summary
        })

        # Salva o arquivo de log forense em disco
        trace_json_path = trace.save_to_disk()
        trace_dict = trace.to_dict()

        evaluation_record = Evaluation(
            id=generate_uuid(),
            tenant_id=tenant_id,
            process_id=process_id,
            policy_version_id=active_policy_version.id,
            overall_result=decision_result.overall_verdict,
            total_rules_evaluated=len(decision_result.rule_results),
            rules_passed=sum(1 for r in decision_result.rule_results if r.status == "PASS"),
            rules_failed=sum(1 for r in decision_result.rule_results if r.status == "FAIL"),
            rules_unknown=sum(1 for r in decision_result.rule_results if r.status == "UNKNOWN"),
            decision_summary=decision_result.summary,
            rules_results=[r.model_dump() for r in decision_result.rule_results],
            execution_trace=trace_dict
        )
        self.db.add(evaluation_record)

        # Se exigir revisão humana ou falha técnica, cria registro persistente em HumanReview
        if decision_result.overall_verdict in ["REQUIRES_HUMAN_REVIEW", "TECHNICAL_FAILURE"]:
            from src.models.entities import HumanReview
            reason_str = "MISSING_EVIDENCE"
            if decision_result.overall_verdict == "TECHNICAL_FAILURE":
                reason_str = "TECHNICAL_FAILURE"
            elif any(r.status == "UNKNOWN" and "Evidência documental" in (r.failure_reason or "") for r in decision_result.rule_results):
                reason_str = "MISSING_EVIDENCE"
            elif any(r.status == "UNKNOWN" for r in decision_result.rule_results):
                reason_str = "RULE_EVALUATION_UNKNOWN"

            human_review = HumanReview(
                id=generate_uuid(),
                tenant_id=tenant_id,
                process_id=process_id,
                evaluation_id=evaluation_record.id,
                status="OPEN",
                review_reason=reason_str
            )
            self.db.add(human_review)

        # Atualiza status do Processo
        process_record = self.db.query(Process).filter(Process.id == process_id).first()
        if process_record:
            process_record.status = (
                "EVALUATED" if decision_result.overall_verdict not in ["REQUIRES_HUMAN_REVIEW", "TECHNICAL_FAILURE"] else "REQUIRES_HUMAN_REVIEW"
            )
            process_record.total_pages = total_pages

        self.db.commit()


        # Monta lista de páginas com dados para retorno
        pages_summary = []
        for p in processed_pages:
            pages_summary.append({
                "page_number": p["page_number"],
                "document_name": p.get("document_name", ""),
                "page_in_document": p.get("page_in_document", 1),
                "segment_type": p.get("segment_type", "OUTROS"),
                "raw_text": p.get("raw_text", ""),
                "quality_score": p.get("mean_confidence", 1.0),
                "words_data": p.get("words_data", [])
            })

        # Monta a Matriz de Cruzamento de Documentos e Fatos (Cross-Document Synthesis Matrix)
        documents_matrix = []
        for doc_item in documents_summary:
            d_name = doc_item["filename"]
            d_pages = [p for p in processed_pages if p.get("document_name") == d_name]
            d_segments = list(set(p.get("segment_type", "OUTROS") for p in d_pages))
            
            contributed_facts = []
            if case_facts["financial"].get("evidence") and case_facts["financial"]["evidence"].get("document_name") == d_name:
                contributed_facts.append(f"Financeiro (Valor Pleiteado: R$ {case_facts['financial'].get('requested_amount', 0):,.2f})")
            if any(rc.get("document_name") == d_name for rc in case_facts["financial"].get("receipts_found", [])):
                contributed_facts.append("Comprovante / Nota Fiscal de Desembolso")
            if case_facts["treatment"].get("evidence") and case_facts["treatment"]["evidence"].get("document_name") == d_name:
                contributed_facts.append(f"Laudo Médico / Diagnóstico (CID {case_facts['treatment'].get('cid_10') or 'Geral'})")
            if case_facts["administrative_denial"].get("evidence") and case_facts["administrative_denial"]["evidence"].get("document_name") == d_name:
                contributed_facts.append("Negativa Administrativa da Operadora")

            documents_matrix.append({
                "document_index": doc_item["document_index"],
                "document_name": d_name,
                "pages_count": doc_item["pages_count"],
                "identified_pieces": d_segments,
                "contributed_facts": contributed_facts if contributed_facts else ["Peça processual / Documentos anexos"]
            })

        return {
            "process_id": process_id,
            "total_pages": total_pages,
            "documents_count": len(documents_summary),
            "documents_summary": documents_summary,
            "documents_matrix": documents_matrix,
            "pages": pages_summary,
            "policy_version": active_policy_version.version,
            "verdict": decision_result.overall_verdict,
            "summary": decision_result.summary,
            "identified_theme": case_facts.get("identified_theme", "Geral"),
            "extracted_facts": case_facts,
            "rules": [r.model_dump() for r in decision_result.rule_results],
            "conditional_clauses": decision_result.conditional_clauses,
            "saving_analysis": decision_result.saving_analysis,
            "segregated_amounts": decision_result.segregated_amounts,
            "execution_trace": trace_dict
        }

    def _extract_facts(self, pages: list, tenant_id: str, process_id: str, structured_rules: Optional[dict] = None, trace: Optional[Any] = None) -> dict:
        """
        Extrai valores monetários, diagnósticos, comprovantes, negativas e fatos de cada página do processo,
        avaliando tópicos e vedações de forma 100% dinâmica a partir do PDF da norma ativa.
        """
        full_text = " \n ".join([p.get("raw_text") or "" for p in pages])
        full_text_lower = full_text.lower()

        if trace:
            trace.log("FASE_3_EXTRACAO_FATOS", f"Iniciando varredura e extração de variáveis em {len(pages)} página(s)...")

        # Tenta extração via LLM (OpenRouter) se configurada
        llm_client = OpenRouterExtractionClient()
        llm_facts = None
        if llm_client.is_configured():
            try:
                if trace:
                    trace.log("FASE_3_EXTRACAO_FATOS", f"Enviando processo para análise e extração estruturada via LLM ({llm_client.model})...")
                policy_summary = ""
                if structured_rules and "topics" in structured_rules:
                    policy_summary = "\n".join([f"- Tema {t.get('topic_number')}: {t.get('topic_name')}" for t in structured_rules["topics"]])
                llm_facts = llm_client.extract_facts(process_text=full_text, policy_summary=policy_summary)
            except Exception as e:
                if trace:
                    trace.log("FASE_3_EXTRACAO_FATOS", f"Aviso: Falha na extração LLM, acionando fallback determinístico: {str(e)}", level="WARNING")

        if llm_facts:
            # Popula variáveis a partir do retorno da IA
            fin = llm_facts.get("financial", {})
            treat = llm_facts.get("treatment", {})
            adm = llm_facts.get("administrative_denial", {})

            requested_amount = fin.get("requested_amount", 0.0)
            moral_amount = fin.get("moral_damage_amount", 0.0)
            material_amount = fin.get("material_damage_amount", requested_amount if moral_amount == 0 else max(0.0, requested_amount - moral_amount))
            procedural_stage = llm_facts.get("procedural_stage", "PRE_SENTENCA")
            has_school_aide = treat.get("has_school_aide_request", False)
            cid_found = treat.get("cid_10")
            identified_theme = llm_facts.get("identified_theme", "Geral")
            applicable_topic_num = llm_facts.get("applicable_topic_num", 1)

            if trace:
                trace.log("FASE_3_EXTRACAO_FATOS", f"Extração LLM concluída. Valor: R$ {requested_amount:,.2f} | Fase: {procedural_stage} | CID: {cid_found or 'N/A'} | Tema: {identified_theme}", level="SUCCESS")
                trace.complete_phase("FASE_3_EXTRACAO_FATOS", "COMPLETED", {
                    "requested_amount": requested_amount,
                    "material_amount": material_amount,
                    "moral_amount": moral_amount,
                    "procedural_stage": procedural_stage,
                    "cid_10": cid_found,
                    "has_school_aide": has_school_aide,
                    "extractor": "OPENROUTER_LLM"
                })
        else:
            # 1. Fallback Determinístico: Extração robusta de valor pleiteado na petição inicial, decisões e comprovantes
            requested_amount = 0.0
            amount_matches = re.findall(
                r'(?:dá-se\s+à\s+causa\s+o\s+valor\s+de|valor\s+da\s+causa|valor\s+da\s+ação|condenação|indenização|danos?\s+morais?\s*(?:no\s+valor\s+de)?|reembolso\s+de|valor\s+total|total\s+dos\s+serviços)\s*[:=]*\s*(?:no\s+valor\s+de)?\s*R\$\s*([\d.,]+)',
                full_text,
                re.IGNORECASE
            )
            if amount_matches:
                for match in amount_matches:
                    parsed = BrazilianDomainValidator.parse_brazilian_currency(match)
                    if parsed and parsed > 0:
                        requested_amount = parsed
                        break
            else:
                general_amounts = re.findall(r'R\$\s*([\d.,]+)', full_text)
                if general_amounts:
                    for gm in general_amounts:
                        parsed = BrazilianDomainValidator.parse_brazilian_currency(gm)
                        if parsed and parsed > 0:
                            requested_amount = parsed
                            break

            # 1.1 Extração de Rubricas Segregadas (Dano Material vs Dano Moral vs Sucumbência)
            moral_amount = BrazilianDomainValidator.extract_moral_damage_from_text(full_text, requested_amount=requested_amount)
            material_amount = max(0.0, requested_amount - moral_amount) if moral_amount > 0 else requested_amount

            # 1.2 Detecção Precisa de Fase Processual (Petição Inicial vs Sentença/Acórdão)
            first_pages_text = " \n ".join([(p.get("raw_text") or "").lower() for p in pages[:3]])
            last_pages_text = " \n ".join([(p.get("raw_text") or "").lower() for p in pages[-5:]])

            is_initial_petition = any(k in first_pages_text for k in [
                "petição inicial", "peticao inicial", "excelentíssimo senhor doutor", "excelentissimo senhor doutor",
                "ação indenizatória", "acao indenizatoria", "ação ordinária", "acao ordinaria", "procedimento de juizado", "dos fatos"
            ])
            has_operative_sentence = any(k in last_pages_text for k in [
                "julgo procedente", "julgo improcedente", "julgo extinto", "acordam os desembargadores", "dispositivo da sentença", "dispositivo da sentenca"
            ])

            if is_initial_petition and not has_operative_sentence:
                procedural_stage = "PRE_SENTENCA"
            elif any(k in full_text_lower for k in ["transitado em julgado", "acórdão", "acordao", "turma recursal", "recurso inominado", "fase recursal"]) or has_operative_sentence:
                procedural_stage = "POS_SENTENCA_RECURSAL"
            else:
                procedural_stage = "PRE_SENTENCA"

            # 1.3 Detecção Precoce de Pedido de A.T. Escolar / Mediação Escolar / Terapias
            has_school_aide = any(k in full_text_lower for k in [
                "at escolar", "acompanhamento terapeutico escolar", "acompanhante terapeutico escolar",
                "mediacao escolar", "mediador escolar", "acompanhamento em ambiente escolar", "aba em ambiente escolar",
                "terapia aba em ambiente escolar", "ambiente escolar"
            ])

            # 1.4 Extração de CID-10 se presente
            cid_match = re.search(r'\b([A-Z]\d{2}(?:\.\d{1,2})?)\b', full_text)
            cid_found = cid_match.group(1) if cid_match else None

            if trace:
                trace.log("FASE_3_EXTRACAO_FATOS", f"Valor da Causa Identificado: R$ {requested_amount:,.2f} (Material: R$ {material_amount:,.2f} | Moral: R$ {moral_amount:,.2f}).")
                trace.log("FASE_3_EXTRACAO_FATOS", f"Fase Processual Detectada: {procedural_stage} (Petição Inicial: {is_initial_petition} | Sentença/Acórdão: {has_operative_sentence}).")
                trace.log("FASE_3_EXTRACAO_FATOS", f"Diagnóstico / CID-10: {cid_found or 'Não identificado expressamente'} | Pedido de A.T. Escolar: {has_school_aide}.")
                trace.complete_phase("FASE_3_EXTRACAO_FATOS", "COMPLETED", {
                    "requested_amount": requested_amount,
                    "material_amount": material_amount,
                    "moral_amount": moral_amount,
                    "procedural_stage": procedural_stage,
                    "cid_10": cid_found,
                    "has_school_aide": has_school_aide,
                    "extractor": "REGEX_FALLBACK"
                })

        # 2. Classificação Dinâmica do Tema Baseada Exclusivamente no PDF da Norma Ativa
        identified_theme = None
        applicable_topic_num = None
        norm_full_text = BrazilianDomainValidator.normalize_text_for_matching(full_text)

        # 2.1 Se o LLM já classificou e o tema existe na norma ativa, adota diretamente
        if llm_facts and llm_facts.get("applicable_topic_num"):
            candidate_num = llm_facts.get("applicable_topic_num")
            active_topics_list = structured_rules.get("topics", []) if structured_rules else []
            for t in active_topics_list:
                if t.get("topic_number") == candidate_num:
                    applicable_topic_num = candidate_num
                    identified_theme = f"Tema {t.get('topic_number', 1):02d}: {t.get('topic_name')}"
                    if trace:
                        trace.log("FASE_4_CLASSIFICACAO_TEMA", f"Tema identificado via IA e confirmado na Norma Ativa: '{identified_theme}'.", level="SUCCESS")
                        trace.complete_phase("FASE_4_CLASSIFICACAO_TEMA", "COMPLETED", {"winner_theme": identified_theme, "topic_number": applicable_topic_num, "method": "LLM_CONFIRMED"})
                    break

        # 2.2 Motor Determinístico de Afinidade por Tema (Varre 100% dos tópicos da norma ativa)
        if not identified_theme and structured_rules and "topics" in structured_rules:
            best_topic = None
            best_score = 0
            for t in structured_rules["topics"]:
                t_num = t.get("topic_number")
                t_name = t.get("topic_name", "")
                score = BrazilianDomainValidator.score_topic_affinity(norm_full_text, t)

                if score > 0 and trace:
                    trace.log("FASE_4_CLASSIFICACAO_TEMA", f"Score Tema {t_num:02d} ({t_name[:35]}...): {score} pontos.")

                if score > best_score:
                    best_score = score
                    best_topic = t

            if best_topic and best_score > 0:
                identified_theme = f"Tema {best_topic.get('topic_number', 1):02d}: {best_topic.get('topic_name')}"
                applicable_topic_num = best_topic.get("topic_number")
                if trace:
                    trace.log("FASE_4_CLASSIFICACAO_TEMA", f"Tema Vencedor: '{identified_theme}' com score de afinidade {best_score}.", level="SUCCESS")
                    trace.complete_phase("FASE_4_CLASSIFICACAO_TEMA", "COMPLETED", {"winner_theme": identified_theme, "topic_number": applicable_topic_num, "score": best_score, "method": "DETERMINISTIC_AFFINITY"})
            else:
                identified_theme = "THEME_UNKNOWN (Requer Revisão Humana)"
                applicable_topic_num = None
                if trace:
                    trace.log("FASE_4_CLASSIFICACAO_TEMA", "Aviso: Nenhum tema da norma ativa identificado com afinidade suficiente. Classificado como THEME_UNKNOWN.", level="WARNING")
                    trace.complete_phase("FASE_4_CLASSIFICACAO_TEMA", "COMPLETED", {"winner_theme": identified_theme, "topic_number": None, "score": 0})
        elif not identified_theme:
            identified_theme = "THEME_UNKNOWN"
            applicable_topic_num = None

        # 3. Inicialização e Avaliação Dinâmica de Vedações do PDF da Norma Ativa
        topics_facts = {}
        active_topics = structured_rules.get("topics", []) if structured_rules else []
        if active_topics:
            for t in active_topics:
                t_num = t.get("topic_number")
                if t_num is not None:
                    topics_facts[f"topic_{t_num:02d}"] = {
                        "requirements_met": True,
                        "has_prohibition": False,
                        "evidence": None
                    }
        else:
            topics_facts["topic_01"] = {
                "requirements_met": True,
                "has_prohibition": False,
                "evidence": None
            }

        # Avaliação de Vedações e Requisitos de Fase exclusivamente a partir dos textos extraídos do PDF da Norma
        if structured_rules and "topics" in structured_rules and applicable_topic_num is not None:
            for t in structured_rules["topics"]:
                t_num = t.get("topic_number")
                if t_num != applicable_topic_num:
                    continue
                
                reqs = t.get("requirements", [])
                prohibitions = t.get("prohibitions", [])

                # Se a norma veda acordo expressamente em fase pré-sentença para este tema (ex: Fraude de boleto)
                if procedural_stage == "PRE_SENTENCA":
                    combined_rules_text = " ".join([BrazilianDomainValidator.normalize_text_for_matching(x) for x in reqs + prohibitions])
                    if any(k in combined_rules_text for k in [
                        "somente com sentenca", "nao fazer acordo pre sentenca", "nao faremos acordo em casos pre-sentenca",
                        "nao faremos acordo pre sentenca", "somente em casos com sentenca", "nao fazer acordo pre-sentenca",
                        "nao permitido acordo pre-sentenca", "nao permitido acordo pre sentenca"
                    ]):
                        topics_facts[f"topic_{t_num:02d}"]["has_prohibition"] = True
                        topics_facts[f"topic_{t_num:02d}"]["requirements_met"] = False
                        if trace:
                            trace.log("FASE_5_AVALIACAO_REGRAS", f"VEDAÇÃO DA NORMA ACIONADA: Tema {t_num:02d} veda acordos em fase pré-sentença.", level="WARNING")
                        break

                # Avaliação de Vedações Específicas: verifica se o processo incide em termos vedados do manual
                for prohib in prohibitions:
                    prohib_clean = BrazilianDomainValidator.normalize_text_for_matching(prohib)
                    
                    # 1. Vedação de AT / Acompanhante / Mediação / Ambiente Escolar
                    if re.search(r'\b(?:at|acompanhamento terapeutico|acompanhante terapeutico|ambiente escolar|mediacao escolar)\b', prohib_clean):
                        if has_school_aide or any(k in norm_full_text for k in [
                            "at escolar", "acompanhamento terapeutico escolar", "acompanhante terapeutico escolar",
                            "ambiente escolar", "mediacao escolar", "mediador escolar", "aba em ambiente escolar",
                            "terapia aba em ambiente escolar"
                        ]):
                            topics_facts[f"topic_{t_num:02d}"]["has_prohibition"] = True
                            topics_facts[f"topic_{t_num:02d}"]["requirements_met"] = False
                            if trace:
                                trace.log("FASE_5_AVALIACAO_REGRAS", f"VEDAÇÃO DA NORMA ACIONADA: Pedido de A.T. / Acompanhamento em Ambiente Escolar vedado na norma ativa.", level="WARNING")
                            break

                    # 2. Vedação de Prestador Particular / Fora da Rede Credenciada
                    if "prestador particular" in prohib_clean or "fora da rede" in prohib_clean:
                        if any(k in norm_full_text for k in [
                            "prestador nao credenciado", "clinica nao credenciada", "medico nao credenciado",
                            "prestador particular nao credenciado", "fora da rede credenciada", "rede nao credenciada",
                            "prestador eventual", "clinica eventual"
                        ]):
                            topics_facts[f"topic_{t_num:02d}"]["has_prohibition"] = True
                            topics_facts[f"topic_{t_num:02d}"]["requirements_met"] = False
                            if trace:
                                trace.log("FASE_5_AVALIACAO_REGRAS", f"VEDAÇÃO DA NORMA ACIONADA: Tratamento pleiteado fora da rede credenciada / em prestador eventual.", level="WARNING")
                            break

                    # 3. Vedação de Reembolso Integral
                    if "reembolso integral" in prohib_clean:
                        if any(k in norm_full_text for k in ["reembolso integral", "restituicao integral de 100%", "100% de reembolso"]):
                            topics_facts[f"topic_{t_num:02d}"]["has_prohibition"] = True
                            topics_facts[f"topic_{t_num:02d}"]["requirements_met"] = False
                            if trace:
                                trace.log("FASE_5_AVALIACAO_REGRAS", f"VEDAÇÃO DA NORMA ACIONADA: Pedido de Reembolso Integral 100% vedado na norma ativa.", level="WARNING")
                            break

                    # 4. Extrai termos específicos entre parênteses ou termos técnicos chave
                    specific_terms = re.findall(r'\((.*?)\)', prohib)
                    terms_to_check = []
                    if specific_terms:
                        for st in specific_terms:
                            terms_to_check.extend([s.strip().lower() for s in st.split(',') if len(s.strip()) > 2])
                    
                    # Adiciona expressões compostas proibitivas extraídas do manual
                    for direct_term in [
                        "transplante", "gastroplastia endoscopica", "fertilizacao in vitro",
                        "procedimento com fins esteticos", "foundation one", "sem registro na anvisa",
                        "paciente sus na rede privada", "protese customizada", "off label", "off-label",
                        "experimental", "cirurgia reparadora pos-bariatrica",
                        "mig", "treini", "padovan", "cuevas", "pediasuit", "therasuit", "floortime", "neurofeedback"
                    ]:
                        if direct_term in prohib_clean:
                            terms_to_check.append(direct_term)

                    for term in terms_to_check:
                        norm_term = BrazilianDomainValidator.normalize_text_for_matching(term)
                        if len(norm_term) >= 3 and norm_term in norm_full_text:
                            topics_facts[f"topic_{t_num:02d}"]["has_prohibition"] = True
                            topics_facts[f"topic_{t_num:02d}"]["requirements_met"] = False
                            if trace:
                                trace.log("FASE_5_AVALIACAO_REGRAS", f"VEDAÇÃO DA NORMA ACIONADA: Hipótese vedada '{term}' identificada nos autos.", level="WARNING")
                            break

        facts = {
            "identified_theme": identified_theme,
            "applicable_topic_num": applicable_topic_num,
            "procedural_stage": procedural_stage,
            "financial": {
                "requested_amount": requested_amount,
                "paid_amount_by_beneficiary": requested_amount,
                "material_damage_amount": material_amount,
                "moral_damage_amount": moral_amount,
                "sucumbence_amount": 0.0,
                "has_fiscal_receipt": False,
                "receipts_found": [],
                "evidence": None
            },
            "treatment": {
                "treatment_type": "TERAPIA_ESPECIAL" if any(k in full_text_lower for k in ["aba", "denver", "f84", "tea", "autismo"]) else "ASSISTENCIAL",
                "cid_10": cid_found,
                "has_medical_report": False,
                "has_valid_medical_prescription": False,
                "tea_methods_detected": [],
                "has_school_aide_request": has_school_aide,
                "evidence": None
            },
            "administrative_denial": {
                "has_administrative_denial": False,
                "evidence": None
            },
            "topics": topics_facts,
            "dossier_pages_count": len(pages)
        }

        # 6. Varredura e Cruzamento Multi-Documental Profundo em todas as páginas
        initial_petition_evidence = None

        for p in pages:
            raw_text = p.get("raw_text") or ""
            raw_lower = raw_text.lower()
            page_num = p.get("page_number", 1)
            doc_name = p.get("document_name", "documento.pdf")
            page_in_doc = p.get("page_in_document", 1)

            # 6.1 Detecção de Petição Inicial para ancoragem de pedidos
            if not initial_petition_evidence and any(k in raw_lower for k in ["petição inicial", "peticao inicial", "dos pedidos", "valor da causa", "dá-se à causa"]):
                valid, ev = EvidenceGroundingValidator.validate_and_create_evidence(
                    extracted_snippet="Petição Inicial" if "petição inicial" in raw_lower or "peticao inicial" in raw_lower else "Valor da Causa",
                    page_raw_text=raw_text,
                    words_data=p.get("words_data", []),
                    document_type="PETICAO_INICIAL",
                    page_number=page_num,
                    document_name=doc_name,
                    page_in_document=page_in_doc
                )
                if valid:
                    initial_petition_evidence = ev

            # 6.2 Detecção de Comprovantes / Notas Fiscais / Recibos / PIX / Desembolso
            fiscal_keywords = [
                "nota fiscal", "danfe", "nfs-e", "nf-e", "recibo", "comprovante de pagamento",
                "comprovante de transferencia", "comprovante pix", "extrato", "fatura",
                "boleto quitado", "autenticacao mecanica", "recibo de pagamento"
            ]
            if any(k in raw_lower for k in fiscal_keywords):
                snippet_candidate = "Nota Fiscal"
                for fk in ["nota fiscal", "danfe", "recibo", "comprovante de pagamento", "comprovante pix", "fatura"]:
                    if fk in raw_lower:
                        snippet_candidate = fk.title()
                        break

                valid, ev = EvidenceGroundingValidator.validate_and_create_evidence(
                    extracted_snippet=snippet_candidate,
                    page_raw_text=raw_text,
                    words_data=p.get("words_data", []),
                    document_type="NOTA_FISCAL",
                    page_number=page_num,
                    document_name=doc_name,
                    page_in_document=page_in_doc
                )
                if valid:
                    facts["financial"]["has_fiscal_receipt"] = True
                    facts["financial"]["evidence"] = ev
                    facts["financial"]["receipts_found"].append({
                        "page_number": page_num,
                        "document_name": doc_name,
                        "page_in_document": page_in_doc,
                        "snippet": raw_text[:120].strip()
                    })

            # 6.3 Detecção de Laudo / Relatório Médico / Prescrição / Atestado
            medical_keywords = [
                "laudo medico", "laudo médico", "relatorio medico", "relatório médico",
                "prescricao medica", "prescrição médica", "receituario", "receituário",
                "atestado medico", "atestado médico", "parecer medico", "parecer médico",
                "declaracao medica", "declaração médica", "laudo neurologico", "laudo neurológico",
                "laudo psiquiatrico", "laudo psiquiátrico", "crm", "medico assistente", "médico assistente"
            ]
            if any(k in raw_lower for k in medical_keywords):
                snippet_candidate = "Laudo"
                for mk in ["relatório médico", "relatorio medico", "prescrição médica", "prescricao medica", "receituário", "receituario", "atestado médico", "atestado medico", "laudo"]:
                    if mk in raw_lower:
                        snippet_candidate = mk.title()
                        break

                valid, ev = EvidenceGroundingValidator.validate_and_create_evidence(
                    extracted_snippet=snippet_candidate,
                    page_raw_text=raw_text,
                    words_data=p.get("words_data", []),
                    document_type="LAUDO_MEDICO",
                    page_number=page_num,
                    document_name=doc_name,
                    page_in_document=page_in_doc
                )
                if valid:
                    facts["treatment"]["has_medical_report"] = True
                    facts["treatment"]["evidence"] = ev

                # Valida 2 eixos para TEA/ABA se aplicável
                tea_val = BrazilianDomainValidator.validate_tea_medical_evidence(raw_text)
                if tea_val["is_valid"]:
                    facts["treatment"]["has_valid_medical_prescription"] = True
                    facts["treatment"]["tea_methods_detected"] = tea_val["detected_methods"]

            # 6.4 Detecção de Negativa / Indeferimento / Protocolo da Operadora
            denial_keywords = [
                "negativa", "indeferimento", "indeferido", "nao autorizada", "não autorizada",
                "recusa", "solicitação não atendida", "solicitacao nao atendida", "resposta a solicitacao",
                "resposta à solicitação", "canal de atendimento", "carta resposta", "protocolo",
                "glosa", "fora do rol", "ausencia de cobertura", "ausência de cobertura"
            ]
            if any(k in raw_lower for k in denial_keywords):
                snippet_candidate = "negativa"
                for dk in ["negativa", "indeferimento", "recusa", "não autorizada", "nao autorizada", "carta resposta", "protocolo"]:
                    if dk in raw_lower:
                        snippet_candidate = dk
                        break

                valid, ev = EvidenceGroundingValidator.validate_and_create_evidence(
                    extracted_snippet=snippet_candidate,
                    page_raw_text=raw_text,
                    words_data=p.get("words_data", []),
                    document_type="NEGATIVA_OPERADORA",
                    page_number=page_num,
                    document_name=doc_name,
                    page_in_document=page_in_doc
                )
                if valid:
                    facts["administrative_denial"]["has_administrative_denial"] = True
                    facts["administrative_denial"]["evidence"] = ev

        # 6.5 Se não houver recibo/nota fiscal isolada, ancora a evidência financeira na Petição Inicial
        if not facts["financial"]["evidence"] and initial_petition_evidence:
            facts["financial"]["evidence"] = initial_petition_evidence
        elif not facts["financial"]["evidence"] and len(pages) > 0:
            first_p = pages[0]
            valid, ev = EvidenceGroundingValidator.validate_and_create_evidence(
                extracted_snippet="R$",
                page_raw_text=first_p.get("raw_text") or "",
                words_data=first_p.get("words_data", []),
                document_type="PETICAO_INICIAL",
                page_number=1,
                document_name=first_p.get("document_name", "documento.pdf"),
                page_in_document=first_p.get("page_in_document", 1)
            )
            if valid:
                facts["financial"]["evidence"] = ev

        return facts

