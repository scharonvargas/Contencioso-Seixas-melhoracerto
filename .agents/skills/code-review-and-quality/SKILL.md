---
name: code-review-and-quality
description: "Revisão e qualidade de código: avaliação de arquitetura limpa, legibilidade, tratamento de erros, performance e integridade de tipos."
---

# Code Review and Quality

Esta skill define os critérios para revisão técnica de alterações e novas implementações.

---

## 🧐 Eixos de Avaliação

### 1. Correção e Robustez
- O código trata todos os cenários de erro esperados (arquivos não encontrados, JSON inválido, valores nulos)?
- Não há variáveis não tipadas ou supressões de tipo injustificadas.

### 2. Arquitetura e Separação de Responsabilidades
- O código em `src/rule_engine/` permanece agnóstico em relação a regras específicas de clientes?
- As rotas da API em `src/api/` são apenas controladoras finas que delegam a lógica para `src/services/`?

### 3. Performance e Recursos
- Não há carregamento excessivo de arquivos grandes em memória sem streaming.
- Conexões de banco de dados e arquivos abertos são fechados adequadamente (context managers).

### 4. Manutenibilidade e Legibilidade
- Nomes de funções e variáveis refletem o domínio jurídico/técnico com precisão.
- Código complexo contém docstrings e justificativas claras.
