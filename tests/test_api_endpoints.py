import pytest
import fitz
from fastapi.testclient import TestClient
from src.api.main import app

client = TestClient(app)

def test_health_check_endpoint():
    response = client.get("/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert data["service"] == "Seixas AI"

def test_get_active_policy_endpoint():
    response = client.get("/policies/active")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ACTIVE"
    assert data["total_rules"] >= 1

def test_policy_draft_diff_and_activation_lifecycle():
    import uuid
    uid = uuid.uuid4().hex[:6]
    test_ver = f"2026.TEST_{uid}"
    rule_code_new = f"RULE_NEW_{uid}"

    # 1. Cria nova versão DRAFT
    new_draft_payload = {
        "policy_name": "Manual de Acordos 2026",
        "version": test_ver,
        "rules": [
            {
                "rule_code": "RULE_001_DESEMBOLSO",
                "title": "Comprovação de Desembolso Financeiro",
                "description": "Exige nota fiscal ou recibo.",
                "mandatory": True,
                "condition": {"==": [{"var": "financial.has_fiscal_receipt"}, True]},
                "required_evidence_fields": ["financial"],
                "failure_message_template": "Ausência de Nota Fiscal."
            },
            {
                "rule_code": rule_code_new,
                "title": "Teto Máximo de R$ 30.000,00",
                "description": "Novo teto reduzido para 30k.",
                "mandatory": True,
                "condition": {"<=": [{"var": "financial.requested_amount"}, 30000.0]},
                "required_evidence_fields": ["financial"],
                "failure_message_template": "Excede o teto."
            }
        ]
    }
    
    draft_res = client.post("/policies/draft", json=new_draft_payload)
    assert draft_res.status_code == 200
    draft_data = draft_res.json()
    assert draft_data["status"] == "DRAFT"
    draft_id = draft_data["id"]

    # 2. Consulta o Diff Semântico entre DRAFT e ACTIVE
    diff_res = client.get(f"/policies/{draft_id}/diff")
    assert diff_res.status_code == 200
    diff_data = diff_res.json()
    assert any(r["rule_code"] == rule_code_new for r in diff_data["rules_added"])

    # 3. Ativa a nova versão (Transição Atômica)
    activate_res = client.post(f"/policies/{draft_id}/activate")
    assert activate_res.status_code == 200
    activated_data = activate_res.json()
    assert activated_data["status"] == "ACTIVE"

    # 4. Confirma que a nova versão agora é a ACTIVE retornada
    active_now = client.get("/policies/active").json()
    assert active_now["version"] == test_ver

    from src.core.database import SessionLocal
    from src.models.entities import PolicyVersion
    db = SessionLocal()
    try:
        oficial = db.query(PolicyVersion).filter(PolicyVersion.version == "2026.1-AMIL-IT-ACORDOS").first()
        if not oficial:
            oficial = db.query(PolicyVersion).filter(PolicyVersion.version == "2026.OFICIAL").first()
        if oficial:
            db.query(PolicyVersion).filter(PolicyVersion.tenant_id == oficial.tenant_id).update({"status": "INACTIVE"})
            oficial.status = "ACTIVE"
            db.commit()
    finally:
        db.close()

def test_process_upload_endpoint():
    # Cria PDF sintético válido em memória com PyMuPDF
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Petição Inicial. Ação de Reembolso de Saúde. Valor R$ 35.000,00.")
    fake_pdf_content = doc.tobytes()
    doc.close()
    
    files = {
        "file": ("autos_processo.pdf", fake_pdf_content, "application/pdf")
    }
    data = {
        "cnj_number": "0001234-56.2025.8.26.0100",
        "beneficiary_name": "Carlos Eduardo Pereira",
        "operator_name": "Vida Plena Saúde"
    }
    
    response = client.post("/processes/upload", data=data, files=files)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] in ["PROCESSING", "SUCCESS"]
    assert res_json["total_pages"] >= 1

def test_hitl_queue_and_resolution_endpoints():
    # 1. Lista a fila HITL
    queue_res = client.get("/hitl/queue")
    assert queue_res.status_code == 200
    queue = queue_res.json()
    assert len(queue) >= 1
    review_id = queue[0]["review_id"]

    # 2. Operador resolve a pendência
    resolution_payload = {
        "decision": "APPROVED_AGREEMENT",
        "operator_notes": "Nota fiscal conferida manualmente no documento em anexo às fls. 45."
    }
    resolve_res = client.post(f"/hitl/{review_id}/resolve", json=resolution_payload)
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "success"

def test_process_multi_pdf_upload_endpoint():
    # Cria PDF 1: Petição Inicial
    doc1 = fitz.open()
    p1 = doc1.new_page()
    p1.insert_text((50, 50), "EXCELENTÍSSIMO JUIZ. Petição Inicial de Reembolso. Valor da causa R$ 28.000,00.")
    pdf1_bytes = doc1.tobytes()
    doc1.close()

    # Cria PDF 2: Nota Fiscal / Desembolso
    doc2 = fitz.open()
    p2 = doc2.new_page()
    p2.insert_text((50, 50), "DANFE / NOTA FISCAL DE SERVIÇOS MÉDICOS. Valor Pago: R$ 28.000,00. Quitado.")
    pdf2_bytes = doc2.tobytes()
    doc2.close()

    # Cria PDF 3: Negativa da Operadora
    doc3 = fitz.open()
    p3 = doc3.new_page()
    p3.insert_text((50, 50), "COMUNICADO DE INDEFERIMENTO / NEGATIVA. Solicitamos indeferimento do reembolso.")
    pdf3_bytes = doc3.tobytes()
    doc3.close()

    files = [
        ("files", ("01_peticao_inicial.pdf", pdf1_bytes, "application/pdf")),
        ("files", ("02_nota_fiscal.pdf", pdf2_bytes, "application/pdf")),
        ("files", ("03_negativa_operadora.pdf", pdf3_bytes, "application/pdf")),
    ]
    data = {
        "cnj_number": "5008888-11.2025.8.26.0100",
        "beneficiary_name": "Ana Paula Rodrigues",
        "operator_name": "Grupo Amil"
    }

    response = client.post("/processes/upload", data=data, files=files)
    assert response.status_code == 200
    res_json = response.json()
    assert res_json["status"] == "SUCCESS"
    assert res_json["documents_count"] == 3
    assert res_json["total_pages"] == 3
    assert len(res_json["documents_summary"]) == 3
    assert res_json["cnj_number"] == "5008888-11.2025.8.26.0100"
