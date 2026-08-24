# 00-seixas-core — Regras Inegociáveis de Domínio (Always On)

Este documento estabelece as diretrizes invioláveis que regem qualquer alteração no Seixas AI.

---

## 🔒 Princípios Fundamentais

1. **Zero Hardcoded Rules**: Nenhuma regra de negócio, teto financeiro, alçada, vedação ou saving pode ser escrita diretamente em código Python (`src/`). Todas as regras derivam exclusivamente da `PolicyVersion` no estado `ACTIVE` compilada a partir de PDF.
2. **Motor Determinístico**: O código é um interpretador agnóstico de árvores JSON-Logic e validadores matemáticos. O LLM não decide elegibilidade de negócio se o motor puder executá-la.
3. **Evidence-First**: Todo fato jurídico/documental requer provenance espacial completa (`document_id`, `page_number`, `bounding_box`, `text_snippet`).
4. **Tríade Booleana Estrita**:
   - `PASS`: Fato comprovado documentalmente com evidência válida.
   - `FAIL`: Fato comprovado documentalmente que viola o critério da norma ativa.
   - `UNKNOWN`: Ausência de documento, ilegibilidade ou ambiguidade.
   - **PROIBIDO**: Tratar `UNKNOWN` como `FALSE` ou inferir `PASS` por suposição. Todo `UNKNOWN` é roteado para Human-in-the-Loop (HITL).
5. **Isolamento de Tenant**: Nenhuma query, leitura de arquivo em storage ou execução de regra pode ocorrer sem `tenant_id` autenticado.
