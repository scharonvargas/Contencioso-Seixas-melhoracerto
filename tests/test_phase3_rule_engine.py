import pytest
from src.rule_engine.deterministic_engine import DeterministicRuleEngine
from src.validators.brazilian_validators import BrazilianDomainValidator

@pytest.fixture
def sample_active_policy():
    return {
        "policy_version_id": "2026.1-NORM-SAUDE",
        "rules": [
            {
                "rule_code": "RULE_RECEIPT_MANDATORY",
                "title": "Comprovação de Desembolso",
                "mandatory": True,
                "condition": {"==": [{"var": "financial.has_fiscal_receipt"}, True]},
                "required_evidence_fields": ["financial"],
                "failure_message_template": "Ausência de Nota Fiscal ou comprovante idôneo."
            },
            {
                "rule_code": "RULE_MAX_AMOUNT",
                "title": "Teto Máximo de R$ 50.000",
                "mandatory": True,
                "condition": {"<=": [{"var": "financial.requested_amount"}, 50000.0]},
                "required_evidence_fields": ["financial"],
                "failure_message_template": "Valor solicitado R$ {{financial.requested_amount}} excede o teto."
            }
        ]
    }

def test_rule_engine_eligible_process(sample_active_policy):
    engine = DeterministicRuleEngine(sample_active_policy)
    
    case_facts = {
        "financial": {
            "requested_amount": 25000.0,
            "has_fiscal_receipt": True,
            "evidence": {"page_number": 10, "text_snippet": "NF 123 - R$ 25.000,00"}
        }
    }
    
    result = engine.evaluate("proc_123", case_facts)
    assert result.overall_verdict == "ELIGIBLE"
    assert len(result.rule_results) == 2
    assert all(r.status == "PASS" for r in result.rule_results)

def test_rule_engine_ineligible_excess_amount(sample_active_policy):
    engine = DeterministicRuleEngine(sample_active_policy)
    
    case_facts = {
        "financial": {
            "requested_amount": 80000.0,
            "has_fiscal_receipt": True,
            "evidence": {"page_number": 10, "text_snippet": "NF 123 - R$ 80.000,00"}
        }
    }
    
    result = engine.evaluate("proc_456", case_facts)
    assert result.overall_verdict == "INELIGIBLE"
    assert result.rule_results[1].status == "FAIL"
    assert "80000.0" in result.rule_results[1].failure_reason

def test_rule_engine_unknown_missing_evidence(sample_active_policy):
    engine = DeterministicRuleEngine(sample_active_policy)
    
    case_facts = {
        "financial": {
            "requested_amount": 10000.0,
            "has_fiscal_receipt": True,
            "evidence": None  # Evidência ausente
        }
    }
    
    result = engine.evaluate("proc_789", case_facts)
    assert result.overall_verdict == "REQUIRES_HUMAN_REVIEW"
    assert result.rule_results[0].status == "UNKNOWN"

def test_brazilian_validators():
    assert BrazilianDomainValidator.validate_cpf("11144477735") is True
    assert BrazilianDomainValidator.validate_cpf("11111111111") is False
    assert BrazilianDomainValidator.parse_brazilian_currency("R$ 1.500,50") == 1500.50
    assert BrazilianDomainValidator.validate_cid10("F84.0") is True
    assert BrazilianDomainValidator.validate_cid10("INVALID_CID") is False
