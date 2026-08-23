"""
scripts/seed_db.py
Script de inicialização e carga de dados de demonstração (Tenant, Usuário Admin e Norma Ativa).
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import SessionLocal, init_db
from src.models.entities import Tenant, User, Policy, PolicyVersion, generate_uuid
from datetime import datetime, timezone

def seed_database():
    print("Inicializando tabelas do banco de dados...")
    init_db()
    
    db = SessionLocal()
    try:
        # 1. Verifica ou cria Tenant padrão
        tenant = db.query(Tenant).filter(Tenant.slug == "operadora-saude-padrao").first()
        if not tenant:
            tenant = Tenant(
                id=generate_uuid(),
                corporate_name="Operadora de Saúde Vida Plena S.A.",
                trade_name="Vida Plena Saúde",
                cnpj="12345678000199",
                slug="operadora-saude-padrao",
                is_active=True
            )
            db.add(tenant)
            db.commit()
            db.refresh(tenant)
            print(f"Tenant criado: {tenant.trade_name} ({tenant.id})")

        # 2. Usuário Administrador
        admin_user = db.query(User).filter(User.email == "admin@seixas-ai.com.br").first()
        if not admin_user:
            admin_user = User(
                id=generate_uuid(),
                tenant_id=tenant.id,
                full_name="Gestor Jurídico de Acordos",
                email="admin@seixas-ai.com.br",
                password_hash="pbkdf2:sha256:mock_hash",
                role="ADMIN",
                is_active=True
            )
            db.add(admin_user)
            db.commit()
            db.refresh(admin_user)
            print(f"Usuário Admin criado: {admin_user.email}")

        # 3. Norma Padrão e Versão ACTIVE
        policy = db.query(Policy).filter(Policy.tenant_id == tenant.id).first()
        if not policy:
            policy = Policy(
                id=generate_uuid(),
                tenant_id=tenant.id,
                name="Manual Interno de Acordos de Reembolso em Saúde",
                description="Norma interna vigente que estabelece os critérios operacionais exclusivos para celebração de acordos judiciais."
            )
            db.add(policy)
            db.commit()
            db.refresh(policy)

            # Versão 2026.1 ACTIVE
            active_version = PolicyVersion(
                id=generate_uuid(),
                tenant_id=tenant.id,
                policy_id=policy.id,
                version="2026.1",
                status="ACTIVE",
                file_hash_sha256="e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
                pdf_storage_path="policies/manual_acordos_2026_1.pdf",
                structured_rules={
                    "policy_version_id": "2026.1",
                    "rules": [
                        {
                            "rule_code": "RULE_001_DESEMBOLSO",
                            "title": "Comprovação de Desembolso Financeiro",
                            "description": "Exige Nota Fiscal ou Recibo idôneo com comprovação de pagamento.",
                            "mandatory": True,
                            "condition": {
                                "and": [
                                    {"==": [{"var": "financial.has_fiscal_receipt"}, True]},
                                    {">": [{"var": "financial.paid_amount_by_beneficiary"}, 0]}
                                ]
                            },
                            "required_evidence_fields": ["financial"],
                            "failure_message_template": "Ausência de Nota Fiscal com comprovação de pagamento efetivo."
                        },
                        {
                            "rule_code": "RULE_002_TETO_MAXIMO",
                            "title": "Teto Operacional de R$ 60.000,00",
                            "description": "Valor total pleiteado não pode ultrapassar R$ 60.000,00.",
                            "mandatory": True,
                            "condition": {"<=": [{"var": "financial.requested_amount"}, 60000.0]},
                            "required_evidence_fields": ["financial"],
                            "failure_message_template": "Valor pleiteado R$ {{financial.requested_amount}} excede o teto de R$ 60.000,00."
                        },
                        {
                            "rule_code": "RULE_003_RECUSA_PREVIA",
                            "title": "Negativa Administrativa Prévia",
                            "description": "Comprovação de solicitação prévia e recusa da operadora antes da ação.",
                            "mandatory": True,
                            "condition": {"==": [{"var": "administrative_denial.has_administrative_denial"}, True]},
                            "required_evidence_fields": ["administrative_denial"],
                            "failure_message_template": "Ausência de comprovação de negativa administrativa prévia da operadora."
                        }
                    ]
                },
                approved_by=admin_user.id,
                activated_at=datetime.now(timezone.utc)
            )
            db.add(active_version)
            db.commit()
            print(f"Norma Ativa criada e versionada: {policy.name} (Versão {active_version.version})")

        print("Seed do banco de dados concluído com sucesso!")
    finally:
        db.close()

if __name__ == "__main__":
    seed_database()
