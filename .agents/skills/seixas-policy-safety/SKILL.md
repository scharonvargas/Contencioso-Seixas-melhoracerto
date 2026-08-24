---
name: seixas-policy-safety
description: "Garantia de segurança de políticas: compilação dinâmica de normas PDF, zero regras hardcoded em código e respeito estrito ao estado ACTIVE."
---

# Seixas Policy Safety

Esta skill é o guardião inegociável da regra suprema do Seixas AI: **ZERO HARDCODED RULES**.

---

## 🔒 Princípios de Domínio

1. **Fonte Única na Norma Ativa**:
   - Todas as regras de elegibilidade, tetos monetários, alçadas, percentuais de saving e condicionantes devem vir **exclusivamente** da `PolicyVersion` marcada como `ACTIVE` no banco de dados para o tenant.
2. **Proibição Absoluta de Hardcode**:
   - É terminantemente proibido codificar regras específicas de operadoras ou instruções de trabalho (ex: "se tema == medicamento então teto é 10000") em código Python (`src/`).
3. **Imutabilidade e Hash**:
   - Toda compilação de norma gera um hash SHA-256 do arquivo original e de sua árvore JSON-Logic correspondente para auditoria forense.
4. **Sem Conhecimento Jurídico Externo**:
   - O sistema e o LLM não devem aplicar leis genéricas, súmulas ou jurisprudência externa para alterar regras da norma ativa.

---

## 🛠️ Procedimento de Verificação

Ao alterar `src/rule_engine/`, `src/compiler/` ou `src/api/routes/policies.py`:
1. Verificar se nenhuma constante de negócio foi introduzida no código.
2. Garantir que a árvore JSON-Logic é gerada pelo compilador de normas e interpretada de forma agnóstica.
3. Testar a transição atômica de versões de norma (`DRAFT` → `ACTIVE` → `ARCHIVED`).
