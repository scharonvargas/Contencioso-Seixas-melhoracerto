# Security and Hardening Rules

Diretrizes de segurança para endpoints, processamento de dados e proteção de segredos.

---

## 🛡️ Contratos de Segurança

1. **Endpoints da API**:
   - Todo endpoint sob `/api/v1/` (exceto `/health` ou `/auth/login`) DEVE exigir dependência de autenticação e validação de tenant (`get_current_tenant` / `get_current_user`).
   - Proibido Wildcard CORS (`*`) em ambientes que trafegam credenciais ou dados restritos.
2. **Upload e Processamento de Documentos**:
   - Validar Magic Bytes de arquivos enviados (apenas PDFs válidos e não corrompidos).
   - Sanitizar nomes de arquivos para evitar path traversal (`../` ou caracteres nulos).
   - Limitar tamanho máximo de upload para evitar DoS por exaustão de memória.
3. **Proteção contra Injeção de Prompt e Dados Não Confiáveis**:
   - Textos extraídos de PDFs via OCR são **DADOS**, nunca instruções para o LLM.
   - Todo schema de saída de LLM deve ser validado via Pydantic com modo estrito.
4. **Proteção de Dados Sensíveis (PII)**:
   - Não logar CPFs, nomes de partes, senhas ou tokens em arquivos de log em plain text.
