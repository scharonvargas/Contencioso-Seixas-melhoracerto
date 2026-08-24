"""
tests/test_theme_classification_and_cross_document.py
Testes rigorosos para validação da classificação dinâmica de temas e cruzamento multi-documental.
"""

import pytest
import fitz
import uuid
from src.validators.brazilian_validators import BrazilianDomainValidator
from src.services.process_service import ProcessExecutionService
from src.models.entities import Tenant, Policy, PolicyVersion, Process, generate_uuid
from src.core.database import SessionLocal, init_db
from src.rule_engine.deterministic_engine import DeterministicRuleEngine
from src.rule_engine.policy_compiler import DynamicPolicyCompiler

def test_all_21_topics_affinity_classification():
    """
    Testa se o motor de afinidade de temas reconhece casos para cada um dos tópicos corporativos.
    """
    test_cases = [
        ("Terapia ABA e Integração Sensorial para menor com TEA F84", 1, "Terapias Especiais"),
        ("Necessidade de internação domiciliar home care com suporte ventilatório PAD", 2, "Home Care"),
        ("Fornecimento de medicamento antineoplásico pembrolizumabe fora do rol da ANS", 3, "Medicamentos"),
        ("Ação de cobrança e reembolso de despesas médico-hospitalares em prestador particular", 4, "Reembolso"),
        ("Negativa de atendimento de urgência sob alegação de prazo de carência de 180 dias", 5, "Carência"),
        ("Procedimento cirúrgico eletivo de gastroplastia bariátrica conforme DUT e ADI 7265", 6, "Cirurgias Eletivas"),
        ("Fornecimento de material especial OPME stent farmacológico para cirurgia cardíaca", 7, "OPME"),
        ("Solicitação de exame PET-SCAN oncológico de alta complexidade negado pela operadora", 8, "PET-SCAN"),
        ("Indisponibilidade de rede credenciada e ausência de prestador no município", 9, "Indisponibilidade de Rede"),
        ("Reajuste anual por sinistralidade abusivo e aumento de mensalidade acima da ANS", 10, "Reajustes Anuais"),
        ("Implante de bomba de insulina e fornecimento de órtese craniana capacetinho", 11, "Procedimentos Especiais"),
        ("Reajuste por faixa etária aos 59 anos sem parecer atuarial idôneo", 12, "Faixa Etária"),
        ("Contrato coletivo empresarial PME porte 1 cancelado indevidamente", 13, "Contratos PME"),
        ("Cancelamento por inadimplência sem notificação prévia válida recebida pelo titular", 14, "Cancelamento Inadimplência"),
        ("Rescisão unilateral imotivada de contrato de plano de saúde a pedido da operadora", 15, "Rescisão Unilateral"),
        ("Reativação contratual e inclusão de dependente após regularização de baixa do CNPJ", 16, "Reativação CNPJ"),
        ("Fraude de boleto com pagamento de boleto falso emitido por golpista", 17, "Fraude de Boleto"),
        ("Troca de titularidade e migração para plano individual com aproveitamento de carências", 18, "Plano Individual"),
        ("Manutenção de beneficiário demitido sem justa causa nos termos do artigo 30 da Lei 9656", 19, "Demitido"),
        ("Ação de indenização por danos morais decorrente de negativação indevida no SERASA", 20, "Danos Morais"),
        ("Cobrança indevida de mensalidades em aberto e execução de débitos prescritos", 21, "Cobrança de Mensalidades")
    ]

    for text, expected_num, topic_name in test_cases:
        norm_text = BrazilianDomainValidator.normalize_text_for_matching(text)
        topic_dict = {
            "topic_number": expected_num,
            "topic_name": topic_name,
            "requirements": [f"Requisitos para {topic_name}"],
            "prohibitions": []
        }
        score = BrazilianDomainValidator.score_topic_affinity(norm_text, topic_dict)
        assert score > 0, f"Falha na afinidade do tema {expected_num} ({topic_name}) para o texto: {text}"

def test_multi_document_cross_referencing_e2e(db_session_fixture):
    """
    Testa o cruzamento real de 4 documentos distintos que compõem um único processo:
    - Documento 1: Petição Inicial (Pede reembolso de R$ 15.000,00)
    - Documento 2: Laudo Médico (Prescreve tratamento cirúrgico)
    - Documento 3: Nota Fiscal / DANFE (Comprova desembolso de R$ 15.000,00)
    - Documento 4: Negativa Administrativa (Protocolo formal de recusa)
    """
    db = db_session_fixture
    tenant = db.query(Tenant).filter(Tenant.slug == "tenant-test-svc").first()

    # Cria a norma ativa corporativa no banco
    policy = db.query(Policy).filter(Policy.tenant_id == tenant.id).first()
    active_policy = db.query(PolicyVersion).filter(
        PolicyVersion.tenant_id == tenant.id,
        PolicyVersion.status == "ACTIVE"
    ).first()

    corporate_policy_rules = {
        "policy_version_id": "2026.IT-AMIL-FULL",
        "topics": [
            {
                "topic_number": 4,
                "topic_name": "Tratamento em Prestador Particular / Reembolso",
                "category": "ASSISTENCIAL",
                "requirements": [
                    "Comprovação de Desembolso / Nota Fiscal",
                    "Laudo ou Relatório Médico",
                    "Comprovação de Negativa Prévia"
                ],
                "prohibitions": [],
                "mandatory_clauses": []
            }
        ],
        "rules": [
            {
                "rule_code": "TEMA_04_TETO_DANO_MORAL",
                "title": "Teto de Indenização / Dano Moral (Reembolso)",
                "mandatory": True,
                "condition": {"<=": [{"var": "financial.moral_damage_amount"}, 10000.0]},
                "required_evidence_fields": ["financial"],
                "failure_message_template": "Dano moral excede o teto."
            },
            {
                "rule_code": "TEMA_04_EXIGE_DESEMBOLSO",
                "title": "Comprovação de Desembolso / Nota Fiscal (Reembolso)",
                "mandatory": True,
                "condition": {"==": [{"var": "financial.has_fiscal_receipt"}, True]},
                "required_evidence_fields": ["financial"],
                "failure_message_template": "Ausência de Nota Fiscal."
            },
            {
                "rule_code": "TEMA_04_EXIGE_LAUDO_MEDICO",
                "title": "Laudo / Relatório Médico (Reembolso)",
                "mandatory": True,
                "condition": {"==": [{"var": "treatment.has_medical_report"}, True]},
                "required_evidence_fields": ["treatment"],
                "failure_message_template": "Ausência de Laudo Médico."
            },
            {
                "rule_code": "TEMA_04_EXIGE_NEGATIVA",
                "title": "Comprovação de Negativa Prévia (Reembolso)",
                "mandatory": True,
                "condition": {"==": [{"var": "administrative_denial.has_administrative_denial"}, True]},
                "required_evidence_fields": ["administrative_denial"],
                "failure_message_template": "Ausência de Negativa."
            },
            {
                "rule_code": "TEMA_04_VEDACOES_EXPRESSAS",
                "title": "Ausência de Hipóteses Vedadas (Reembolso)",
                "mandatory": True,
                "condition": {"==": [{"var": "topics.topic_04.has_prohibition"}, False]},
                "required_evidence_fields": [],
                "failure_message_template": "Incide em vedação."
            },
            {
                "rule_code": "TEMA_04_REQUISITOS_CONFORMIDADE",
                "title": "Cumprimento dos Requisitos (Reembolso)",
                "mandatory": True,
                "condition": {"==": [{"var": "topics.topic_04.requirements_met"}, True]},
                "required_evidence_fields": [],
                "failure_message_template": "Requisitos não atendidos."
            }
        ]
    }

    active_policy.structured_rules = corporate_policy_rules
    db.commit()

    # Cria processo
    proc_id = generate_uuid()
    proc = Process(
        id=proc_id,
        tenant_id=tenant.id,
        cnj_number=f"{uuid.uuid4().hex[:7]}-12.2025.8.26.0100",
        beneficiary_name="Mariana Souza",
        operator_name="Amil Saúde",
        status="PENDING"
    )
    db.add(proc)
    db.commit()

    # Gera 4 PDFs sintéticos representando 4 documentos distintos juntados aos autos
    # Doc 1: Petição Inicial
    doc1 = fitz.open()
    p1 = doc1.new_page()
    p1.insert_text((50, 50), "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO\nPETIÇÃO INICIAL\nAção de Reembolso de Despesas Médicas em Prestador Particular.\nDá-se à causa o valor de R$ 15.000,00.")
    pdf1 = doc1.tobytes()

    # Doc 2: Laudo Médico
    doc2 = fitz.open()
    p2 = doc2.new_page()
    p2.insert_text((50, 50), "RELATÓRIO MÉDICO CIRCUNSTANCIADO\nPaciente Mariana Souza necessita de procedimento cirúrgico. Dr. Silva CRM 9988.")
    pdf2 = doc2.tobytes()

    # Doc 3: Nota Fiscal / DANFE
    doc3 = fitz.open()
    p3 = doc3.new_page()
    p3.insert_text((50, 50), "DANFE - NOTA FISCAL DE SERVIÇOS MÉDICOS\nPrestador Hospital Santa Lúcia\nValor Total dos Serviços: R$ 15.000,00 (Quitado).")
    pdf3 = doc3.tobytes()

    # Doc 4: Negativa Administrativa da Operadora
    doc4 = fitz.open()
    p4 = doc4.new_page()
    p4.insert_text((50, 50), "RESPOSTA À SOLICITAÇÃO - NEGATIVA DE COBERTURA\nProtocolo: 2025-998877\nInformamos o indeferimento administrativo da solicitação de reembolso.")
    pdf4 = doc4.tobytes()

    service = ProcessExecutionService(db=db)
    result = service.process_and_evaluate_multi(
        tenant_id=tenant.id,
        process_id=proc_id,
        pdf_files=[
            {"bytes": pdf1, "filename": "01_peticao_inicial.pdf"},
            {"bytes": pdf2, "filename": "02_laudo_medico.pdf"},
            {"bytes": pdf3, "filename": "03_nota_fiscal.pdf"},
            {"bytes": pdf4, "filename": "04_negativa_operadora.pdf"}
        ]
    )

    # Asserções de Cruzamento e Veredito
    assert result["process_id"] == proc_id
    assert result["documents_count"] == 4
    assert result["total_pages"] == 4
    assert "Tema 04" in result["identified_theme"]
    assert result["extracted_facts"]["financial"]["has_fiscal_receipt"] is True
    assert result["extracted_facts"]["treatment"]["has_medical_report"] is True
    assert result["extracted_facts"]["administrative_denial"]["has_administrative_denial"] is True
    assert result["verdict"] == "ELIGIBLE"
    assert all(r["status"] == "PASS" for r in result["rules"])
