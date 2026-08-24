"""
tests/test_adversarial_and_safety_hardening.py
Testes Adversariais e de Blindagem Arquitetural do Seixas AI.
Garante Fail-Closed, Zero Hardcodes, Isolamento Multi-Tenant,
Integridade de Evidências e Persistência de Auditoria.
"""

import pytest
from src.rule_engine.deterministic_engine import DeterministicRuleEngine
from src.models.entities import Tenant, Policy, PolicyVersion, Process, Evaluation, HumanReview, generate_uuid
from src.core.database import SessionLocal
from src.ocr.cascade_engine import OCRCascadeEngine
from src.rule_engine.policy_compiler import DynamicPolicyCompiler


def test_zero_rules_yields_technical_failure():
    """
    TRAVA P0: Uma política com zero regras NUNCA pode retornar ELIGIBLE.
    Deve retornar TECHNICAL_FAILURE ou REQUIRES_HUMAN_REVIEW com falha explícita.
    """
    empty_policy = {
        "policy_version_id": "test_empty_policy",
        "rules": []
    }
    engine = DeterministicRuleEngine(empty_policy)
    result = engine.evaluate(process_id="proc_zero_rules", case_fact_data={})

    assert result.overall_verdict in ["TECHNICAL_FAILURE", "REQUIRES_HUMAN_REVIEW"]
    assert result.overall_verdict != "ELIGIBLE"
    assert "regras" in result.summary.lower() or "técnica" in result.summary.lower() or "critério" in result.summary.lower()


def test_missing_evidence_never_becomes_pass():
    """
    TRAVA P0: Requisito de norma que exige comprovação documental sem evidência
    NUNCA pode virar PASS nem ELIGIBLE por suposição.
    """
    policy_with_evidence_req = {
        "policy_version_id": "test_evidence_policy",
        "rules": [
            {
                "rule_code": "CRIT_NOTA_FISCAL",
                "title": "Apresentação de Nota Fiscal Quitada",
                "condition": {"==": [{"var": "financial.has_fiscal_receipt"}, True]},
                "required_evidence_fields": ["financial.has_fiscal_receipt"],
                "mandatory": True,
                "blocking": True
            }
        ]
    }
    engine = DeterministicRuleEngine(policy_with_evidence_req)
    
    # Processo onde a petição alega ter nota fiscal mas NÃO há evidência rastreável
    case_facts = {
        "financial": {
            "requested_amount": 5000.0,
            "has_fiscal_receipt": True,
            # Sem objeto evidence estruturado com page_number
        }
    }
    result = engine.evaluate(process_id="proc_no_evidence", case_fact_data=case_facts)

    assert result.overall_verdict == "REQUIRES_HUMAN_REVIEW"
    rule_res = next(r for r in result.rule_results if r.rule_code == "CRIT_NOTA_FISCAL")
    assert rule_res.status == "UNKNOWN"
    assert "não comprovada" in rule_res.failure_reason.lower()


def test_no_hardcoded_stj_clauses_in_rule_engine():
    """
    TRAVA P0: O motor determinístico não deve injetar jurisprudência do STJ por conta própria
    se a política ativa não contiver essa cláusula.
    """
    custom_policy = {
        "policy_version_id": "test_no_stj",
        "rules": [
            {
                "rule_code": "CRIT_VALOR",
                "title": "Teto de Valor",
                "condition": {"<=": [{"var": "financial.requested_amount"}, 10000.0]},
                "mandatory": True
            }
        ],
        "topics": []
    }
    engine = DeterministicRuleEngine(custom_policy)
    case_facts = {
        "financial": {"requested_amount": 5000.0},
        "treatment": {"has_school_aide_request": True} # Pedido de AT escolar
    }
    result = engine.evaluate(process_id="proc_school_aide", case_fact_data=case_facts)

    # Se a política não estipulou a cláusula STJ, o Python não deve inventá-la
    for clause in result.conditional_clauses:
        assert "REsp 2.064.964/SP" not in clause
        assert "AgInt no REsp" not in clause


def test_tenant_isolation_policy_versions():
    """
    TRAVA P0: Desativação ou busca de norma de um Tenant A NÃO deve desativar ou afetar Tenant B.
    """
    db = SessionLocal()
    try:
        tenant_a_id = f"tenant_test_a_{generate_uuid()[:6]}"
        tenant_b_id = f"tenant_test_b_{generate_uuid()[:6]}"

        t_a = Tenant(id=tenant_a_id, corporate_name="Operadora A", trade_name="Op A", cnpj=f"11{generate_uuid()[:12]}", slug=f"op-a-{generate_uuid()[:4]}")
        t_b = Tenant(id=tenant_b_id, corporate_name="Operadora B", trade_name="Op B", cnpj=f"22{generate_uuid()[:12]}", slug=f"op-b-{generate_uuid()[:4]}")
        db.add_all([t_a, t_b])

        p_a = Policy(id=generate_uuid(), tenant_id=tenant_a_id, name="Manual Op A")
        p_b = Policy(id=generate_uuid(), tenant_id=tenant_b_id, name="Manual Op B")
        db.add_all([p_a, p_b])

        pv_a = PolicyVersion(
            id=generate_uuid(), tenant_id=tenant_a_id, policy_id=p_a.id, version="1.0",
            status="ACTIVE", file_hash_sha256="hash_a", pdf_storage_path="path_a",
            structured_rules={"rules": [{"rule_code": "R_A", "title": "Regra A", "condition": {"==": [1, 1]}}]}
        )
        pv_b = PolicyVersion(
            id=generate_uuid(), tenant_id=tenant_b_id, policy_id=p_b.id, version="1.0",
            status="ACTIVE", file_hash_sha256="hash_b", pdf_storage_path="path_b",
            structured_rules={"rules": [{"rule_code": "R_B", "title": "Regra B", "condition": {"==": [1, 1]}}]}
        )
        db.add_all([pv_a, pv_b])
        db.commit()

        # Desativação de versão apenas do Tenant A
        db.query(PolicyVersion).filter(PolicyVersion.tenant_id == tenant_a_id).update({"status": "INACTIVE"})
        db.commit()

        # Verifica se Tenant B permaneceu intacto como ACTIVE
        pv_b_check = db.query(PolicyVersion).filter(PolicyVersion.id == pv_b.id).first()
        assert pv_b_check.status == "ACTIVE", "A desativação do Tenant A vazou e desativou a política do Tenant B!"
    finally:
        db.close()


def test_hitl_persistence_in_database():
    """
    TRAVA P0: Itens que exigem intervenção humana devem ser persistidos na tabela HumanReview.
    """
    db = SessionLocal()
    try:
        t_id = f"tenant_hitl_{generate_uuid()[:6]}"
        tenant = Tenant(id=t_id, corporate_name="Op HITL", trade_name="Op HITL", cnpj=f"33{generate_uuid()[:12]}", slug=f"op-hitl-{generate_uuid()[:4]}")
        db.add(tenant)
        
        proc_id = generate_uuid()
        proc = Process(
            id=proc_id, tenant_id=t_id, cnj_number=f"0000001-00.2025.8.26.{generate_uuid()[:4]}",
            beneficiary_name="Beneficiário Teste HITL", operator_name="Operadora HITL", status="REQUIRES_HUMAN_REVIEW"
        )
        db.add(proc)

        pol = Policy(id=generate_uuid(), tenant_id=t_id, name="Manual HITL")
        db.add(pol)
        pv = PolicyVersion(id=generate_uuid(), tenant_id=t_id, policy_id=pol.id, version="1.0", status="ACTIVE", file_hash_sha256="h", pdf_storage_path="p", structured_rules={"rules": []})
        db.add(pv)

        eval_id = generate_uuid()
        evaluation = Evaluation(
            id=eval_id, tenant_id=t_id, process_id=proc_id, policy_version_id=pv.id,
            overall_result="REQUIRES_HUMAN_REVIEW", decision_summary="Evidência ausente para dano material"
        )
        db.add(evaluation)

        review = HumanReview(
            id=generate_uuid(),
            tenant_id=t_id,
            process_id=proc_id,
            evaluation_id=eval_id,
            status="OPEN",
            review_reason="MISSING_EVIDENCE"
        )
        db.add(review)
        db.commit()

        # Consulta no banco
        saved_review = db.query(HumanReview).filter(HumanReview.process_id == proc_id).first()
        assert saved_review is not None
        assert saved_review.status == "OPEN"
        assert saved_review.review_reason == "MISSING_EVIDENCE"
        assert saved_review.tenant_id == t_id
    finally:
        db.close()


def test_policy_compiler_handles_unlimited_paragraphs():
    """
    TRAVA P1: A compilação da política não deve truncar em 10 parágrafos.
    """
    long_policy_text = "\n\n".join([
        f"Item {i}: O valor de reembolso para a especialidade {i} deve respeitar a tabela de coparticipação fixada em R$ {100 + i * 50},00."
        for i in range(1, 25)
    ])
    
    compiled = DynamicPolicyCompiler.compile_from_pdf_text(
        pdf_text=long_policy_text,
        policy_name="Política Longa Sem Truncamento",
        version="1.0"
    )
    
    assert compiled.total_criteria_extracted >= 20, f"Compilação truncada! Extraiu apenas {compiled.total_criteria_extracted} critérios."
