---
name: seixas-evidence-grounding
description: "Rastreabilidade espacial de evidências documentais: bounding boxes, snippets, integridade de fatos e tríade booleana PASS/FAIL/UNKNOWN."
---

# Seixas Evidence Grounding

Esta skill garante que nenhum fato processual exista no sistema sem ancoragem documental rastreável e auditável.

---

## 📐 Estrutura Obrigatória de Evidência

Todo fato extraído de um processo deve conter obrigatoriamente:
- `document_id`: Identificador do arquivo no processo.
- `page_number`: Número exato da página (1-indexed).
- `bounding_box`: Coordenadas espaciais normalizadas `[x0, y0, x1, y1]`.
- `text_snippet`: Trecho de texto literal extraído da página.
- `confidence`: Nível de confiança da extração/OCR (0.0 a 1.0).

---

## ⚖️ Tríade Booleana e HITL

```text
       ┌─────────────── Evidência Encontrada? ───────────────┐
       │                                                      │
      SIM                                                    NÃO
       │                                                      │
Atende ao Critério?                                    Estado: UNKNOWN
  ├── SIM  → PASS                                             │
  └── NÃO  → FAIL                                      Roteamento: HITL
                                                  (Human-in-the-Loop)
```

- **Fato sem evidência documental NÃO é `FALSE` nem `PASS`**: É rigorosamente `UNKNOWN`.
- **Inconsistência entre petição e laudo/comprovante**: Retornar `CONFLICTING` e encaminhar para HITL.
- **Proibição de Suposição**: O modelo jamais deve "deduzir" que um requisito foi cumprido se o documento comprobatório estiver ausente.
