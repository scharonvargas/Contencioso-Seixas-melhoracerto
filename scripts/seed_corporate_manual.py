"""
scripts/seed_corporate_manual.py
Gera o PDF da Instrução de Trabalho do Grupo Amil fornecida pelo usuário,
extrai dinamicamente todos os 21 temas e registra como a Norma ACTIVE no banco.
"""

import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import fitz
import hashlib
from src.core.database import SessionLocal, init_db
from src.models.entities import Tenant, Policy, PolicyVersion, generate_uuid
from src.rule_engine.policy_compiler import DynamicPolicyCompiler

CORPORATE_MANUAL_TEXT = """
Grupo Amil — Contencioso de Massa
Instrução de Trabalho Acordos — Contencioso Cível de Massa

O que você vai encontrar nesta Instrução de Trabalho
Esta Instrução de Trabalho é complementar às Políticas internas do Grupo Amil e suas empresas e tem por objetivo estabelecer diretrizes, limites, alçadas e procedimentos para a celebração de acordos em ações judiciais cíveis, assegurando uniformidade na atuação entre o Departamento Jurídico e os escritórios externos, mitigação de riscos, otimização de custos e incremento de encerramentos com qualidade, em conformidade com normas internas e regulatórias.

Temas Assistenciais

1. Terapias Especiais:
Requisitos:
- Negociação para cobertura de terapias especiais com métodos usuais (ABA, Denver, Prompt, Pecs, Integração Sensorial, RTA), desde que estejam indicados no processo por meio de relatório médico.
- Limitação da carga horária a 40h semanais.
- Não cobrir AT (Acompanhamento Terapêutico).
- Não cobrir tratamento em prestador particular sem possibilidade futura de rede credenciada.
- Cobertura de tratamentos em clínica eventual somente com autorização expressa do Jurídico da Amil.
- Não cobrir por meio de reembolso integral.
Parâmetros do Acordo:
- Confirmação da liminar, limitada com as regras acima.
- Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
- Permitido: Negociação para cobertura de terapias especiais com métodos usuais (ABA, Denver, Prompt, Pecs, Integração Sensorial, RTA) independente da carga horária.
- Pagamento do valor da condenação com saving mínimo de 10%.
Não permitido acordo pré-Sentença nas seguintes hipóteses:
- Terapias cujo método não possui evidência científica (Mig, Treini, Padovan, Cuevas, Pediasuit, Therasuit, Floortime, Neurofeedback).

2. Home Care:
Requisitos:
- Quando a área técnica concorda com o PAD da liminar e indica celebração de acordo no RCA.
- Casos de óbito do beneficiário durante o processo, alta ou cancelamento do contrato.
- Após realização de perícia médica desfavorável. Não cobrir AT.
- Não cobrir tratamento em prestador particular sem autorização do advogado interno.
- Não cobrir por meio de reembolso integral.
- Não fechar acordo para cobertura de cuidador, nem medicamento domiciliar e nem itens de higiene pessoal.
Parâmetros do Acordo:
- Confirmação da liminar, limitada com as regras acima.
- Home Care atualizado conforme evolução médica.
- Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
- Pagamento do valor da condenação com saving mínimo de 10%.

3. Medicamento:
Requisitos:
- Cobertura de medicamentos com negativa Fora DUT/Fora Rol.
- Cobertura de medicamento antineoplásico.
- Cobertura de medicamento com tratamento já encerrado, na rede credenciada.
- Cobertura de medicamento na rede credenciada com contrato cancelado.
- Em casos de óbito do beneficiário e contrato excluído.
Parâmetros do Acordo:
- Confirmação da liminar, limitada com as regras acima.
- Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
- Pagamento do valor da condenação com saving mínimo de 10%.
Não permitido acordo pré-Sentença nas seguintes hipóteses:
- Cobertura de medicamento de alto custo (valor superior a R$ 100.000,00), salvo se dose única.
- Cobertura de medicamento experimental.
- Cobertura de medicamento off label de qualquer natureza.
- Cobertura de medicamento importado não nacionalizado.
- Cobertura de medicamento sem registro na ANVISA.
- Cobertura de medicamento para tratamento domiciliar, salvo antineoplásico.
- Cobertura de tratamento em prestador particular fora da rede.

4. Carência:
Requisitos:
- Comprovado no processo se tratar de Urgência e Emergência.
- Não haver requisitos de fraude ou Doença Pré-Existente (DLP).
- Liminar que tenha sido cumprida.
- Investigação de doença grave (ex: Câncer) sem DLP omitida.
- Procedimento de alto custo acima de R$ 100.000,00 exige autorização prévia.
Parâmetros do Acordo:
- Confirmação da liminar, limitada com as regras acima.
- Pagamento de até R$ 7.200,00 por dano moral + sucumbência.

5. Rol de Procedimentos e DUT:
Requisitos:
- Procedimento integralmente em conformidade com critérios da ADI nº 7.265 do STF.
- Não haja requisitos de fraude.
- Cumprimento de liminar.
- Acima de R$ 100.000,00 exige sinalização prévia.
Parâmetros do Acordo:
- Confirmação da liminar.
- Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
- Pós-sentença saving mínimo de 10%.

6. Atraso na Autorização:
Requisitos:
- Procedimento coberto e o objeto tenha sido somente a demora na autorização.
- Sem requisitos de fraude.
- Liminar cumprida.
Parâmetros do Acordo:
- Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
- Pós-sentença saving mínimo de 10%.

7. Pool de Cobertura (Outros temas):
Requisitos:
- PET-SCAN e PET/CT.
- OPME cirúrgico com fornecedor credenciado.
- TAVI.
Parâmetros do Acordo:
- Sem compromisso do prestador virar credenciado.
- Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Não permitido acordo pré-Sentença nas seguintes hipóteses:
- OPME não relacionado ao ato cirúrgico ou fornecedor não homologado.
- Transplantes.
- Tratamento em prestador particular ou reembolso integral.
- Bariátrica endoscópica.
- Fraude ao contrato.
- Fertilização in vitro.
- Internação de paciente SUS na rede privada.
- Procedimento estético.
- Exame genético Foundation One.

8. Rede de Atendimento:
Requisitos:
- Comprovação da ausência ou indisponibilidade da Rede Credenciada.
- Não ser tratamento continuado (ex: Quimioterapia ou TEA).
- Comprovação de tentativa de contato prévio via Call Center.
Parâmetros do Acordo:
- Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
- Pós-sentença saving mínimo de 10%.

9. Internação Psiquiátrica:
Requisitos:
- Beneficiário com alta médica e aceite de cobrança em coparticipação.
- Beneficiário com contrato ativo que aceite internação na rede credenciada.
Parâmetros do Acordo:
- Pagamento de até R$ 7.200,00 por dano moral + sucumbência.

10. OPME e Junta Médica:
Requisitos:
- Lente Intraocular já cumprida.
- Órtese craniana / capacetinho.
- Bomba de insulina (Tema 1316 STJ).
- Prótese peniana.
- Laudo pericial desfavorável para a operadora.
Parâmetros do Acordo:
- Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Não permitido acordo pré-Sentença nas seguintes hipóteses:
- Prótese customizada.
- Médicos ofensores.

Temas Não Assistenciais

11. Reajuste:
Requisitos:
- Parecer atuarial desfavorável.
Parâmetros do Acordo:
- Faixa etária: Desconto de 50% no índice de reajuste + devolução simples com saving mínimo de 25%.
- Anual/Sinistralidade: Substituição pelo índice da ANS + devolução simples com saving mínimo de 25%.
- Pós-condenação saving mínimo de 10%.

12. Cancelamento - Aviso Prévio e Multa Rescisória:
Requisitos:
- Contratos PME Porte 1 sem requisitos de fraude.
- Empresa representada pelo seu Sócio.
Parâmetros do Acordo:
- Rescisão contratual e inexigibilidade das mensalidades.
- Honorários de sucumbência de até R$ 2.000,00.
- Sem danos morais, salvo negativação comprovada.

13. Demais Cancelamentos (Inadimplência, Rescisão a Pedido):
Requisitos:
- Falha administrativa no cancelamento (ausência de notificação prévia).
Parâmetros do Acordo:
- Reativação do plano com pagamento da mensalidade atrasada.
- Pagamento de até R$ 7.200,00 por dano moral + sucumbência.

14. Rescisão Unilateral de Planos Coletivos Por Adesão:
Requisitos:
- Cancelamento a pedido da Operadora.
Parâmetros do Acordo:
- Sucumbência de até R$ 2.000,00.
- Em nenhuma hipótese haverá acordo para fornecer plano individual.

15. Cancelamento de Contrato Por Baixa do CNPJ:
Requisitos:
- Reativação do contrato com regularização do CNPJ.
Parâmetros do Acordo:
- Sucumbência de até R$ 2.000,00.

16. Movimentação Cadastral:
Requisitos:
- Falha administrativa/operacional na movimentação cadastral.
Parâmetros do Acordo:
- Sucumbência de até R$ 2.000,00.
Não permitido acordo nas seguintes hipóteses:
- Implantação de plano Pessoa Física.
- Downgrade ou Upgrade de Pessoa Física.

17. Fraude de Boleto:
Requisitos:
- Somente com Sentença de Procedência (não fazer acordo pré-sentença).
Parâmetros do Acordo:
- Reativação do contrato e negociação de valores com saving mínimo de 10%.

18. Reembolso:
Requisitos:
- Recusa em razão de pagamento parcelado no cartão de crédito.
- Insuficiência de rede de atendimento local comprovada.
- Atendimento de urgência/emergência fora da rede credenciada.
- Ausência de tabela contratual de reembolso.
Parâmetros do Acordo:
- Reembolso integral nos casos de ausência comprovada de rede.
- Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
- Se a diferença for inferior a R$ 10.000,00 fechar acordo direto.
- Saving mínimo de 10% sobre o valor da condenação.

19. Negativação do Nome (Sustação de Protesto):
Requisitos:
- Negativação indevida do beneficiário.
- Ausência de notificação prévia válida.
Parâmetros do Acordo:
- Baixa imediata da negativação.
- Devolução simples de valores pagos indevidamente.
- Pagamento de até R$ 3.000,00 por dano moral + sucumbência.

20. Documentos Obrigatórios:
Requisitos:
- Ação com objeto exclusivo de obtenção de documento sem cumulação de dano moral.
- Comprovação de recusa administrativa prévia.
Parâmetros do Acordo:
- Disponibilização do documento solicitado.
- Pagamento de até R$ 2.000,00 de sucumbência.

21. Mensalidade:
Requisitos:
- Indício de falha na cobrança durante a vigência do contrato.
Parâmetros do Acordo:
- Emissão de boletos corretos e reprocessamento.
- Pagamento de até R$ 2.000,00 por dano moral + sucumbência.

Rotinas e Atualização Sistêmicas de Negociação
Regras de Saving:
- Pós-sentença e pós-acórdão: saving mínimo de 10% sobre a condenação.
- Fraudes: casos NÃO são elegíveis a acordo.
- Impossibilidade absoluta de implantação de produtos individuais.
"""

def seed_corporate_policy_from_pdf():
    print("=" * 80)
    print("COMPILANDO MANUAL CORPORATIVO DE ACORDOS EM PDF (21 TEMAS)...")
    print("=" * 80)

    # 1. Gera o PDF do manual em storage_data/policies/
    policies_dir = Path("storage_data/policies")
    policies_dir.mkdir(parents=True, exist_ok=True)
    pdf_path = policies_dir / "Instrucao_Trabalho_Acordos_Amil_2026.pdf"

    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((40, 40), CORPORATE_MANUAL_TEXT)
    doc.save(str(pdf_path))
    doc.close()

    with open(pdf_path, "rb") as f:
        pdf_bytes = f.read()

    file_hash = hashlib.sha256(pdf_bytes).hexdigest()

    # 2. Compila dinamicamente sem regras hardcoded
    compiled = DynamicPolicyCompiler.compile_corporate_manual(
        pdf_text=CORPORATE_MANUAL_TEXT,
        policy_name="Instrução de Trabalho Acordos — Contencioso de Massa",
        version="2026.1-AMIL-IT-ACORDOS",
        file_hash=file_hash
    )

    print(f"Empresa Identificada : {compiled.company_name}")
    print(f"Versão da Norma      : {compiled.version}")
    print(f"Total de Temas       : {compiled.total_topics}")
    print(f"Total de Regras Logic: {len(compiled.all_rules)}")
    print("-" * 80)
    for t in compiled.topics:
        print(f" - Tema {t.topic_number:02d} [{t.category:<16}]: {t.topic_name} ({len(t.requirements)} reqs, {len(t.prohibitions)} vedações)")

    # 3. Persiste no Banco como a ÚNICA versão ACTIVE
    init_db()
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "operadora-saude-padrao").first()
        if not tenant:
            tenant = Tenant(
                id=generate_uuid(),
                corporate_name="Amil Assistência Médica Internacional S.A.",
                trade_name="Grupo Amil",
                cnpj="29309127000179",
                slug="operadora-saude-padrao"
            )
            db.add(tenant)
            db.commit()

        # Desativa todas as versões de teste / legadas em qualquer tenant
        all_active = db.query(PolicyVersion).all()
        for v in all_active:
            if v.version != compiled.version:
                v.status = "SUPERSEDED"

        tenants_to_seed = [tenant]
        for extra_t_id in ["tenant_saude_001", "tenant_001"]:
            t_extra = db.query(Tenant).filter(Tenant.id == extra_t_id).first()
            if t_extra and t_extra not in tenants_to_seed:
                tenants_to_seed.append(t_extra)

        structured_dict = {
            "policy_version_id": compiled.version,
            "company_name": compiled.company_name,
            "total_topics": compiled.total_topics,
            "general_rules": compiled.general_rules,
            "topics": [t.model_dump() for t in compiled.topics],
            "rules": compiled.all_rules
        }

        for t_target in tenants_to_seed:
            policy = db.query(Policy).filter(Policy.tenant_id == t_target.id).first()
            if not policy:
                policy = Policy(
                    id=generate_uuid(),
                    tenant_id=t_target.id,
                    name="Instrução de Trabalho Acordos — Contencioso Cível de Massa"
                )
                db.add(policy)
                db.commit()

            existing_v = db.query(PolicyVersion).filter(
                PolicyVersion.tenant_id == t_target.id,
                PolicyVersion.version == compiled.version
            ).first()

            if existing_v:
                existing_v.structured_rules = structured_dict
                existing_v.file_hash_sha256 = file_hash
                existing_v.status = "ACTIVE"
                p_version = existing_v
            else:
                new_v_id = generate_uuid()
                p_version = PolicyVersion(
                    id=new_v_id,
                    tenant_id=t_target.id,
                    policy_id=policy.id,
                    version=compiled.version,
                    status="ACTIVE",
                    file_hash_sha256=file_hash,
                    pdf_storage_path=str(pdf_path),
                    structured_rules=structured_dict
                )
                db.add(p_version)
            db.commit()

        print("\n" + "=" * 80)
        print("NORMA CORPORATIVA ATIVA CADASTRADA COM SUCESSO NO BANCO!")
        print(f"Policy ID: {p_version.id} | Status: ACTIVE")
        print("=" * 80)
    finally:
        db.close()

if __name__ == "__main__":
    seed_corporate_policy_from_pdf()
