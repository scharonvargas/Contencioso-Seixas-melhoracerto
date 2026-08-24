# Tenant Isolation Rules

Regras estritas para garantir isolamento multi-tenant absoluto em todas as camadas da aplicação.

---

## 🏢 Diretrizes de Isolamento Multi-Tenant

1. **Camada de Banco de Dados / ORM**:
   - Toda query de leitura (`SELECT`), inserção (`INSERT`), atualização (`UPDATE`) ou deleção (`DELETE`) em tabelas de negócio (processos, regras, execuções, traces) DEVE conter filtro explícito por `tenant_id`.
   - Proibido usar fallbacks globais (ex: `WHERE tenant_id == current_tenant OR tenant_id IS NULL`), salvo em tabelas de sistema estritamente públicas.
2. **Armazenamento de Arquivos (Storage)**:
   - Caminhos de armazenamento de PDFs e imagens de OCR devem ser particionados por tenant: `storage_data/{tenant_id}/{process_id}/...`.
   - Nenhum endpoint pode servir um arquivo sem antes verificar se o arquivo pertence ao `tenant_id` autenticado na requisição.
3. **Execução de Políticas**:
   - O carregamento da `PolicyVersion ACTIVE` deve ser estritamente filtrado por `tenant_id`. Nunca compartilhar cache de regras entre tenants distintos.
