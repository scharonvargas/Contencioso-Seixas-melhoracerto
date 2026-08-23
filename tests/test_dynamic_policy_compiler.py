import pytest
import fitz
from src.rule_engine.policy_compiler import DynamicPolicyCompiler
from src.rule_engine.deterministic_engine import DeterministicRuleEngine

def test_dynamic_policy_compilation_from_custom_pdf():
    # Cria em memória um PDF de manual customizado enviado pelo usuário
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text(
        (50, 50),
        "MANUAL DE DIRETRIZES DE ACORDOS - HOSPITAL SANTA HELENA 2026\n\n"
        "Critério 1: Somente serão objeto de acordo solicitações de reembolso com valor de até R$ 45.000,00.\n\n"
        "Critério 2: É indispensável a comprovação documental do laudo de biópsia prévio assinado por médico patologista.\n\n"
        "Critério 3: O paciente deve ter histórico de negativa formal pela operadora no prazo de até 90 dias antes do ajuizamento.\n"
    )
    pdf_bytes = doc.tobytes()

    # 1. Extração do texto
    extracted_text = DynamicPolicyCompiler.extract_text_from_pdf(pdf_bytes)
    assert "MANUAL DE DIRETRIZES" in extracted_text
    assert "Critério 1" in extracted_text

    # 2. Compilação dinâmica para regras estruturadas (Zero Hardcoded Rules)
    compiled_policy = DynamicPolicyCompiler.compile_from_pdf_text(
        pdf_text=extracted_text,
        policy_name="Norma Customizada Santa Helena",
        version="2026.Custom"
    )

    assert compiled_policy.total_criteria_extracted == 3
    assert len(compiled_policy.rules) == 3
    
    # Critério 1 deve ter extraído a condição de teto financeiro de R$ 45.000,00 dinamicamente do texto
    rule1 = compiled_policy.rules[0]
    assert rule1.rule_code == "CRITERIO_001"
    assert "<=" in rule1.condition
    assert rule1.condition["<="][1] == 45000.0

    # Critério 2 deve ser a biópsia
    rule2 = compiled_policy.rules[1]
    assert rule2.rule_code == "CRITERIO_002"
    assert "biópsia" in rule2.description.lower()

    # 3. Execução das regras dinâmicas no motor determinístico
    structured_rules = {
        "policy_version_id": compiled_policy.version,
        "rules": [r.model_dump() for r in compiled_policy.rules]
    }
    engine = DeterministicRuleEngine(structured_rules)

    # Caso 1: Fatos que atendem aos critérios dinâmicos extraídos do PDF
    case_facts_pass = {
        "financial": {
            "requested_amount": 40000.0,
            "evidence": {"document_type": "PETICAO_INICIAL", "page_number": 1}
        },
        "facts": {
            "criterio_002": {
                "comprovado": True,
                "evidence": {"document_type": "LAUDO_BIOPSIA", "page_number": 3}
            },
            "criterio_003": {
                "comprovado": True,
                "evidence": {"document_type": "NEGATIVA", "page_number": 4}
            }
        }
    }

    result = engine.evaluate("proc_custom_1", case_facts_pass)
    assert result.overall_verdict == "ELIGIBLE"
    assert len(result.rule_results) == 3
    assert all(r.status == "PASS" for r in result.rule_results)

    # Caso 2: Fatos que violam o teto extraído do PDF (R$ 50.000 > R$ 45.000)
    case_facts_fail = {
        "financial": {
            "requested_amount": 50000.0,
            "evidence": {"document_type": "PETICAO_INICIAL", "page_number": 1}
        },
        "facts": {
            "criterio_002": {
                "comprovado": True,
                "evidence": {"document_type": "LAUDO_BIOPSIA", "page_number": 3}
            },
            "criterio_003": {
                "comprovado": True,
                "evidence": {"document_type": "NEGATIVA", "page_number": 4}
            }
        }
    }

    result_fail = engine.evaluate("proc_custom_2", case_facts_fail)
    assert result_fail.overall_verdict == "INELIGIBLE"
    assert result_fail.rule_results[0].status == "FAIL"
