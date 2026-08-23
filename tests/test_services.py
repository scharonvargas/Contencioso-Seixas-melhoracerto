import pytest
import fitz
import uuid
from src.core.database import SessionLocal, init_db
from src.models.entities import Tenant, User, Policy, PolicyVersion, Process, generate_uuid
from src.core.storage import StorageService
from src.services.process_service import ProcessExecutionService

@pytest.fixture
def db_session_fixture():
    init_db()
    db = SessionLocal()
    
    tenant = db.query(Tenant).filter(Tenant.slug == "tenant-test-svc").first()
    if not tenant:
        tenant = Tenant(
            id=generate_uuid(),
            corporate_name="Test Health Operator",
            trade_name="Test Operator",
            cnpj="99887766000100",
            slug="tenant-test-svc"
        )
        db.add(tenant)
        db.commit()

    policy = db.query(Policy).filter(Policy.tenant_id == tenant.id).first()
    if not policy:
        policy = Policy(
            id=generate_uuid(),
            tenant_id=tenant.id,
            name="Norma Teste"
        )
        db.add(policy)
        db.commit()

    p_ver = db.query(PolicyVersion).filter(
        PolicyVersion.tenant_id == tenant.id,
        PolicyVersion.version == "2026.1"
    ).first()

    if p_ver:
        p_ver.status = "ACTIVE"
        db.commit()
    else:
        p_ver = PolicyVersion(
            id=generate_uuid(),
            tenant_id=tenant.id,
            policy_id=policy.id,
            version="2026.1",
            status="ACTIVE",
            file_hash_sha256="fake_sha",
            pdf_storage_path="fake_path.pdf",
            structured_rules={
                "policy_version_id": "2026.1",
                "rules": [
                    {
                        "rule_code": "RULE_TEST_DESEMBOLSO",
                        "title": "Nota Fiscal Obrigatória",
                        "mandatory": True,
                        "condition": {"==": [{"var": "financial.has_fiscal_receipt"}, True]},
                        "required_evidence_fields": ["financial"],
                        "failure_message_template": "Ausência de Nota Fiscal."
                    }
                ]
            }
        )
        db.add(p_ver)
        db.commit()

    yield db
    db.close()

def test_storage_service_save_and_url():
    storage = StorageService(base_dir="./test_storage_dir")
    fake_pdf = b"%PDF-1.4 Mock content"
    
    path = storage.save_process_pdf("t1", "p1", fake_pdf, "autos.pdf")
    assert "autos.pdf" in path
    
    url = storage.get_presigned_view_url("t1/p1/autos.pdf")
    assert "/s3/" in url
    
    storage.delete_process_files("t1", "p1")

def test_process_execution_service(db_session_fixture):
    db = db_session_fixture
    tenant = db.query(Tenant).filter(Tenant.slug == "tenant-test-svc").first()
    
    # Cria processo com CNJ único e aleatório para garantir idempotência em testes repetidos
    proc_id = generate_uuid()
    unique_cnj = f"{uuid.uuid4().hex[:7]}-99.2025.8.26.0100"
    proc = Process(
        id=proc_id,
        tenant_id=tenant.id,
        cnj_number=unique_cnj,
        beneficiary_name="Beneficiário Teste",
        operator_name="Test Operator",
        status="PENDING"
    )
    db.add(proc)
    db.commit()

    # Cria PDF sintético em memória
    doc = fitz.open()
    p1 = doc.new_page()
    p1.insert_text((50, 50), "Petição Inicial. Ação de Reembolso de Saúde. Valor: R$ 12.000,00.")
    p2 = doc.new_page()
    p2.insert_text((50, 50), "DANFE - Nota Fiscal de Serviços. Prestador Hospital São Luiz. Valor R$ 12.000,00.")
    pdf_bytes = doc.tobytes()

    service = ProcessExecutionService(db=db)
    result = service.process_and_evaluate(
        tenant_id=tenant.id,
        process_id=proc_id,
        pdf_bytes=pdf_bytes,
        filename="processo_teste.pdf"
    )

    assert result["process_id"] == proc_id
    assert result["total_pages"] == 2
    assert result["verdict"] == "ELIGIBLE"
    assert result["rules"][0]["status"] == "PASS"

    # Confirma persistência no banco
    updated_proc = db.query(Process).filter(Process.id == proc_id).first()
    assert updated_proc.status == "EVALUATED"
    assert updated_proc.total_pages == 2
