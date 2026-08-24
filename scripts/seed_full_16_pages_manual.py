import os
import sys
sys.path.insert(0, os.path.abspath('.'))

from src.rule_engine.policy_compiler import DynamicPolicyCompiler
from src.core.database import SessionLocal
from src.models.entities import PolicyVersion, Tenant

full_16_pages_text = """
Instrução de Trabalho Acordos - Contencioso Cível de Massa
Grupo Amil

O que você vai encontrar nesta Instrução de Trabalho
Esta Instrução de Trabalho é complementar às Políticas internas do Grupo Amil e suas empresas e tem por objetivo estabelecer diretrizes, limites, alçadas e procedimentos para a celebração de acordos em ações judiciais cíveis, assegurando uniformidade na atuação entre o Departamento Jurídico e os escritórios externos, mitigação de riscos, otimização de custos e incremento de encerramentos com qualidade, em conformidade com normas internas e regulatórias.

Temas Assistenciais

1. Terapias Especiais:
Requisitos:
➤ Negociação para cobertura de terapias especiais com métodos usuais (ABA, Denver, Prompt, Pecs, Integração Sensorial, RTA), desde que estejam indicados no processo por meio de relatório médico.
➤ Limitação da carga horária a 40h semanais
➤ Não cobrir AT (Acompanhamento Terapêutico).
➤ Não cobrir tratamento em prestador particular sem possibilidade futura de rede credenciada.
➤ Cobertura de tratamentos em clínica eventual somente com autorização expressa do Jurídico da Amil.
➤ Não cobrir por meio de reembolso integral.
Parâmetros do Acordo:
➤ Confirmação da liminar, limitada com as regras acima.
➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Permitido: Negociação para cobertura de terapias especiais com métodos usuais (ABA, Denver, Prompt, Pecs, Integração Sensorial, RTA) independente da carga horária.
➤ Só será possível acordo independentemente do método após eventual decisão desfavorável do STJ.
➤ Só realizar acordo para terapias cujo método não possui evidência científica (Mig, Treini, Padovan, Cuevas, Pediasuit, Therasuit, Floortime, Neurofeedback), após eventual decisão do STJ, pois em tais casos, temos como recorrer em razão da ADI 7.265 do STF.
➤ Não realizar acordos para tratamento em prestador particular sem possibilidade futura de redirecionamento para rede credenciada.
➤ Cobertura de tratamentos em clínica eventual somente com autorização expressa do Jurídico da Amil.
➤ Só realizar acordo para cobertura/fornecimento de AT após eventual decisão desfavorável do STJ.
➤ Pagamento do valor da condenação com saving mínimo de 10%.
CLÁUSULA OBRIGATÓRIA:
Resta acordada a manutenção do tratamento das terapias especiais deferidas no processo a serem realizadas no prestador em que já se encontra em atendimento com possibilidade futura de redirecionamento para rede credenciada apta.

2. Home Care:
Requisitos:
➤ Quando a área técnica concorda com o PAD da liminar e indica celebração de acordo no RCA;
➤ Casos de óbito do beneficiário durante o processo, alta ou cancelamento do contrato;
➤ Após realização de perícia médica desfavorável (acordo conforme laudo pericial). Não cobrir AT (Acompanhamento Terapêutico).
➤ Não cobrir tratamento em prestador particular sem autorização do advogado interno
➤ Não cobrir por meio de reembolso integral.
➤ Não fechar acordo (sem que haja decisão transitada em julgado para tanto) para cobertura/fornecimento de cuidador, nem medicamento de uso domiciliar e nem itens de higiene pessoal.
Parâmetros do Acordo:
➤ Confirmação da liminar, limitada com as regras acima.
➤ Que o Home Care seja atualizado conforme a evolução médica do paciente.
➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Pagamento do valor da condenação com saving mínimo de 10%.

3. Medicamento:
Requisitos:
➤ Cobertura de medicamentos com negativa Fora DUT/Fora Rol
➤ Cobertura de medicamento antineoplásico;
➤ Cobertura de medicamento com tratamento já encerrado, na rede credenciada;
➤ Cobertura de medicamento na rede credenciada com contrato cancelado, registrando o fim do contrato e obrigações em minuta;
➤ Em casos de óbito do beneficiário e contrato excluído.
Parâmetros do Acordo:
➤ Confirmação da liminar, limitada com as regras acima.
➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Pagamento do valor da condenação com saving mínimo de 10%.
Não permitido acordo pré-Sentença nas seguintes hipóteses:
➤ Cobertura de medicamento de alto custo (valor superior a R$ 100.000,00), salvo se dose única (nesse caso, consultar o advogado do tema por e-mail);
➤ Cobertura de medicamento experimental;
➤ Cobertura de medicamento off label de qualquer natureza;
➤ Cobertura de medicamento Importados/não nacionalizados;
➤ Cobertura de medicamento SEM registro na ANVISA;
➤ Cobertura de medicamento para tratamento domiciliar, salvo antineoplásico/câncer;
➤ Cobertura de tratamento em prestador particular/fora da rede credenciada;
➤ Casos com decisão genérica que não especifique exatamente qual o medicamento a ser coberto, como por exemplo: todos os medicamentos que o autor vier a precisar para tratamento do seu quadro clínico.

4. Carência:
Requisitos:
➤ Se estiver comprovado no processo se tratar de Urgência e Emergência
➤ Caso não haja requisitos de fraude ou DLP
➤ Se tiver liminar, que tenha sido cumprida. Caso haja descumprimento, devemos cumprir antes de negociar.
➤ Se o caso não tiver Urgência e Emergência que seja relacionada a alguma investigação de doença grave (exemplo: Câncer), mas que não haja indícios de DLP omitida
➤ Se o procedimento for relacionado a procedimento de alto custo (acima de R$ 100.000,00) ou procedimento não coberto, deverá ser solicitada autorização do Jurídico interno antes de negociar.
Parâmetros do Acordo:
➤ Confirmação da liminar, limitada com as regras acima.
➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Pagamento do valor da condenação com saving mínimo de 10%.

5. Rol de Procedimentos e DUT:
Requisitos:
➤ A celebração de acordo somente será admitida quando o procedimento estiver integralmente em conformidade com os critérios definidos pelo STF na ADI nº 7.265, cabendo à Amil disponibilizar no RCA os subsídios técnicos demonstrem eventual não preenchimento desses requisitos; na ausência dessas informações no RCA, o escritório fica autorizado, a negociar acordo.
➤ Caso não haja requisitos de fraude
➤ Se tiver liminar, que tenha sido cumprida. Caso haja descumprimento, devemos cumprir antes de negociar.
➤ Se o procedimento for relacionado a custo muito alto (acima de R$ 100.000,00), peço que nos sinalize antes de negociar.
Parâmetros do Acordo:
➤ Confirmação da liminar, limitada com as regras acima.
➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Pagamento do valor da condenação com saving mínimo de 10%.

6. Atraso na Autorização:
Requisitos:
➤ Se o procedimento for coberto e o objeto tenha sido somente a demora na autorização.
➤ Casos haja discussão de cobertura pelo ROL e DUT usar os requisitos desse objeto
➤ Caso não haja requisitos de fraude
➤ Se tiver liminar, que tenha sido cumprida. Caso haja descumprimento, devemos cumprir antes de negociar.
➤ Se o procedimento for relacionado a custo muito alto (acima de R$ 100.000,00), peço que nos sinalize antes de negociar.
Parâmetros do Acordo:
➤ Confirmação da liminar, limitada com as regras acima.
➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Pagamento do valor da condenação com saving mínimo de 10%.

7. Pool de Cobertura (outros temas):
Requisitos:
➤ PET -SCAN e PET/CT;
➤ Nos casos de OPME relacionado ao ato cirúrgico com fornecedor credenciado;
➤ TAVI
Parâmetros do Acordo:
➤ Confirmação da liminar, limitada com as regras acima.
➤ Não haja o compromisso de o prestador virar credenciado
➤ Cobertura de tratamentos em clínica eventual somente com autorização expressa do Jurídico da Amil.
➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Pagamento do valor da condenação com saving mínimo de 10%.
Não permitido acordo pré-Sentença nas seguintes hipóteses:
➤ Não faremos acordos para cobertura de OPME se o material não estiver relacionado ao ato cirúrgico, for de alto custo, divergência de quantidade, envolver indicações de fornecedores não homologados, ou quando houver questões de fraude ou em desconformidade com a RN 424, ANS;
➤ Transplantes;
➤ Casos de CPT/ DLP em casos de Doenças Complexas – e.g., hidrocefalia, neurotransmissores, etc.
➤ Não faremos acordos para cobertura de tratamento em prestador particular;
➤ Não faremos acordo em casos envolvendo gastroplastia (bariátrica) endoscópica.
➤ Não faremos acordos para cobertura por meio de reembolso integral;
➤ hipóteses de fraude ao contrato ou intuito de burlá-lo;
➤ Fertilização in vitro
➤ Casos de internação de paciente SUS na rede privada
➤ Junta Médica nos casos em que o beneficiário não concorde em seguir com o resultado da junta.
➤ Procedimento com fins estéticos.
➤ Exame genético - Foundation One;

8. Rede de Atendimento:
Requisitos:
➤ Que tenha sido comprovada a ausência ou indisponibilidade da nossa Rede Credenciada
➤ Não seja tratamento continuado (Ex: Quimioterapia ou TEA);
➤ Que a parte comprove que tentou contato com a Amil para indicar um prestador. Nos casos em que for alegado solicitação de rede pelo Call Center, a Amil deverá disponibilizar a confirmação no RCA.
➤ Se tiver liminar, que tenha sido cumprida. Caso haja descumprimento, devemos cumprir antes de negociar.
➤ Cobertura de tratamentos em clínica eventual somente com autorização expressa do Jurídico da Amil.
➤ Caso não haja requisitos de fraude
Parâmetros do Acordo:
➤ Confirmação da liminar, limitada com as regras acima e não haja o compromisso de o prestador virar credenciado Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Pagamento do valor da condenação com saving mínimo de 10%.

9. Internação Psiquiátrica:
Requisitos:
➤ Nos casos em que o beneficiário já teve alta médica
➤ Nos casos em que o beneficiário já teve alta médica e há o aceite de cobrança em coparticipação, conforme contrato.
➤ Nos casos em que os beneficiários, com contrato ativo, aceite o tratamento e internação em rede credenciada;
➤ Cobertura de tratamentos em clínica eventual somente com autorização expressa do Jurídico da Amil.
Parâmetros do Acordo:
➤ Confirmação da liminar, limitada com as regras acima.
➤ Não haja o compromisso de o prestador virar credenciado
➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Pagamento do valor da condenação com saving mínimo de 10%.
Não permitido acordo nas seguintes hipóteses:
➤ Não faremos acordos para casos em que a clínica estiver envolvida em fraude;
➤ Não faremos acordos para casos que não tivermos o comparativo de valores praticados em nossa rede

10. OPME e Junta Médica
Requisitos:
➤ Casos de Lente Intraocular (quando já tiver cumprido).
➤ Casos envolvendo calota craniana/órtese craniana (capacetinho).
➤ Bomba de insulina (tema 1316 STJ).
➤ Prótese peniana (com liminar para fornecimento).
➤ Laudo de Perícia desfavorável para a operadora.
Parâmetros do Acordo:
➤ Confirmação da liminar, limitada com as regras acima.
➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Pagamento do valor da condenação com saving mínimo de 10%.
Não permitido acordo nas seguintes hipóteses:
➤ Prótese customizada
➤ Médicos Ofensores

Temas Não Assistenciais

11. Reajuste:
Requisitos:
➤ Casos com parecer atuarial desfavorável do time atuarial da Amil: indicação para acordo já na entrada do caso.
➤ Faixa etária: Desconto de 50% no índice do reajuste aplicado + devolução simples dos valores pagos a maior com economia de pelo menos 25% sobre os valores a devolver.
➤ Anual/sinistralidade: substituição do índice de reajuste aplicado pelo índice da ANS + devolução simples dos valores pagos a maior com economia de pelo menos 25% sobre os valores a devolver.
➤ Casos em que a perícia judicial homologada for desfavorável, mas deverá ser solicitada autorização do Jurídico Interno da Amil e consulta ao time atuarial
Acordos pós- condenação:
➤ Casos com parecer desfavorável (sempre indicados);
➤ Casos com parecer favorável (somente após esgotamento da via recursal e dispensa do RESP);
➤ Em ambas as hipóteses: cumprimento da OBF fixada na decisão (substituição/redução ou retirada do reajuste aplicado) + devolução simples dos valores pagos a maior com economia de pelo menos 10% sobre os valores a devolver.

12. Cancelamento - Aviso Prévio e Multa rescisória
Contratos PME porte 1
Requisitos:
➤ Não ter requisitos de Fraude.
➤ A empresa estar corretamente representada pelo seu Sócio.
Parâmetros do Acordo:
➤ Rescisão contratual;
➤ Declaração de inexigibilidade das mensalidades geradas após o pedido de cancelamento ou da multa contratual cobrada
➤ Pagamento de até R$ 2.000,00 de honorários de sucumbência, e devolução de valores proporcionais indicados nos subsídios.
➤ Não será proposto pagamento de indenização por danos morais, exceto se a houver negativação relacionada às mensalidades do período de aviso, desde que devidamente comprovada e havendo pedido expresso na petição inicial.

13. Demais Cancelamentos (Inadimplência, Rescisão a Pedido do Contratante etc.)
Requisitos:
➤ Sempre que houver qualquer falha administrativa no cancelamento. Por ex.: cancelamento de plano pessoa física sem o envio/confirmação de notificação prévia pelo beneficiário; notificação recebida por 3° e a pessoa mora em casa etc.
Parâmetros do Acordo:
➤ Reativação do plano mediante o pagamento da mensalidade atrasada
➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Pós sentença:
➤ Dispensa recursal pelo advogado interno;
➤ OF conforme termos do julgado e pagamento com economia mínima de 10% do valor atualizado da condenação.

14. Rescisão Unilateral de Planos Coletivos Por Adesão
Requisitos:
➤ Cancelamento a pedido da Operadora;
➤ Contrato já cancelado após a decisão judicial a pedido de beneficiário/falecimento.
Parâmetros do Acordo:
➤ Manutenção cancelamento;
➤ Sucumbência de até R$ 2.000,00.
➤ Quitação p/ ambos os réus.
➤ NENHUMA HIPÓTESE HAVERÁ ACORDO PARA FORNECER PLANO INDIVIDUAL.

15. Cancelamento de Contrato Por Baixa do CNPJ
Requisitos:
➤ Reativação do contrato
➤ Sucumbência de até R$ 2.000,00.
➤ Tenha ocorrido a regularização do CNPJ até o ajuizamento da ação ou durante a tramitação do processo.
Pós-sentença:
➤ OF conforme termos julgados e pagamento com economia mínima de 10% do valor atualizado da condenação.

16. Movimentação Cadastral (Inclusão e Exclusão de beneficiário, Remissão, Portabilidade, Implantação de Proposta)
Requisitos:
➤ Apenas quando houver qualquer falha administrativa/operacional na movimentação cadastral.
Parâmetros do Acordo:
➤ Sucumbência de até R$ 2.000,00.
➤ Concordar com a Obrigação de Fazer dentro dos limites dessa Instrução de Trabalho e com autorização Interna do Departamento Jurídico
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Pagamento do valor da condenação com saving mínimo de 10%.
Não permitido acordo nas seguintes hipóteses:
➤ Implantação de plano Pessoa Física;
➤ Downgrade e Upgrade de plano Pessoa Física;
➤ Troca de titularidade quando a pessoa que assumirá a titularidade não tem elegibilidade para figurar no contrato;
➤ Manutenção de plano empresarial ativo com apenas uma vida;
➤ Inclusão de dependente em plano pessoa física que não seja filho do titular ou novo cônjuge;
➤ Inclusão de dependente do dependente (neto, sobrinho etc., quando não houver previsão no contrato).

17. Fraude de Boleto
Requisitos:
➤ Não faremos acordo em casos pré-sentença. Somente em casos com Sentença de procedência.
Acordos pós-condenação:
➤ Confirmação da Obrigação de Fazer para reativação do contrato e baixa da mensalidade. negociação dos valores a pagar com economia de pelo menos 10%.

18. Reembolso
Requisitos:
➤ Recusa de reembolso em razão de o pagamento ser parcelado no cartão de crédito;
➤ Demonstração de insuficiência de rede de atendimento no local do atendimento;
➤ Atendimento de urgência/emergência fora da rede credenciada;
➤ Ausência de tabela contratual de reembolso (não localizado pela área).
Parâmetros do Acordo:
➤ Pagamento do reembolso nos limites do contrato direto na conta do beneficiário
➤ O Reembolso será integral quando ficar comprovado que havia ausência de rede credenciada para o procedimento.
➤ Casos de ausência de tabela: reembolso integral direto na conta do beneficiário
➤ Pagamento de até R$ 7.200,00 por dano moral + sucumbência.
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Se o Valor da diferença do Reembolso for inferior a R$ 10.000,00, mesmo que haja rede credenciada, em caso de condenação, podemos fechar.
➤ Pagamento do valor da condenação com saving mínimo de 10%.

19. Negativação do Nome (Sustação de Protesto)
Requisitos:
➤ Negativação indevida do nome do beneficiário por débito relacionado ao contrato do plano de saúde;
➤ Ausência de notificação prévia e válida;
➤ Cobrança de valores já pagos ou indevidos.
Parâmetros do Acordo:
➤ Baixa imediata da negativação;
➤ Eventual devolução de valores pagos indevidamente, de forma simples;
➤ Possibilidade de negociação do débito quando houve inadimplência legítima;
➤ Pagamento de até R$ 3.000,00 por dano moral + sucumbência;
➤ Casos de baixo valor econômico são passíveis de acordo, visando mitigação de custo processual e encerramento célere da demanda.
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Pagamento do valor da condenação com saving mínimo de 10%.

20. Documentos Obrigatórios
Requisitos:
➤ A ação deve ter como objeto exclusivo a obtenção do documento, sem cumulação relevante de dano moral;
➤ Comprovação de solicitação administrativa prévia, não atendida ou negada pela operadora;
➤ Documentos relacionados ao contrato ou a relação assistencial do beneficiário com a operadora, não sendo admitidos pedidos de documentos inexistentes, não produzidos pela operadora ou que a guarda não seja obrigatória ou já tenha expirado nos termos legais/regulatórios;
➤ Legitimidade para requerer o documento.
Parâmetros do Acordo:
➤ Disponibilização do documento solicitado;
➤ Prioritariamente sem natureza indenizatória. Em caso de impossibilidade de apresentar o documento, avaliar o risco de condenação e viabilidade de composição financeira.
➤ Pagamento de até R$ 2.000,00 por dano moral + sucumbência;
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Cumprimento a obrigação de fazer.
➤ Pagamento do valor da condenação com saving mínimo de 10%.

21. Mensalidade
Requisitos:
➤ Indício de falha na cobrança ou na comunicação ao beneficiário;
➤ Cobrança relacionada ao período da vigência do contrato;
Parâmetros do Acordo:
➤ Regularização da cobrança, com emissão dos boletos corretos/ ou reprocessamento dos valores;
➤ Possibilidade de negociação do débito, quando houve inadimplência legítima;
➤ Pagamento de até R$ 2.000,00 por dano moral + sucumbência;
Acordos Pós Sentença (Quando não vamos recorrer):
➤ Mesmas regras acima.
➤ Cumprimento a obrigação de fazer.
➤ Pagamento do valor da condenação com saving mínimo de 10%.
"""

compiled = DynamicPolicyCompiler.compile_corporate_manual(
    pdf_text=full_16_pages_text,
    policy_name="Instrução de Trabalho — Acordos (Contencioso de Massa)",
    version="2026.1-AMIL-OFICIAL"
)

print(f"Compiled {compiled.total_topics} topics and {len(compiled.all_rules)} rules!")
for t in compiled.topics:
    print(f"Topic {t.topic_number:02d} ({t.category}): {t.topic_name} | Reqs: {len(t.requirements)} | Params: {len(t.agreement_parameters)} | Proh: {len(t.prohibitions)}")

db = SessionLocal()
from src.models.entities import Policy

tenants = db.query(Tenant).all()
for tenant in tenants:
    policy = db.query(Policy).filter(Policy.tenant_id == tenant.id).first()
    if not policy:
        policy = Policy(
            tenant_id=tenant.id,
            name="Instrução de Trabalho — Acordos (Contencioso de Massa)",
            description="Manual Oficial Amil 2026 com 21 temas operacionais"
        )
        db.add(policy)
        db.flush()

    db.query(PolicyVersion).filter(PolicyVersion.tenant_id == tenant.id).update({"status": "INACTIVE"})
    
    pv = PolicyVersion(
        tenant_id=tenant.id,
        policy_id=policy.id,
        version="2026.1-AMIL-OFICIAL",
        status="ACTIVE",
        file_hash_sha256="sha256_full_16_pages_amil_2026",
        pdf_storage_path="policies/Instrucao_Trabalho_Acordos_Amil_2026.pdf",
        structured_rules={
            "policy_version_id": "2026.1-AMIL-OFICIAL",
            "topics": [t.model_dump() for t in compiled.topics],
            "general_rules": compiled.general_rules,
            "rules": compiled.all_rules
        }
    )
    db.add(pv)

db.commit()
print("All tenants updated successfully with ACTIVE 2026.1-AMIL-OFICIAL policy!")
db.close()
