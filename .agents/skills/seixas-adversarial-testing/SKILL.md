---
name: seixas-adversarial-testing
description: "Testes adversariais de processos jurídicos: geração de casos extremos, pegadinhas documentais, citações falsas e inconsistências para blindagem do motor."
---

# Seixas Adversarial Testing

Esta skill atua como uma equipe de Red Team, projetando cenários adversariais e testes de estresse para tentar induzir o sistema a erros de avaliação.

---

## 🎯 Cenários Adversariais Mandatórios

1. **Citação de Processo Externo**:
   - A petição cita um acórdão ou laudo de outro número de processo como exemplo.
   - **Comportamento Esperado**: O sistema não deve atribuir os fatos do processo citado ao processo atual.
2. **Divergência de Valores**:
   - Petição inicial indica valor da causa de R$ 50.000,00, mas o pedido de condenação líquida é de R$ 8.000,00.
   - **Comportamento Esperado**: Distinguir claramente `valor_da_causa`, `valor_do_pedido` e `valor_procedimento`.
3. **Evidência Tardia / Oculta**:
   - PDF com 400 páginas onde a nota fiscal relevante está na página 389.
   - **Comportamento Esperado**: Não abortar extração prematuramente; manter rastreabilidade exata da página.
4. **Documento Corrompido / Ilegível**:
   - Páginas com manchas pretas ou resolução de 50 DPI.
   - **Comportamento Esperado**: Não inventar score de confiança 0.90; classificar como `UNKNOWN` e alertar o revisor humano.
5. **Ataque Cross-Tenant**:
   - Tenant A tenta avaliar um processo passando o `id` de um documento do Tenant B.
   - **Comportamento Esperado**: HTTP 403 / 404 imediato sem vazamento de metadados.
