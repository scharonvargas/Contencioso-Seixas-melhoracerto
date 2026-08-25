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

    # 0. Captura versão ativa original
    original_active = client.get("/policies/active").json()
    original_version = original_active.get("version")

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
        if original_version:
            orig = db.query(PolicyVersion).filter(PolicyVersion.version == original_version).first()
            if orig:
                db.query(PolicyVersion).filter(PolicyVersion.tenant_id == orig.tenant_id).update({"status": "INACTIVE"})
                orig.status = "ACTIVE"
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
    assert res_json["cnj_number"] == "5008888-11.2025.8.26.0100"


def test_process_decision_lifecycle():
    # 1. Cria um processo para teste
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Petição Inicial. Ação de Saúde. R$ 5.000,00.")
    fake_pdf = doc.tobytes()
    doc.close()

    upload_res = client.post(
        "/processes/upload",
        data={"cnj_number": "7777777-11.2026.8.26.0100", "beneficiary_name": "Decisao Teste"},
        files={"file": ("teste_decisao.pdf", fake_pdf, "application/pdf")}
    )
    assert upload_res.status_code == 200
    proc_id = upload_res.json()["process_id"]

    # 2. Testa Aprovação
    approve_res = client.post(f"/processes/{proc_id}/decide", json={
        "decision": "APPROVE",
        "operator_notes": "Aprovado com sucesso.",
        "proposal_amount": 4000.0,
        "operator_name": "Dr. Silva"
    })
    assert approve_res.status_code == 200
    assert approve_res.json()["new_status"] == "APPROVED"

    # 3. Testa Envio p/ HITL
    hitl_res = client.post(f"/processes/{proc_id}/decide", json={
        "decision": "SEND_TO_HITL",
        "operator_notes": "Falta documento legível.",
        "operator_name": "Dr. Silva"
    })
    assert hitl_res.status_code == 200
    assert hitl_res.json()["new_status"] == "REQUIRES_HUMAN_REVIEW"

    # 4. Testa Rejeição
    reject_res = client.post(f"/processes/{proc_id}/decide", json={
        "decision": "REJECT",
        "operator_notes": "Teto excedido e matéria vedada.",
        "operator_name": "Dr. Silva"
    })
    assert reject_res.status_code == 200
    assert reject_res.json()["new_status"] == "REJECTED"

    # 5. Testa Reabertura do Processo do Histórico para Inbox
    reopen_res = client.post(f"/processes/{proc_id}/reopen", json={
        "reason": "Nova prova documental juntada aos autos.",
        "operator_name": "Dr. Silva"
    })
    assert reopen_res.status_code == 200
    assert reopen_res.json()["new_status"] == "EVALUATED"


def test_process_scope_filtering_and_bulk_actions():
    # 1. Cria 2 processos sintéticos
    doc = fitz.open()
    p = doc.new_page()
    p.insert_text((50, 50), "Petição Inicial. Ação Teste. R$ 3.000,00.")
    fake_pdf = doc.tobytes()
    doc.close()

    res1 = client.post(
        "/processes/upload",
        data={"cnj_number": "8888888-01.2026.8.26.0100", "beneficiary_name": "Bulk Teste 1"},
        files={"file": ("bulk1.pdf", fake_pdf, "application/pdf")}
    )
    res2 = client.post(
        "/processes/upload",
        data={"cnj_number": "8888888-02.2026.8.26.0100", "beneficiary_name": "Bulk Teste 2"},
        files={"file": ("bulk2.pdf", fake_pdf, "application/pdf")}
    )
    p1_id = res1.json()["process_id"]
    p2_id = res2.json()["process_id"]

    # 2. Testa Aprovação em Lote
    bulk_res = client.post("/processes/bulk-approve", json={
        "process_ids": [p1_id, p2_id],
        "operator_name": "Dr. Coordenador",
        "operator_notes": "Aprovados em lote."
    })
    assert bulk_res.status_code == 200
    assert bulk_res.json()["approved_count"] == 2

    # 3. Testa Filtragem por Scope
    inbox_res = client.get("/processes?scope=inbox")
    assert inbox_res.status_code == 200
    inbox_ids = [p["process_id"] for p in inbox_res.json()]
    assert p1_id not in inbox_ids
    assert p2_id not in inbox_ids

    history_res = client.get("/processes?scope=history")
    assert history_res.status_code == 200
    hist_ids = [p["process_id"] for p in history_res.json()]
    assert p1_id in hist_ids
    assert p2_id in hist_ids

    # 4. Testa Exportação CSV
    csv_res = client.get("/processes/export/csv?scope=history")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "CNJ" in csv_res.text


