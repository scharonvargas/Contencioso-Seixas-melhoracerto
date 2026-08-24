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

def test_corporate_manual_16_pages_compilation():
    sample_text = """
    Instrução de Trabalho Acordos - Contencioso Cível de Massa
    Grupo Amil
    
    1. Terapias Especiais:
    Requisitos:
    ➤ Negociação para cobertura de terapias especiais com métodos usuais (ABA, Denver, Prompt, Pecs, Integração Sensorial, RTA), desde que estejam indicados no processo por meio de relatório médico.
    ➤ Limitação da carga horária a 40h semanais
    ➤ Não cobrir AT (Acompanhamento Terapêutico).
    ➤ Não cobrir tratamento em prestador particular sem possibilidade futura de rede credenciada.
    Parâmetros do Acordo:
    ➤ Confirmação da liminar, limitada com as regras acima.
    ➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
    Acordos Pós Sentença (Quando não vamos recorrer):
    ➤ Pagamento do valor da condenação com saving mínimo de 10%.
    
    2. Home Care:
    Requisitos:
    ➤ Quando a área técnica concorda com o PAD da liminar.
    ➤ Casos de óbito do beneficiário durante o processo.
    Parâmetros do Acordo:
    ➤ Pagamento de até R$ 7.200,00 por dano moral.
    
    3. Medicamento:
    Requisitos:
    ➤ Cobertura de medicamentos com negativa Fora DUT/Fora Rol.
    ➤ Cobertura de medicamento antineoplásico.
    Não permitido acordo pré-Sentença nas seguintes hipóteses:
    ➤ Cobertura de medicamento de alto custo (valor superior a R$ 100.000,00).
    ➤ Cobertura de medicamento experimental.
    
    10. OPME e Junta Médica
    Requisitos:
    ➤ Casos de Lente Intraocular.
    ➤ Bomba de insulina (tema 1316 STJ).
    Parâmetros do Acordo:
    ➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
    
    11. Reajuste:
    Requisitos:
    ➤ Casos com parecer atuarial desfavorável.
    
    12. Cancelamento - Aviso Prévio e Multa rescisória
    Contratos PME porte 1
    Requisitos:
    ➤ Não ter requisitos de Fraude.
    ➤ A empresa estar corretamente representada pelo seu Sócio.
    
    17. Fraude de Boleto
    Requisitos:
    ➤ Não faremos acordo em casos pré-sentença.
    
    18. Reembolso
    Requisitos:
    ➤ Recusa de reembolso em razão de o pagamento ser parcelado no cartão de crédito.
    ➤ Demonstração de insuficiência de rede de atendimento.
    Parâmetros do Acordo:
    ➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
    
    21. Mensalidade
    Requisitos:
    ➤ Indício de falha na cobrança ou na comunicação ao beneficiário.
    """
    
    compiled = DynamicPolicyCompiler.compile_corporate_manual(
        pdf_text=sample_text,
        policy_name="Instrução de Trabalho Acordos Amil 2026",
        version="2026.IT-AMIL"
    )
    
    assert compiled.total_topics >= 8
    topics_dict = {t.topic_number: t for t in compiled.topics}
    
    assert 1 in topics_dict
    assert "Terapias Especiais" in topics_dict[1].topic_name
    assert len(topics_dict[1].requirements) >= 3
    assert len(topics_dict[1].agreement_parameters) >= 1
    
    assert 3 in topics_dict
    assert "Medicamento" in topics_dict[3].topic_name
    assert len(topics_dict[3].prohibitions) >= 1
    
    assert 10 in topics_dict
    assert "OPME" in topics_dict[10].topic_name
    
    assert 18 in topics_dict
    assert "Reembolso" in topics_dict[18].topic_name
    assert len(topics_dict[18].rules) >= 2

