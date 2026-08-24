---
name: systematic-debugging
description: "Protocolo sistemático de depuração: reprodução de falhas, localização da causa raiz e validação antes da correção de código."
---

# Systematic Debugging

Esta skill define o protocolo mandatório para resolução de bugs e regressões.

---

## 🚫 Proibições Estritas (Shotgun Debugging)

- **NUNCA** faça alterações especulativas em múltiplos arquivos esperando que o erro desapareça.
- **NUNCA** encubra sintomas com blocos `try/catch` vazios, valores default arbitrários ou supressão de exceções.
- **NUNCA** altere código de produção sem antes isolar e reproduzir o defeito.

---

## 🔄 Protocolo de 6 Etapas

```text
1. REPRODUZIR     → Criar script mínimo ou teste unitário isolado que falha de forma determinística.
2. ISOLAR         → Localizar a linha exata e a condição de estado onde o comportamento desvia do esperado.
3. CAUSA RAIZ     → Identificar a causa fundamental (ex: tipo incorreto, race condition, parser falhando).
4. HIPÓTESE       → Formular uma explicação comprovável para a falha.
5. CORREÇÃO MÍNIMA→ Aplicar a menor alteração arquiteturalmente coerente que soluciona a causa raiz.
6. VERIFICAÇÃO    → Demonstrar que o teste de reprodução passou e nenhuma suíte adjacente regrediu.
```

---

## 🧪 Prática no Workspace

1. Criar reprodução isolada em `tests/` ou `scratch/`.
2. Executar via terminal:
   ```bash
   uv run pytest tests/path_to_test.py -k test_name -v
   ```
3. Confirmar a falha inicial (RED).
4. Implementar a correção na causa raiz.
5. Confirmar o sucesso (GREEN).
