import pytest
from src.validators.brazilian_validators import BrazilianDomainValidator
from src.extraction.schemas import (
    CaseFactModel,
    MedicalTreatmentFact,
    FinancialReimbursementFact,
    AdministrativeDenialFact,
    EvidenceSource
)
from src.rule_engine.deterministic_engine import DeterministicRuleEngine

def test_ponto1_urgency_clinical_lexicon_matching():
    """
    Ponto 1: Validação do léxico canônico de urgência/emergência (IT-AMIL-04).
    Garante que variações como UTI pediátrica, risco de morte e citação ao art. 12, V, c da Lei 9.656/98 sejam reconhecidas.
    """
    # 1. UTI pediátrica
    sample_text_1 = "Paciente com quadro de insuficiência respiratória necessitando de internação em leito de UTI pediátrica com urgência médica."
    res1 = BrazilianDomainValidator.match_clinical_urgency_expression(sample_text_1)
    assert res1["is_urgent"] is True
    assert "uti pediatrica" in res1["matched_terms"]
    assert "urgencia medica" in res1["matched_terms"]

    # 2. Risco de morte / dano irreparável
    sample_text_2 = "Laudo emitido atestando risco de vida e perigo de dano irreparável caso o procedimento cirúrgico não ocorra de imediato."
    res2 = BrazilianDomainValidator.match_clinical_urgency_expression(sample_text_2)
    assert res2["is_urgent"] is True
    assert "risco de vida" in res2["matched_terms"]
    assert "perigo de dano irreparavel" in res2["matched_terms"]

    # 3. Base legal canônica
    sample_text_3 = "Ação de obrigação de fazer fundamentada no art. 12, V, c da Lei 9.656/98 e súmula 597 do STJ referente à carência de 24 horas."
    res3 = BrazilianDomainValidator.match_clinical_urgency_expression(sample_text_3)
    assert res3["is_urgent"] is True
    assert "art 12 v c da lei 9656" in res3["matched_terms"]
    assert "sumula 597 do stj" in res3["matched_terms"]

def test_ponto2_tea_aba_two_axis_validator():
    """
    Ponto 2: Validador de Laudo Médico em 2 Eixos para Terapias Especiais / TEA (IT-AMIL-01).
    Eixo 1 (Documento Médico Idôneo) ∧ Eixo 2 (Método Terapêutico).
    """
    # Cenário Válido: Laudo neurológico + ABA + Terapia Ocupacional
    valid_snippet = (
        "Em anexo, Laudo Médico Neurológico da Dra. Mariana CRM/MA 4521 indicando que o menor "
        "necessita de tratamento contínuo pelo método ABA (Análise do Comportamento Aplicada) "
        "e Terapia Ocupacional com Integração Sensorial."
    )
    res_valid = BrazilianDomainValidator.validate_tea_medical_evidence(valid_snippet)
    assert res_valid["is_valid"] is True
    assert res_valid["has_medical_doc"] is True
    assert res_valid["has_tea_method"] is True
    assert "ABA" in res_valid["detected_methods"]
    assert "TERAPIA_OCUPACIONAL" in res_valid["detected_methods"]
    assert "INTEGRACAO_SENSORIAL" in res_valid["detected_methods"]

    # Cenário Inválido: Petição menciona método ABA, mas não possui menção a laudo/relatório médico
    invalid_snippet = "A parte autora requer a concessão de liminar para fornecimento do método ABA."
    res_invalid = BrazilianDomainValidator.validate_tea_medical_evidence(invalid_snippet)
    assert res_invalid["is_valid"] is False
    assert res_invalid["has_medical_doc"] is False
    assert res_invalid["has_tea_method"] is True

def test_ponto3_post_sentence_appeal_saving_calculation():
    """
    Ponto 3: Matriz Parametrizada Pós-Sentença / Recursal com cálculo de Deságio e Risco Recursal (+20% sucumbência).
    Caso TJAL 0700071: Condenação líquida R$ 6.788,18 com 50% de litisconsórcio passivo.
    """
    sentenced_total = 6788.18
    operator_share = 0.50 # Amil responde por 50%
    effective_liability = sentenced_total * 0.50 # R$ 3.394,09
    
    # Proposta com 75% da condenação da cota da operadora
    proposal_amount = round(effective_liability * 0.75, 2) # R$ 2.545,57

    saving_data = BrazilianDomainValidator.calculate_judicial_settlement_saving(
        sentenced_amount=sentenced_total,
        proposal_amount=proposal_amount,
        operator_share=operator_share,
        appeal_risk_fee=0.20
    )

    assert saving_data["is_within_authorized_range"] is True
    assert saving_data["effective_operator_liability"] == 3394.09
    assert saving_data["desagio_percentage"] == pytest.approx(25.0, 0.1)
    assert saving_data["saving_vs_sentence"] > 0
    assert saving_data["saving_vs_appeal_risk"] > saving_data["saving_vs_sentence"]

def test_ponto4_conditional_settlement_school_aide_exclusion():
    """
    Ponto 4: Resolução de Vedações Parciais e Contrapropostas Estruturadas (A.T. Escolar).
    Gera veredito CONDITIONALLY_ELIGIBLE com cláusula expressa de renúncia baseada no STJ REsp 2.064.964/SP.
    """
    sample_policy = {
        "policy_version_id": "it_amil_tea_2026",
        "topics": [
            {
                "topic_number": 1,
                "topic_name": "Terapias Especiais (TEA/ABA)",
                "mandatory_clauses": [
                    "RENUNCIA_EXPRESSA_AT_ESCOLAR: Proposta autorizada exclusivamente para terapias clínicas, condicionada à renúncia expressa quanto ao pedido de AT escolar."
                ]
            }
        ],
        "rules": [
            {
                "rule_code": "TEMA_01_LIMITE_VALOR",
                "title": "Teto Terapias Especiais",
                "condition": {"<=": [{"var": "financial.capped_amount"}, 7200.0]},
                "required_evidence_fields": ["financial"],
                "failure_message_template": "Valor excede R$ 7.200."
            },
            {
                "rule_code": "TEMA_01_LAUDO_MEDICO",
                "title": "Laudo Médico Especializado",
                "condition": {"==": [{"var": "treatment.has_valid_medical_prescription"}, True]},
                "required_evidence_fields": ["treatment"],
                "failure_message_template": "Laudo médico não comprovado."
            }
        ]
    }

    engine = DeterministicRuleEngine(sample_policy)

    fact_data = {
        "applicable_topic_num": 1,
        "treatment": {
            "treatment_type": "Terapia TEA/ABA",
            "has_school_aide_request": True, # Pede A.T. Escolar cumulado
            "evidence": {
                "document_type": "laudo_medico",
                "page_number": 12,
                "bounding_box": [100, 100, 200, 500],
                "text_snippet": "Laudo médico psiquiátrico prescrevendo psicoterapia ABA e acompanhamento terapêutico escolar."
            }
        },
        "financial": {
            "requested_amount": 5000.0,
            "moral_damage_amount": 2000.0,
            "evidence": {
                "document_type": "peticao_inicial",
                "page_number": 5,
                "bounding_box": [100, 100, 200, 500],
                "text_snippet": "Requer o pagamento de R$ 5.000,00."
            }
        }
    }

    result = engine.evaluate(process_id="proc_tea_at_escolar_01", case_fact_data=fact_data)

    assert result.overall_verdict == "CONDITIONALLY_ELIGIBLE"
    assert len(result.conditional_clauses) == 1
    assert "RENUNCIA_EXPRESSA_AT_ESCOLAR" in result.conditional_clauses[0]


def test_ponto5_damage_segregation_material_vs_moral():
    """
    Ponto 5: Segregação Contábil no Teto entre Dano Material (Reembolso) e Dano Moral.
    Garante que o teto da norma se aplique sobre o Dano Moral + Sucumbência, não bloqueando o dano material comprovado.
    """
    sample_policy = {
        "policy_version_id": "it_amil_reembolso_2026",
        "rules": [
            {
                "rule_code": "TEMA_11_LIMITE_VALOR",
                "title": "Teto Indenizatório de Dano Moral",
                "condition": {"<=": [{"var": "financial.capped_amount"}, 2000.0]},
                "required_evidence_fields": ["financial"],
                "failure_message_template": "Indenização excede o teto de R$ 2.000,00."
            },
            {
                "rule_code": "TEMA_11_COMPROVACAO_DOCUMENTAL",
                "title": "Recibo de Desembolso",
                "condition": {"==": [{"var": "financial.has_fiscal_receipt"}, True]},
                "required_evidence_fields": ["financial"],
                "failure_message_template": "Recibo fiscal não comprovado."
            }
        ]
    }

    engine = DeterministicRuleEngine(sample_policy)

    # Processo com R$ 6.000 de Dano Material comprovado + R$ 1.500 de Dano Moral (Total R$ 7.500)
    fact_data = {
        "applicable_topic_num": 11,
        "financial": {
            "requested_amount": 7500.0,
            "material_damage_amount": 6000.0,
            "moral_damage_amount": 1500.0,
            "has_fiscal_receipt": True,
            "evidence": {
                "document_type": "recibo_reembolso",
                "page_number": 8,
                "bounding_box": [100, 100, 200, 500],
                "text_snippet": "Comprovante de pagamento e nota fiscal de R$ 6.000,00 e indenização de R$ 1.500,00."
            }
        }
    }

    result = engine.evaluate(process_id="proc_segregacao_danos_01", case_fact_data=fact_data)

    assert result.overall_verdict == "ELIGIBLE"
    assert result.segregated_amounts["material_damage_amount"] == 6000.0
    assert result.segregated_amounts["moral_damage_amount"] == 1500.0
    assert result.segregated_amounts["requested_amount"] == 7500.0

def test_fraude_de_boleto_pre_sentenca_ineligible():
    """
    Caso TJAL 0700071-15.2024.8.02.0025: Petição inicial alegando golpe do boleto falso.
    Tema 17 (Fraude de Boleto): Veda expressamente acordo em fase pré-sentença.
    Veredito obrigatório: INELIGIBLE.
    """
    from src.rule_engine.policy_compiler import DynamicPolicyCompiler
    from scripts.seed_corporate_manual import CORPORATE_MANUAL_TEXT

    compiled = DynamicPolicyCompiler.compile_corporate_manual(
        pdf_text=CORPORATE_MANUAL_TEXT,
        policy_name="Instrução de Trabalho Acordos",
        version="2026.1-AMIL-IT-ACORDOS",
        file_hash="test_hash"
    )

    engine = DeterministicRuleEngine(compiled.model_dump())

    fact_data = {
        "identified_theme": "Tema 17: Fraude de Boleto",
        "applicable_topic_num": 17,
        "procedural_stage": "PRE_SENTENCA",
        "financial": {
            "requested_amount": 16788.18,
            "material_damage_amount": 6788.18,
            "moral_damage_amount": 10000.0,
            "has_fiscal_receipt": True,
            "evidence": {
                "document_type": "NOTA_FISCAL",
                "page_number": 31,
                "bounding_box": [100, 100, 200, 900],
                "text_snippet": "Boleto Safra R$ 6.788,18"
            }
        },
        "topics": {
            "topic_17": {
                "requirements_met": False,
                "has_prohibition": True,
                "evidence": {"document_type": "PETICAO_INICIAL", "page_number": 1}
            }
        }
    }

    result = engine.evaluate(process_id="proc_tjal_0700071", case_fact_data=fact_data)

    assert result.overall_verdict == "INELIGIBLE"
    assert any("Somente com Sentença de Procedência" in r.failure_reason for r in result.rule_results if r.status == "FAIL")

def test_luziane_rocha_carencia_moral_exceeded_ineligible():
    """
    Caso TJMA 0811884-29.2026.8.10.0001 (Luziane Rocha):
    Ação de Carência de Parto com pedido de R$ 15.000,00 a título de danos morais.
    Na norma ativa, o teto para Carência (Tema 4) é R$ 7.200,00.
    Veredito obrigatório: INELIGIBLE (TEMA_04_TETO_DANO_MORAL).
    """
    from src.rule_engine.policy_compiler import DynamicPolicyCompiler
    from scripts.seed_corporate_manual import CORPORATE_MANUAL_TEXT

    compiled = DynamicPolicyCompiler.compile_corporate_manual(
        pdf_text=CORPORATE_MANUAL_TEXT,
        policy_name="Instrução de Trabalho Acordos",
        version="2026.1-AMIL-IT-ACORDOS",
        file_hash="test_hash"
    )
    engine = DeterministicRuleEngine(compiled.model_dump())

    fact_data = {
        "identified_theme": "Tema 04: Carência",
        "applicable_topic_num": 4,
        "procedural_stage": "PRE_SENTENCA",
        "financial": {
            "requested_amount": 15000.0,
            "material_damage_amount": 0.0,
            "moral_damage_amount": 15000.0,
            "has_fiscal_receipt": False,
            "evidence": {"document_type": "PETICAO_INICIAL", "page_number": 45}
        },
        "topics": {
            "topic_04": {
                "requirements_met": True,
                "has_prohibition": False,
                "evidence": {"document_type": "PETICAO_INICIAL", "page_number": 1}
            }
        }
    }

    result = engine.evaluate(process_id="proc_luziane_0811884", case_fact_data=fact_data)
    assert result.overall_verdict == "INELIGIBLE"
    assert any(r.rule_code == "TEMA_04_TETO_DANO_MORAL" and r.status == "FAIL" for r in result.rule_results)

def test_viviane_meneses_atraso_moral_exceeded_ineligible():
    """
    Caso TJMA 0803074-22.2025.8.10.0059 (Viviane Meneses):
    Ação com pedido de R$ 20.000,00 de danos morais ('sugerindo-se o valor de R$ Vinte Mil Reais (R$ 20.000,00)').
    Na norma ativa, o teto para Atraso na Autorização (Tema 6) é R$ 7.200,00.
    Veredito obrigatório: INELIGIBLE (TEMA_06_TETO_DANO_MORAL).
    """
    from src.rule_engine.policy_compiler import DynamicPolicyCompiler
    from scripts.seed_corporate_manual import CORPORATE_MANUAL_TEXT

    compiled = DynamicPolicyCompiler.compile_corporate_manual(
        pdf_text=CORPORATE_MANUAL_TEXT,
        policy_name="Instrução de Trabalho Acordos",
        version="2026.1-AMIL-IT-ACORDOS",
        file_hash="test_hash"
    )
    engine = DeterministicRuleEngine(compiled.model_dump())

    fact_data = {
        "identified_theme": "Tema 06: Atraso na Autorização",
        "applicable_topic_num": 6,
        "procedural_stage": "PRE_SENTENCA",
        "financial": {
            "requested_amount": 20400.0,
            "material_damage_amount": 400.0,
            "moral_damage_amount": 20000.0,
            "has_fiscal_receipt": False,
            "evidence": {"document_type": "PETICAO_INICIAL", "page_number": 17}
        },
        "topics": {
            "topic_06": {
                "requirements_met": True,
                "has_prohibition": False,
                "evidence": {"document_type": "PETICAO_INICIAL", "page_number": 1}
            }
        }
    }

    result = engine.evaluate(process_id="proc_viviane_0803074", case_fact_data=fact_data)
    assert result.overall_verdict == "INELIGIBLE"
    assert any(r.rule_code == "TEMA_06_TETO_DANO_MORAL" and r.status == "FAIL" for r in result.rule_results)

def test_brazilian_moral_damage_extractor_forensic_patterns():
    """
    Testa a extração determinística de danos morais cobrindo padrões forenses de petições iniciais.
    """
    # 1. Sugestão de arbitramento com numeral e extenso
    text_1 = "indenização a título de Danos Morais ... Sugerindo-se assim o valor de R$ Vinte Mil Reais (R$ 20.000,00)"
    assert BrazilianDomainValidator.extract_moral_damage_from_text(text_1) == 20000.0

    # 2. Arbitramento judicial em item dos pedidos
    text_2 = "8 - A condenação da operadora de plano de saúde no pagamento de danos morais arbitrado pelo Juízo ao valor de R$ 15.000,00 (quinze mil reais)"
    assert BrazilianDomainValidator.extract_moral_damage_from_text(text_2) == 15000.0

    # 3. Dano moral sofrido em valor a R$ 10.000,00
    text_3 = "reparado o dano moral sofrido em valor a R$ 10.000,00 (dez mil reais)"
    assert BrazilianDomainValidator.extract_moral_damage_from_text(text_3) == 10000.0


