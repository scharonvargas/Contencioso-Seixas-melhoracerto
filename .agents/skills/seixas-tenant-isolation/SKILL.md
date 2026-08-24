---
name: seixas-tenant-isolation
description: "Auditoria e garantia de isolamento multi-tenant: validação de escopo em rotas, queries de banco de dados, storage de arquivos e cache de políticas."
---

# Seixas Tenant Isolation

Esta skill orienta e audita todas as operações para garantir que dados de um tenant jamais sejam acessados, alterados ou inferidos por outro tenant.

---

## 🔒 Checklist de Auditoria Multi-Tenant

### 1. Rotas da API (`src/api/routes/`)
- [ ] O `tenant_id` é extraído do token JWT autenticado e nunca de query params livres?
- [ ] O endpoint verifica se os IDs passados (ex: `process_id`, `policy_id`, `document_id`) pertencem ao `tenant_id` autenticado?

### 2. Acesso a Dados (`src/models/` / Repositórios)
- [ ] Todas as cláusulas `WHERE` incluem `tenant_id == current_tenant_id`?
- [ ] Não há `JOIN` sem restrição de tenant na tabela relacionada?

### 3. Sistema de Arquivos e Storage
- [ ] Os caminhos de disco utilizam prefixos com `tenant_id`?
- [ ] O gerador de download valida permissão do arquivo antes de emitir stream?

### 4. Cache e Políticas
- [ ] O cache em memória de normas ativas utiliza chave composta com `tenant_id`?
- [ ] Invalidação de cache em um tenant não afeta outros tenants.
