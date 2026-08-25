"""
src/api/routes/processes.py
Rotas REST para upload, listagem e auditoria de Processos Judiciais.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from src.core.database import SessionLocal
from src.models.entities import Process, Evaluation, PolicyVersion, DocumentPage, ExtractedFact, Evidence, Tenant, HumanReview, AuditLog, generate_uuid
from src.services.process_service import ProcessExecutionService

router = APIRouter(prefix="/processes", tags=["Processos Judiciais"])

class ProcessDetailResponse(BaseModel):
    process_id: str
    cnj_number: str
    beneficiary_name: str
    operator_name: str
    total_pages: int
    status: str
    verdict: Optional[str] = None
    summary: Optional[str] = None
    identified_theme: Optional[str] = None
    policy_version: Optional[str] = None
    requested_amount: Optional[float] = 0.0
    proposal_amount: Optional[float] = 0.0
    saving_amount: Optional[float] = 0.0
    created_at_formatted: Optional[str] = None
    updated_at_formatted: Optional[str] = None
    rules: List[Dict[str, Any]] = []

@router.get("", response_model=List[ProcessDetailResponse])
@router.get("/", response_model=List[ProcessDetailResponse])
async def list_processes(
    tenant_id: Optional[str] = None,
    scope: Optional[str] = "all"
):
    """
    Lista os processos judiciais cadastrados e avaliados no banco de dados para o tenant.
    scope:
      - 'inbox': apenas processos pendentes de deliberação (PENDING, PROCESSING, EVALUATED, REQUIRES_HUMAN_REVIEW)
      - 'history': apenas processos já deliberados (APPROVED, REJECTED)
      - 'all': todos os processos
    """
    db = SessionLocal()
    try:
        query = db.query(Process)
        if tenant_id:
            query = query.filter(Process.tenant_id == tenant_id)
        
        if scope == "inbox":
            query = query.filter(Process.status.in_(["PENDING", "PROCESSING", "EVALUATED", "REQUIRES_HUMAN_REVIEW"]))
        elif scope == "history":
            query = query.filter(Process.status.in_(["APPROVED", "REJECTED"]))

        processes = query.order_by(Process.created_at.desc()).all()
        results = []
        for p in processes:
            eval_record = db.query(Evaluation).filter(Evaluation.process_id == p.id).first()
            p_ver = db.query(PolicyVersion).filter(PolicyVersion.id == eval_record.policy_version_id).first() if eval_record else None
            theme_fact = db.query(ExtractedFact).filter(ExtractedFact.process_id == p.id, ExtractedFact.fact_key == "identified_theme").first()
            identified_theme = theme_fact.normalized_value if theme_fact else None

            fin_fact = db.query(ExtractedFact).filter(ExtractedFact.process_id == p.id, ExtractedFact.fact_key == "financial").first()
            req_amt = 0.0
            if fin_fact and isinstance(fin_fact.fact_value, dict):
                req_amt = float(fin_fact.fact_value.get("requested_amount", 0.0) or 0.0)
            
            prop_amt = req_amt * 0.80 if (p.status == "APPROVED" or (eval_record and eval_record.overall_result in ["ELIGIBLE", "CONDITIONALLY_ELIGIBLE"])) else 0.0
            sav_amt = (req_amt - prop_amt) if prop_amt > 0 else 0.0

            results.append(ProcessDetailResponse(
                process_id=p.id,
                cnj_number=p.cnj_number,
                beneficiary_name=p.beneficiary_name or "Beneficiário",
                operator_name=p.operator_name or "Operadora de Saúde",
                total_pages=p.total_pages,
                status=p.status,
                verdict=eval_record.overall_result if eval_record else "PENDING",
                summary=eval_record.decision_summary if eval_record else "Em processamento",
                identified_theme=identified_theme,
                policy_version=p_ver.version if p_ver else None,
                requested_amount=req_amt,
                proposal_amount=prop_amt,
                saving_amount=sav_amt,
                created_at_formatted=p.created_at.strftime("%d/%m/%Y %H:%M") if p.created_at else None,
                updated_at_formatted=p.updated_at.strftime("%d/%m/%Y %H:%M") if p.updated_at else None,
                rules=eval_record.rules_results if eval_record and eval_record.rules_results else []
            ))
        return results
    finally:
        db.close()


@router.get("/{process_id}")
async def get_process_details(process_id: str):
    """
    Retorna os detalhes completos de auditoria e regras avaliadas para um processo real.
    """
    db = SessionLocal()
    try:
        proc = db.query(Process).filter(Process.id == process_id).first()
        if not proc:
            raise HTTPException(status_code=404, detail="Processo não encontrado.")

        eval_record = db.query(Evaluation).filter(Evaluation.process_id == proc.id).first()
        p_ver = db.query(PolicyVersion).filter(PolicyVersion.id == eval_record.policy_version_id).first() if eval_record else None

        theme_fact = db.query(ExtractedFact).filter(ExtractedFact.process_id == proc.id, ExtractedFact.fact_key == "identified_theme").first()
        identified_theme = theme_fact.normalized_value if theme_fact else None

        facts_records = db.query(ExtractedFact).filter(ExtractedFact.process_id == proc.id).all()
        facts_dict = {}
        for fr in facts_records:
            facts_dict[fr.fact_key] = fr.fact_value

        pages_records = db.query(DocumentPage).filter(DocumentPage.process_id == proc.id).order_by(DocumentPage.page_number.asc()).all()
        pages_list = []
        for pr in pages_records:
            pages_list.append({
                "page_number": pr.page_number,
                "document_name": pr.document_name or "documento.pdf",
                "page_in_document": pr.page_in_document or pr.page_number,
                "segment_type": pr.segment_type or "OUTROS",
                "raw_text": pr.raw_text or "",
                "quality_score": pr.quality_score,
                "has_native_text": pr.has_native_text,
                "words_data": pr.words_data or []
            })

        return {
            "process_id": proc.id,
            "cnj_number": proc.cnj_number,
            "beneficiary_name": proc.beneficiary_name,
            "operator_name": proc.operator_name,
            "total_pages": proc.total_pages,
            "status": proc.status,
            "verdict": eval_record.overall_result if eval_record else "PENDING",
            "summary": eval_record.decision_summary if eval_record else "Em processamento",
            "identified_theme": identified_theme,
            "policy_version": p_ver.version if p_ver else "2026.1",
            "total_pages_stored": len(pages_records),
            "pages": pages_list,
            "facts": facts_dict,
            "rules": eval_record.rules_results if eval_record and eval_record.rules_results else [],
            "execution_trace": eval_record.execution_trace if eval_record and eval_record.execution_trace else None
        }
    finally:
        db.close()

@router.get("/{process_id}/trace")
async def get_process_trace(process_id: str):
    """
    Retorna o log forense completo estruturado em JSON com as 6 fases da análise.
    """
    db = SessionLocal()
    try:
        eval_record = db.query(Evaluation).filter(Evaluation.process_id == process_id).first()
        if not eval_record or not eval_record.execution_trace:
            # Tenta carregar do disco
            import os, json
            trace_path = os.path.join("logs", "processes", f"{process_id}_trace.json")
            if os.path.exists(trace_path):
                with open(trace_path, "r", encoding="utf-8") as f:
                    return json.load(f)
            raise HTTPException(status_code=404, detail="Trace log não encontrado para este processo.")
        return eval_record.execution_trace
    finally:
        db.close()

@router.get("/{process_id}/log-text")
async def get_process_log_text(process_id: str):
    """
    Retorna o log em texto legível para auditoria humana direta.
    """
    import os
    from fastapi.responses import PlainTextResponse
    log_path = os.path.join("logs", "processes", f"{process_id}.log")
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8") as f:
            return PlainTextResponse(f.read())
    raise HTTPException(status_code=404, detail="Arquivo de log de texto não encontrado.")

@router.post("/upload")
async def upload_judicial_process(
    files: Optional[List[UploadFile]] = File(default=None),
    file: Optional[UploadFile] = File(default=None),
    cnj_number: Optional[str] = Form(default=None),
    beneficiary_name: Optional[str] = Form(default="Beneficiário dos Autos"),
    operator_name: Optional[str] = Form(default="Operadora de Saúde"),
    tenant_id: Optional[str] = Form(default=None)
):
    """
    Recebe um ou múltiplos arquivos PDF reais que compõem o processo judicial,
    processa todas as páginas no motor OCR em cascata, cruza evidências entre as peças
    (Petição Inicial, Laudos Médicos, Notas Fiscais, Negativas) e emite o veredito determinístico.
    """
    import pathlib
    all_uploads = []
    if files:
        all_uploads.extend(files)
    if file:
        all_uploads.append(file)

    if not all_uploads:
        raise HTTPException(status_code=400, detail="Nenhum arquivo PDF foi selecionado.")

    pdf_files_payload = []
    for f in all_uploads:
        if not f.filename:
            continue
        safe_name = pathlib.Path(f.filename).name
        if not safe_name.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"O arquivo '{safe_name}' não é um PDF válido.")
        pdf_bytes = await f.read()
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail=f"O arquivo '{safe_name}' está vazio ou corrompido.")
        if not pdf_bytes.startswith(b"%PDF-"):
            raise HTTPException(status_code=400, detail=f"O arquivo '{safe_name}' não possui cabeçalho binário PDF válido.")
        pdf_files_payload.append({
            "bytes": pdf_bytes,
            "filename": safe_name
        })

    if not pdf_files_payload:
        raise HTTPException(status_code=400, detail="Nenhum PDF válido para processamento.")

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "operadora-saude-padrao").first()
        effective_tenant_id = tenant_id or (tenant.id if tenant else "default_tenant")

        proc_id = generate_uuid()
        effective_cnj = cnj_number if (cnj_number and len(cnj_number) > 5) else f"000{generate_uuid()[:4]}-50.2025.8.26.0100"

        proc = db.query(Process).filter(
            Process.tenant_id == effective_tenant_id,
            Process.cnj_number == effective_cnj
        ).first()

        if not proc:
            proc = Process(
                id=proc_id,
                tenant_id=effective_tenant_id,
                cnj_number=effective_cnj,
                beneficiary_name=beneficiary_name or "Beneficiário dos Autos",
                operator_name=operator_name or "Operadora de Saúde",
                status="PROCESSING"
            )
            db.add(proc)
            db.commit()
        else:
            proc.status = "PROCESSING"
            proc_id = proc.id
            db.commit()

        # Executa esteira completa multi-documento
        service = ProcessExecutionService(db=db)
        result = service.process_and_evaluate_multi(
            tenant_id=effective_tenant_id,
            process_id=proc_id,
            pdf_files=pdf_files_payload
        )

        return {
            "status": "SUCCESS",
            "process_id": proc_id,
            "cnj_number": effective_cnj,
            "beneficiary_name": beneficiary_name or "Beneficiário dos Autos",
            "operator_name": operator_name or "Operadora de Saúde",
            "documents_count": result.get("documents_count", len(pdf_files_payload)),
            "documents_summary": result.get("documents_summary", []),
            "total_pages": result["total_pages"],
            "policy_version": result["policy_version"],
            "identified_theme": result.get("identified_theme"),
            "verdict": result["verdict"],
            "summary": result["summary"],
            "rules": result["rules"]
        }
    finally:
        db.close()


class ProcessDecisionRequest(BaseModel):
    decision: str  # "APPROVE", "REJECT", "SEND_TO_HITL"
    operator_notes: Optional[str] = None
    proposal_amount: Optional[float] = None
    operator_name: Optional[str] = "Advogado Operador"


@router.post("/{process_id}/decide")
async def execute_process_decision(process_id: str, payload: ProcessDecisionRequest):
    """
    Registra a decisão humana formal (Aprovação de Acordo, Rejeição ou Encaminhamento HITL)
    com histórico de auditoria forense no banco de dados.
    """
    db = SessionLocal()
    try:
        proc = db.query(Process).filter(Process.id == process_id).first()
        if not proc:
            raise HTTPException(status_code=404, detail="Processo não encontrado.")

        eval_record = db.query(Evaluation).filter(Evaluation.process_id == proc.id).first()

        decision = payload.decision.upper()
        if decision == "APPROVE":
            proc.status = "APPROVED"
            if eval_record:
                eval_record.overall_result = "ELIGIBLE"
                eval_record.decision_summary = f"Acordo aprovado formalmente por {payload.operator_name}. {payload.operator_notes or ''}".strip()
        elif decision == "REJECT":
            proc.status = "REJECTED"
            if eval_record:
                eval_record.overall_result = "INELIGIBLE"
                eval_record.decision_summary = f"Proposta de acordo rejeitada por {payload.operator_name}. Motivo: {payload.operator_notes or 'Contestação indicada'}".strip()
        elif decision == "SEND_TO_HITL":
            proc.status = "REQUIRES_HUMAN_REVIEW"
            if eval_record:
                eval_record.overall_result = "REQUIRES_HUMAN_REVIEW"
                eval_record.decision_summary = f"Encaminhado para Fila de Revisão Humana por {payload.operator_name}. {payload.operator_notes or ''}".strip()
            # Garante que haja um registro em HumanReview
            existing_review = db.query(HumanReview).filter(
                HumanReview.process_id == proc.id,
                HumanReview.status == "OPEN"
            ).first()
            if not existing_review and eval_record:
                new_review = HumanReview(
                    id=generate_uuid(),
                    tenant_id=proc.tenant_id,
                    process_id=proc.id,
                    evaluation_id=eval_record.id,
                    status="OPEN",
                    review_reason="MANUAL_FLAG_BY_OPERATOR",
                    operator_notes=payload.operator_notes
                )
                db.add(new_review)
        else:
            raise HTTPException(status_code=400, detail=f"Decisão inválida: '{payload.decision}'. Use APPROVE, REJECT ou SEND_TO_HITL.")

        # Registra no log de auditoria
        audit = AuditLog(
            id=generate_uuid(),
            tenant_id=proc.tenant_id,
            event_type=f"DECISION_{decision}",
            entity_name="Process",
            entity_id=proc.id,
            payload={
                "decision": decision,
                "operator_name": payload.operator_name,
                "notes": payload.operator_notes,
                "proposal_amount": payload.proposal_amount
            }
        )
        db.add(audit)
        db.commit()

        return {
            "status": "SUCCESS",
            "process_id": proc.id,
            "decision": decision,
            "new_status": proc.status,
            "summary": eval_record.decision_summary if eval_record else None
        }
    finally:
        db.close()


class ReopenProcessRequest(BaseModel):
    reason: str
    operator_name: Optional[str] = "Advogado Operador"


@router.post("/{process_id}/reopen")
async def reopen_process(process_id: str, payload: ReopenProcessRequest):
    """
    Reabre um processo que já estava arquivado/deliberado no Histórico,
    retornando-o para a Fila de Decisão (status EVALUATED) com registro no AuditLog.
    """
    db = SessionLocal()
    try:
        proc = db.query(Process).filter(Process.id == process_id).first()
        if not proc:
            raise HTTPException(status_code=404, detail="Processo não encontrado.")

        previous_status = proc.status
        proc.status = "EVALUATED"

        audit = AuditLog(
            id=generate_uuid(),
            tenant_id=proc.tenant_id,
            event_type="PROCESS_REOPENED",
            entity_name="Process",
            entity_id=proc.id,
            payload={
                "previous_status": previous_status,
                "new_status": "EVALUATED",
                "reopen_reason": payload.reason,
                "operator_name": payload.operator_name
            }
        )
        db.add(audit)
        db.commit()

        return {
            "status": "SUCCESS",
            "process_id": proc.id,
            "previous_status": previous_status,
            "new_status": proc.status,
            "message": "Processo reaberto com sucesso e retornado para a Fila de Decisão."
        }
    finally:
        db.close()


class BulkApproveRequest(BaseModel):
    process_ids: List[str]
    operator_name: Optional[str] = "Advogado Operador"
    operator_notes: Optional[str] = "Aprovação em lote de processos 100% elegíveis."


@router.post("/bulk-approve")
async def bulk_approve_processes(payload: BulkApproveRequest):
    """
    Aprova múltiplos processos em lote simultaneamente, persistindo as decisões
    e gerando trilha de auditoria em AuditLog.
    """
    if not payload.process_ids:
        raise HTTPException(status_code=400, detail="Nenhum processo informado para aprovação em lote.")

    db = SessionLocal()
    try:
        approved_count = 0
        results = []
        for pid in payload.process_ids:
            proc = db.query(Process).filter(Process.id == pid).first()
            if proc:
                proc.status = "APPROVED"
                eval_record = db.query(Evaluation).filter(Evaluation.process_id == proc.id).first()
                if eval_record:
                    eval_record.overall_result = "ELIGIBLE"
                    eval_record.decision_summary = f"Acordo aprovado em lote por {payload.operator_name}. {payload.operator_notes or ''}".strip()
                
                audit = AuditLog(
                    id=generate_uuid(),
                    tenant_id=proc.tenant_id,
                    event_type="DECISION_APPROVE_BULK",
                    entity_name="Process",
                    entity_id=proc.id,
                    payload={
                        "decision": "APPROVE",
                        "operator_name": payload.operator_name,
                        "notes": payload.operator_notes
                    }
                )
                db.add(audit)
                approved_count += 1
                results.append({"process_id": pid, "status": "APPROVED"})
        db.commit()

        return {
            "status": "SUCCESS",
            "approved_count": approved_count,
            "results": results
        }
    finally:
        db.close()


@router.get("/export/csv")
async def export_processes_csv(
    scope: Optional[str] = "history",
    tenant_id: Optional[str] = None
):
    """
    Exporta os dados dos processos para relatório consolidado em formato CSV.
    """
    import io, csv
    from fastapi.responses import Response

    db = SessionLocal()
    try:
        query = db.query(Process)
        if tenant_id:
            query = query.filter(Process.tenant_id == tenant_id)
        
        if scope == "history":
            query = query.filter(Process.status.in_(["APPROVED", "REJECTED"]))
        elif scope == "inbox":
            query = query.filter(Process.status.in_(["PENDING", "PROCESSING", "EVALUATED", "REQUIRES_HUMAN_REVIEW"]))

        processes = query.order_by(Process.created_at.desc()).all()

        output = io.StringIO()
        writer = csv.writer(output, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        writer.writerow([
            "ID Processo", "CNJ", "Beneficiario", "Operadora", "Status", "Veredito",
            "Tema Classificado", "Valor Pleiteado (R$)", "Proposta Acordo (R$)",
            "Saving Estimado (R$)", "Data Ingestao", "Ultima Atualizacao"
        ])

        for p in processes:
            eval_record = db.query(Evaluation).filter(Evaluation.process_id == p.id).first()
            theme_fact = db.query(ExtractedFact).filter(ExtractedFact.process_id == p.id, ExtractedFact.fact_key == "identified_theme").first()
            fin_fact = db.query(ExtractedFact).filter(ExtractedFact.process_id == p.id, ExtractedFact.fact_key == "financial").first()

            req_amt = 0.0
            if fin_fact and isinstance(fin_fact.fact_value, dict):
                req_amt = float(fin_fact.fact_value.get("requested_amount", 0.0) or 0.0)

            prop_amt = req_amt * 0.80 if (p.status == "APPROVED" or (eval_record and eval_record.overall_result in ["ELIGIBLE", "CONDITIONALLY_ELIGIBLE"])) else 0.0
            saving = req_amt - prop_amt if prop_amt > 0 else 0.0

            writer.writerow([
                p.id,
                p.cnj_number,
                p.beneficiary_name or "Beneficiario",
                p.operator_name or "Grupo Amil",
                p.status,
                eval_record.overall_result if eval_record else "PENDING",
                theme_fact.normalized_value if theme_fact else "Tema Geral",
                f"{req_amt:.2f}".replace(".", ","),
                f"{prop_amt:.2f}".replace(".", ","),
                f"{saving:.2f}".replace(".", ","),
                p.created_at.strftime("%d/%m/%Y %H:%M") if p.created_at else "",
                p.updated_at.strftime("%d/%m/%Y %H:%M") if p.updated_at else ""
            ])

        csv_content = output.getvalue().encode("utf-8-sig")
        return Response(
            content=csv_content,
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=relatorio_processos_seixas.csv"}
        )
    finally:
        db.close()



