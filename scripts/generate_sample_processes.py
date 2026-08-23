"""
scripts/generate_sample_processes.py
Gerador de Processos Judiciais de Demonstração em PDF com dados realistas (Petições, Laudos, NFs, Negativas).
"""

import sys
import os
from pathlib import Path
import random
import fitz

def generate_sample_judicial_case(output_path: str, pages_count: int = 50, scenario: str = "ELIGIBLE"):
    """
    Gera um PDF realista de processo judicial brasileiro com N páginas para testes e benchmarking.
    Cenários: 'ELIGIBLE', 'INELIGIBLE_AMOUNT', 'MISSING_RECEIPT', 'INCONCLUSIVE'.
    """
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    doc = fitz.open()

    cnj_num = f"{random.randint(1000000, 9999999)}-{random.randint(10, 99)}.2025.8.26.0100"
    author_name = random.choice(["Carlos Eduardo Pereira", "Mariana Albuquerque Costa", "Fernando Henrique Silveira", "Juliana Mendes Rocha"])
    operator_name = "Vida Plena Saúde S.A."
    
    if scenario == "ELIGIBLE":
        requested_amount = 35000.0
        paid_amount = 35000.0
        has_receipt = True
        has_denial = True
    elif scenario == "INELIGIBLE_AMOUNT":
        requested_amount = 85000.0 # Excede teto de 60k
        paid_amount = 85000.0
        has_receipt = True
        has_denial = True
    elif scenario == "MISSING_RECEIPT":
        requested_amount = 28000.0
        paid_amount = 0.0
        has_receipt = False # Sem nota fiscal
        has_denial = True
    else:
        requested_amount = 40000.0
        paid_amount = 40000.0
        has_receipt = True
        has_denial = False # Sem negativa prévia

    # 1. PÁGINA 1: Petição Inicial
    p1 = doc.new_page()
    p1.insert_text(
        (50, 50),
        f"EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO DA 10ª VARA CÍVEL DA COMARCA DA CAPITAL - SP\n\n"
        f"PROCESSO CNJ Nº: {cnj_num}\n"
        f"AÇÃO ORDINÁRIA DE OBRIGAÇÃO DE FAZER C/C REEMBOLSO DE DESPESAS MÉDICAS\n\n"
        f"AUTOR: {author_name}, brasileiro, portador do CPF nº 123.456.789-00.\n"
        f"RÉU: {operator_name}, operadora de planos de saúde, inscrita no CNPJ 12.345.678/0001-99.\n\n"
        f"DOS FATOS:\n"
        f"O Autor é beneficiário titular do plano de saúde administrado pela Ré. Em razão de diagnóstico clínico "
        f"especializado, necessitou de tratamento médico contínuo prescrito pelo médico assistente, o qual foi indevidamente "
        f"negado pela operadora na via administrativa.\n\n"
        f"DO PEDIDO:\n"
        f"Requer a condenação da Ré ao reembolso integral da quantia desembolsada no valor total de R$ {requested_amount:,.2f}.\n"
        f"Dá-se à causa o valor de R$ {requested_amount:,.2f}.\n\n"
        f"Termos em que pede deferimento.\n"
        f"São Paulo, 15 de Janeiro de 2025.\n"
        f"Dr. Advogado OAB/SP 123.456"
    )

    # 2. PÁGINA 2: Procuração
    p2 = doc.new_page()
    p2.insert_text(
        (50, 50),
        f"PROCURAÇÃO AD JUDICIA ET EXTRA\n\n"
        f"OUTORGANTE: {author_name}, CPF 123.456.789-00.\n"
        f"OUTORGADO: Sociedade de Advogados Associados, OAB/SP 9999.\n"
        f"PODERES: Pelo presente instrumento, confere amplos poderes para o foro em geral da cláusula ad judicia..."
    )

    # 3. PÁGINA 3: Relatório Médico Circunstanciado
    p3 = doc.new_page()
    p3.insert_text(
        (50, 50),
        f"RELATÓRIO MÉDICO CIRCUNSTANCIADO E PRESCRIÇÃO CLÍNICA\n\n"
        f"PACIENTE: {author_name}\n"
        f"DIAGNÓSTICO: Transtorno do Espectro Autista - CID-10 F84.0.\n\n"
        f"INDICAÇÃO TERAPÊUTICA:\n"
        f"O paciente apresenta necessidade imperiosa e urgente de acompanhamento multidisciplinar com Terapia ABA "
        f"(Análise do Comportamento Aplicada) na intensidade de 20 horas semanais, além de Fonoaudiologia e Terapia Ocupacional.\n"
        f"Tratamento contínuo e por tempo indeterminado.\n\n"
        f"Dr. Roberto Silva Santos - Médico Neurologista\n"
        f"CRM/SP 999.888 - RQE 4455"
    )

    # 4. PÁGINA 4: Negativa Administrativa
    p4 = doc.new_page()
    if has_denial:
        p4.insert_text(
            (50, 50),
            f"COMUNICADO DE NEGATIVA DE COBERTURA ADMINISTRATIVA\n\n"
            f"Prezado(a) {author_name},\n"
            f"Protocolo de Atendimento: 20250819-994411\n"
            f"Em atenção à solicitação de reembolso de despesas médicas nº 887766, informamos que o procedimento "
            f"solicitação não autorizada por não preencher as Diretrizes de Utilização do Rol da ANS.\n\n"
            f"Atenciosamente,\n"
            f"Central de Regulação Médica - {operator_name}"
        )
    else:
        p4.insert_text((50, 50), "Documento de tramitação interna sem registro de negativa prévia.")

    # 5. PÁGINA 5: Nota Fiscal e Recibo de Desembolso
    p5 = doc.new_page()
    if has_receipt:
        p5.insert_text(
            (50, 50),
            f"DANFE - DOCUMENTO AUXILIAR DA NOTA FISCAL DE SERVIÇOS ELETRÔNICA\n\n"
            f"NÚMERO DA NOTA: 00004521 - SÉRIE: 1 - EMISSÃO: 10/01/2025\n"
            f"PRESTADOR: Clínica Terapêutica NeuroVida Ltda - CNPJ: 12.345.678/0001-99\n"
            f"TOMADOR: {author_name} - CPF: 123.456.789-00\n\n"
            f"DISCRIMINAÇÃO DOS SERVIÇOS:\n"
            f"Sessões Especializadas de Terapia ABA Comportamental (CID-10 F84.0).\n\n"
            f"VALOR TOTAL DA NOTA FISCAL: R$ {paid_amount:,.2f}\n"
            f"FORMA DE PAGAMENTO: PIX Integral em 10/01/2025 - Autenticação Bancária: 9944118877\n"
            f"VALOR LÍQUIDO RECEBIDO: R$ {paid_amount:,.2f}"
        )
    else:
        p5.insert_text((50, 50), "Orçamento não quitado / Documento sem valor fiscal comprovado.")

    # Páginas complementares até atingir a meta
    for p_idx in range(6, pages_count + 1):
        p_extra = doc.new_page()
        p_extra.insert_text(
            (50, 50),
            f"PÁGINA PROCESSUAL {p_idx} DE {pages_count}\n\n"
            f"Autos do Processo Judicial Eletrônico CNJ: {cnj_num}\n"
            f"Certidão de juntada e publicações no Diário de Justiça Eletrônico (DJe).\n"
            f"Documento assinado digitalmente conforme MP nº 2.200-2/2001."
        )

    doc.save(output_path)
    doc.close()
    print(f"Processo gerado com sucesso: {output_path} ({pages_count} páginas | Cenário: {scenario})")

if __name__ == "__main__":
    generate_sample_judicial_case("sample_data/processo_elegivel_50p.pdf", pages_count=50, scenario="ELIGIBLE")
    generate_sample_judicial_case("sample_data/processo_ineligivel_valor_50p.pdf", pages_count=50, scenario="INELIGIBLE_AMOUNT")
    generate_sample_judicial_case("sample_data/processo_sem_recibo_hitl_50p.pdf", pages_count=50, scenario="MISSING_RECEIPT")
