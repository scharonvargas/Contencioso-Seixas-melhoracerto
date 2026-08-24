---
name: security-and-hardening
description: "Auditoria contínua de segurança: autenticação, autorização de tenant, uploads, injeção de prompt e proteção de dados sensíveis."
---

# Security and Hardening

Esta skill estabelece os procedimentos de segurança para código, dependências e dados no Seixas AI.

---

## 🔍 Eixos de Auditoria de Segurança

### 1. Autenticação e Autorização (FastAPI)
- Toda rota protegida deve conter `Depends(get_current_user)` ou `Depends(get_current_tenant)`.
- Validar se o usuário logado possui permissão para acessar o recurso solicitado.

### 2. Sanitização de Upload de Arquivos
- Validar extensão (`.pdf`) e header binário (Magic Bytes `%PDF-`).
- Impedir nomes de arquivo com paths relativos (`../`) ou caracteres de escape.
- Salvar arquivos com UUIDs determinísticos em vez de nomes controlados pelo usuário.

### 3. Proteção contra Injeção em LLMs
- Dados extraídos via OCR devem ser encapsulados em blocos de dados isolados nos prompts.
- Proibir que instruções encontradas no texto dos processos alterem as diretrizes do sistema.

### 4. Gestão de Segredos e PII
- Nunca expor chaves de API (`OPENAI_API_KEY`, `ANTHROPIC_API_KEY`, etc.) em código ou respostas.
- Não registrar CPF, dados bancários ou informações médicas completas em logs desprotegidos.
