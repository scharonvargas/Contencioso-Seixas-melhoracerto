---
name: test-driven-development
description: "Desenvolvimento Guiado por Testes: implementação estrita do ciclo Red-Green-Refactor e criação de testes de regressão antes de qualquer bugfix."
---

# Test-Driven Development (TDD)

Esta skill guia a implementação de novas funcionalidades e correção de bugs através de testes determinísticos.

---

## 🎯 Princípios Inegociáveis

1. **Bugfix Requer Teste Prévio**: Nenhum bug é considerado corrigido se não houver um teste automatizado que reproduzia a falha antes da correção.
2. **Ciclo Red-Green-Refactor**:
   - **RED**: Escrever o teste para o comportamento desejado. Executar e confirmar que falha pelo motivo correto.
   - **GREEN**: Escrever o código mínimo necessário para fazer o teste passar.
   - **REFACTOR**: Limpar o código, eliminar duplicações e melhorar legibilidade sem alterar o comportamento ou quebrar os testes.
3. **Determinismo**: Testes não devem depender de chamadas externas de rede não mockadas, horários reais do sistema ou ordem randômica de execução.

---

## 📋 Cenários Críticos no Seixas AI

Todo novo teste para o pipeline do Seixas deve cobrir explicitamente:
- Extração com evidência ausente ou parcial (`UNKNOWN`).
- Documento ilegível / OCR de baixa confiança.
- Conflito entre petição e documentos comprobatórios (`CONFLICTING`).
- Avaliação de regras com tipos divergentes (moeda formatada vs float).
- Isolamento de `tenant_id` nas rotas da API.
