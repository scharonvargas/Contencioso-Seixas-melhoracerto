---
name: verification-before-completion
description: "Protocolo de verificação de evidências antes da conclusão de tarefas: proíbe declarações de sucesso sem comprovação em logs e testes executados."
---

# Verification Before Completion

Esta skill proíbe categoricamente o agente de declarar uma tarefa como concluída sem fornecer evidência objetiva e verificada.

---

## 🚫 Comportamentos Proibidos

- Declarar "Todos os testes passaram" sem ter executado o comando no terminal.
- Afirmar que uma rota ou função funciona sem demonstrar o log de execução ou resposta HTTP.
- Assumir que código recém-escrito compila e executa sem executá-lo.

---

## 🛡️ Checklist Obrigatório de Conclusão

Antes de concluir qualquer tarefa ou responder ao usuário que o trabalho terminou:

1. **Executar a Suíte de Testes Relevante**:
   ```bash
   uv run pytest tests/ -v
   ```
2. **Coletar a Evidência**:
   - Verificar se houve falhas (`failed`), erros (`errors`) ou warnings críticos.
   - Registrar o total de testes executados com sucesso.
3. **Validar Tipo e Sintaxe**:
   - Garantir que não há erros de importação ou referências não resolvidas.
4. **Apresentar a Evidência**:
   - Informar ao usuário exatamente quais testes rodaram e o resultado observado.
