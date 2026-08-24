import pytest
from src.core.config import settings

@pytest.fixture(autouse=True)
def disable_remote_llm_during_tests(monkeypatch):
    """
    Garante que os testes automatizados executem de forma determinística e ultrarrápida,
    sem timeout de rede ou chamadas externas a APIs de terceiros.
    """
    monkeypatch.setattr(settings, "OPENROUTER_API_KEY", "")

@pytest.fixture
def db_session_fixture():
    from src.core.database import SessionLocal, init_db
    from src.models.entities import Tenant, Policy, PolicyVersion, generate_uuid
    from datetime import datetime, timezone
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

    test_rules_payload = {
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

    if p_ver:
        p_ver.status = "ACTIVE"
        p_ver.activated_at = datetime.now(timezone.utc)
        p_ver.structured_rules = test_rules_payload
        db.commit()
    else:
        p_ver = PolicyVersion(
            id=generate_uuid(),
            tenant_id=tenant.id,
            policy_id=policy.id,
            version="2026.1",
            status="ACTIVE",
            activated_at=datetime.now(timezone.utc),
            file_hash_sha256="fake_sha",
            pdf_storage_path="fake_path.pdf",
            structured_rules=test_rules_payload
        )
        db.add(p_ver)
        db.commit()

    db.query(PolicyVersion).filter(
        PolicyVersion.tenant_id == tenant.id,
        PolicyVersion.id != p_ver.id
    ).update({"status": "INACTIVE"})
    db.commit()

    yield db
    db.close()

