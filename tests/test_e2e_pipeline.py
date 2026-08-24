import pytest
import fitz
from src.ingestion.quality_assessor import PageQualityAssessor
from src.ocr.cascade_engine import OCRCascadeEngine
from src.segmentation.segmenter import DocumentSegmenter, DocumentCategory, RELEVANT_DOCUMENT_CATEGORIES
from src.extraction.evidence_grounding import EvidenceGroundingValidator
from src.extraction.schemas import CaseFactModel, MedicalTreatmentFact, FinancialReimbursementFact, AdministrativeDenialFact
from src.rule_engine.deterministic_engine import DeterministicRuleEngine
from src.rule_engine.semantic_diff import PolicySemanticDiff

@pytest.fixture
def active_policy_fixture():
    return {
        "policy_version_id": "2026.1-NORM-SAUDE",
        "rules": [
            {
                "rule_code": "RULE_DESEMBOLSO",
                "title": "Comprovação de Desembolso Financeiro",
                "mandatory": True,
                "condition": {
                    "and": [
                        {"==": [{"var": "financial.has_fiscal_receipt"}, True]},
                        {">": [{"var": "financial.paid_amount_by_beneficiary"}, 0]}
                    ]
                },
                "required_evidence_fields": ["financial"],
                "failure_message_template": "Ausência de Nota Fiscal com comprovação de pagamento."
            },
            {
                "rule_code": "RULE_TETO_MAXIMO",
                "title": "Teto Máximo de R$ 60.000,00",
                "mandatory": True,
                "condition": {"<=": [{"var": "financial.requested_amount"}, 60000.0]},
                "required_evidence_fields": ["financial"],
                "failure_message_template": "Valor solicitado R$ {{financial.requested_amount}} excede o teto."
            },
            {
                "rule_code": "RULE_RECUSA_PREVIA",
                "title": "Recusa Administrativa Prévia",
                "mandatory": True,
                "condition": {"==": [{"var": "administrative_denial.has_administrative_denial"}, True]},
                "required_evidence_fields": ["administrative_denial"],
                "failure_message_template": "Sem comprovação de recusa administrativa prévia."
            }
        ]
    }

def create_synthetic_judicial_pdf() -> fitz.Document:
    """Gera um PDF sintético de 5 páginas representando um processo judicial completo."""
    doc = fitz.open()

    # Pág 1: Petição Inicial
    p1 = doc.new_page()
    p1.insert_text((50, 50), "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO DA VARA CÍVEL.\n"
                            "AÇÃO ORDINÁRIA DE REEMBOLSO DE DESPESAS MÉDICAS.\n"
                            "Autor: Carlos Eduardo Pereira, CPF: 123.456.789-00.\n"
                            "Réu: Operadora de Saúde Vida Plena S.A.\n"
                            "Valor da Ação: R$ 35.000,00.")

    # Pág 2: Procuração (Documento Irrelevante para Acordo)
    p2 = doc.new_page()
    p2.insert_text((50, 50), "PROCURAÇÃO AD JUDICIA.\nOutorgante: Carlos Eduardo Pereira.\nOutorgado: Dr. Advogado...")

    # Pág 3: Laudo Médico
    p3 = doc.new_page()
    p3.insert_text((50, 50), "RELATÓRIO MÉDICO CIRCUNSTANCIADO.\n"
                            "Paciente em tratamento de Terapia ABA contínua, CID-10 F84.0.\n"
                            "Médico: Dr. Roberto Silva - CRM/SP 999888.")

    # Pág 4: Negativa Administrativa da Operadora
    p4 = doc.new_page()
    p4.insert_text((50, 50), "NEGATIVA DE COBERTURA ADMINISTRATIVA.\n"
                            "Protocolo de Atendimento: 20250819-994411.\n"
                            "Informamos que a solicitação não autorizada por não constar no rol.")

    # Pág 5: Nota Fiscal e Recibo de Pagamento
    p5 = doc.new_page()
    p5.insert_text((50, 50), "DANFE - NOTA FISCAL DE SERVIÇOS ELETRÔNICA.\n"
                            "Prestador: Clínica Terapêutica NeuroVida - CNPJ: 12.345.678/0001-99.\n"
                            "Tomador: Carlos Eduardo Pereira.\n"
                            "Discriminação: Tratamento Terapia ABA.\n"
                            "Valor Total da Nota: R$ 35.000,00. Pago via PIX em 10/01/2025.")

    return doc

def test_full_pipeline_end_to_end_eligible(active_policy_fixture):
    # 1. Ingestão do PDF do Processo
    doc = create_synthetic_judicial_pdf()
    assert len(doc) == 5

    # 2. Processamento e OCR em Cascata de todas as páginas
    ocr_engine = OCRCascadeEngine()
    processed_pages = []
    for idx, page in enumerate(doc):
        res = ocr_engine.process_page(page, page_number=idx + 1)
        processed_pages.append(res)

    assert len(processed_pages) == 5
    assert all(p["mean_confidence"] >= 0.85 for p in processed_pages)

    # 3. Segmentação Documental e Filtro de Relevância
    segments = DocumentSegmenter.segment_process_pages(processed_pages)
    assert len(segments) >= 3

    # Verifica se a procuração foi classificada como NÃO relevante
    procuracao_seg = next((s for s in segments if s["category"] == "PROCURACAO"), None)
    if procuracao_seg:
        assert procuracao_seg["is_relevant"] is False

    # 4. Extração de Fatos com Evidence Grounding
    # Simula extração dos documentos relevantes
    nf_page = processed_pages[4] # Pág 5
    neg_page = processed_pages[3] # Pág 4
    laudo_page = processed_pages[2] # Pág 3

    valid_nf, ev_nf = EvidenceGroundingValidator.validate_and_create_evidence(
        extracted_snippet="Valor Total da Nota: R$ 35.000,00",
        page_raw_text=nf_page["raw_text"],
        words_data=nf_page["words_data"],
        document_type="NOTA_FISCAL",
        page_number=5
    )
    assert valid_nf is True

    valid_neg, ev_neg = EvidenceGroundingValidator.validate_and_create_evidence(
        extracted_snippet="Protocolo de Atendimento: 20250819-994411",
        page_raw_text=neg_page["raw_text"],
        words_data=neg_page["words_data"],
        document_type="NEGATIVA_OPERADORA",
        page_number=4
    )
    assert valid_neg is True

    valid_laudo, ev_laudo = EvidenceGroundingValidator.validate_and_create_evidence(
        extracted_snippet="CID-10 F84.0",
        page_raw_text=laudo_page["raw_text"],
        words_data=laudo_page["words_data"],
        document_type="LAUDO_MEDICO",
        page_number=3
    )
    assert valid_laudo is True

    # 5. Consolidação no Case Fact Model
    case_facts = {
        "financial": {
            "requested_amount": 35000.0,
            "paid_amount_by_beneficiary": 35000.0,
            "has_fiscal_receipt": True,
            "evidence": ev_nf
        },
        "treatment": {
            "treatment_type": "TERAPIA_ABA",
            "cid_10": "F84.0",
            "evidence": ev_laudo
        },
        "administrative_denial": {
            "has_administrative_denial": True,
            "protocol": "20250819-994411",
            "evidence": ev_neg
        }
    }

    # 6. Avaliação Determinística pelo Motor de Regras
    engine = DeterministicRuleEngine(active_policy_fixture)
    decision = engine.evaluate(process_id="proc_e2e_001", case_fact_data=case_facts)

    assert decision.overall_verdict == "ELIGIBLE"
    assert len(decision.rule_results) == 3
    assert all(r.status == "PASS" for r in decision.rule_results)
    assert "100% elegível" in decision.summary

def test_full_pipeline_missing_evidence_triggers_hitl(active_policy_fixture):
    engine = DeterministicRuleEngine(active_policy_fixture)

    # Processo onde a negativa não foi comprovada (evidência ausente)
    case_facts_incomplete = {
        "financial": {
            "requested_amount": 35000.0,
            "paid_amount_by_beneficiary": 35000.0,
            "has_fiscal_receipt": True,
            "evidence": {"page_number": 5, "text_snippet": "NF 35k"}
        },
        "treatment": {
            "treatment_type": "TERAPIA_ABA",
            "evidence": {"page_number": 3, "text_snippet": "Laudo"}
        },
        "administrative_denial": {
            "has_administrative_denial": True,
            "evidence": None  # Evidência ausente
        }
    }

    decision = engine.evaluate(process_id="proc_e2e_002", case_fact_data=case_facts_incomplete)
    assert decision.overall_verdict == "REQUIRES_HUMAN_REVIEW"
    assert any(r.status == "UNKNOWN" for r in decision.rule_results)

def test_semantic_diff_on_policy_update(active_policy_fixture):
    # Nova versão da norma reduzindo o teto para R$ 25.000,00 e adicionando nova regra
    updated_rules = [
        active_policy_fixture["rules"][0], # Mantém Desembolso
        {
            "rule_code": "RULE_TETO_MAXIMO",
            "title": "Teto Máximo de R$ 25.000,00", # Alterado
            "mandatory": True,
            "condition": {"<=": [{"var": "financial.requested_amount"}, 25000.0]},
            "required_evidence_fields": ["financial"],
            "failure_message_template": "Valor solicitado R$ {{financial.requested_amount}} excede o novo teto."
        },
        {
            "rule_code": "RULE_EXCLUSAO_EXPERIMENTAL",
            "title": "Exclusão de Tratamento Experimental",
            "mandatory": True,
            "condition": {"!=": [{"var": "treatment.treatment_type"}, "EXPERIMENTAL"]},
            "required_evidence_fields": ["treatment"],
            "failure_message_template": "Tratamentos experimentais não são elegíveis a acordo."
        }
        # Removeu a regra de Recusa Prévia
    ]

    diff = PolicySemanticDiff.compare_policies(
        base_policy_rules=active_policy_fixture["rules"],
        target_policy_rules=updated_rules,
        base_ver="2026.1",
        target_ver="2026.2"
    )

    assert len(diff.rules_added) == 1
    assert diff.rules_added[0].rule_code == "RULE_EXCLUSAO_EXPERIMENTAL"
    assert len(diff.rules_removed) == 1
    assert diff.rules_removed[0].rule_code == "RULE_RECUSA_PREVIA"
    assert len(diff.rules_modified) == 1
    assert diff.rules_modified[0].rule_code == "RULE_TETO_MAXIMO"

def test_process_execution_service_multi_pdf():
    from src.core.database import SessionLocal, init_db
    from src.services.process_service import ProcessExecutionService
    from src.models.entities import Tenant, generate_uuid

    init_db()
    db = SessionLocal()
    try:
        from src.models.entities import Policy, PolicyVersion
        tenant = db.query(Tenant).filter(Tenant.slug == "operadora-saude-padrao").first()
        if not tenant:
            tenant = Tenant(id=generate_uuid(), name="Tenant E2E", slug="operadora-saude-padrao")
            db.add(tenant)
            db.commit()
        tenant_id = tenant.id

        # Garante norma ativa para o tenant
        active_pol = db.query(PolicyVersion).filter(PolicyVersion.tenant_id == tenant_id, PolicyVersion.status == "ACTIVE").first()
        if not active_pol:
            pol = db.query(Policy).filter(Policy.tenant_id == tenant_id).first()
            if not pol:
                pol = Policy(id=generate_uuid(), tenant_id=tenant_id, name="Norma Padrão")
                db.add(pol)
                db.commit()
            active_pol = PolicyVersion(
                id=generate_uuid(),
                tenant_id=tenant_id,
                policy_id=pol.id,
                version="2026.1",
                status="ACTIVE",
                structured_rules={"policy_version_id": "2026.1", "rules": [{"rule_code": "TEST_R1", "condition": {"==": [1, 1]}}]}
            )
            db.add(active_pol)
            db.commit()

        proc_id = generate_uuid()

        # Doc 1: Petição Inicial
        doc1 = fitz.open()
        p1 = doc1.new_page()
        p1.insert_text((50, 50), "Petição Inicial. Ação de Reembolso de Despesas Médicas. Valor da causa R$ 25.000,00.")
        b1 = doc1.tobytes()
        doc1.close()

        # Doc 2: Nota Fiscal
        doc2 = fitz.open()
        p2 = doc2.new_page()
        p2.insert_text((50, 50), "NOTA FISCAL DE PRESTAÇÃO DE SERVIÇOS. Valor Pago R$ 25.000,00.")
        b2 = doc2.tobytes()
        doc2.close()

        service = ProcessExecutionService(db=db)

        result = service.process_and_evaluate_multi(
            tenant_id=tenant_id,
            process_id=proc_id,
            pdf_files=[
                {"bytes": b1, "filename": "peticao.pdf"},
                {"bytes": b2, "filename": "nota_fiscal.pdf"}
            ]
        )

        assert result["total_pages"] == 2
        assert result["documents_count"] == 2
        assert result["verdict"] in ["ELIGIBLE", "NOT_ELIGIBLE", "REQUIRES_HUMAN_REVIEW"]
        assert len(result["documents_summary"]) == 2
    finally:
        db.close()
