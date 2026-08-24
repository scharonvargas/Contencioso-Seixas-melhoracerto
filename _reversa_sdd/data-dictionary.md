# 📖 REVERSA — Dicionário de Dados: Módulo de Análise de Processos

Este documento detalha os modelos, DTOs, schemas de extração e estruturas de fatos processuais manipulados pelo Seixas AI.

---

## 1. Entidades de Persistência (SQLAlchemy ORM)

### 1.1 `Process` (`processes`)
Representa a pasta do processo judicial importado.

| Campo | Tipo | Nullable | Padrão | Descrição |
|---|---|---|---|---|
| `id` | `String(36)` | NÃO | `UUIDv4` | Identificador único primário do processo |
| `tenant_id` | `String(36)` | NÃO | - | FK da empresa/operadora titular |
| `cnj_number` | `String(32)` | NÃO | - | Número unificado do CNJ (ex: `0700071-15.2024.8.02.0025`) |
| `court_name` | `String(128)` | SIM | `None` | Vara e Comarca / Tribunal de Justiça |
| `beneficiary_name`| `String(255)` | NÃO | - | Nome da parte autora / beneficiário |
| `beneficiary_cpf` | `String(11)` | SIM | `None` | CPF da parte autora |
| `operator_name` | `String(255)` | NÃO | - | Nome da operadora ré |
| `status` | `String(32)` | NÃO | `"PENDING"` | `PENDING`, `PROCESSING`, `EVALUATED`, `REQUIRES_HUMAN_REVIEW`, `ERROR` |
| `total_pages` | `Integer` | NÃO | `0` | Quantidade total de páginas somadas dos PDFs |
| `created_at` | `DateTime` | NÃO | `now()` | Data/hora de ingestão dos autos |

### 1.2 `Evaluation` (`evaluations`)
Armazena a decisão técnica emitida pelo motor determinístico.

| Campo | Tipo | Nullable | Padrão | Descrição |
|---|---|---|---|---|
| `id` | `String(36)` | NÃO | `UUIDv4` | ID único da avaliação |
| `tenant_id` | `String(36)` | NÃO | - | FK do Tenant |
| `process_id` | `String(36)` | NÃO | - | FK do Processo |
| `policy_version_id`| `String(36)` | NÃO | - | FK da Norma Ativa utilizada |
| `overall_result` | `String(32)` | NÃO | - | `ELIGIBLE`, `CONDITIONALLY_ELIGIBLE`, `REQUIRES_HUMAN_REVIEW`, `INELIGIBLE` |
| `total_rules_evaluated` | `Integer` | NÃO | `0` | Quantidade de regras da norma executadas |
| `rules_passed` | `Integer` | NÃO | `0` | Quantidade de regras com status `PASS` |
| `rules_failed` | `Integer` | NÃO | `0` | Quantidade de regras com status `FAIL` |
| `rules_unknown` | `Integer` | NÃO | `0` | Quantidade de regras com status `UNKNOWN` |
| `decision_summary` | `Text` | NÃO | - | Resumo executivo em linguagem natural |
| `rules_results` | `JSON` | SIM | `[]` | Lista detalhada de cada regra e seu status |
| `execution_trace` | `JSON` | SIM | `{}` | Log forense completo das 6 fases |

### 1.3 `DocumentPage` (`document_pages`)
Páginas individuais pós-OCR com metadados espaciais.

| Campo | Tipo | Nullable | Descrição |
|---|---|---|---|
| `id` | `String(36)` | NÃO | ID único da página |
| `process_id` | `String(36)` | NÃO | FK do processo |
| `page_number` | `Integer` | NÃO | Número sequencial global no dossiê |
| `document_name` | `String(255)` | SIM | Nome do arquivo PDF de origem |
| `page_in_document` | `Integer` | SIM | Número da página no PDF original |
| `segment_type` | `String(64)` | SIM | Categoria da peça (`PETICAO_INICIAL`, `LAUDO_MEDICO`, etc.) |
| `raw_text` | `Text` | SIM | Camada de texto integral extraída |
| `words_data` | `JSON` | SIM | Lista de palavras e suas coordenadas espaciais `bbox` |
| `quality_score` | `Float` | NÃO | Score de nitidez e confiança do OCR (0.0 a 1.0) |

---

## 2. Estrutura de Fatos do Processo (`case_facts`)

```json
{
  "identified_theme": "Tema 17: Fraude de Boleto",
  "applicable_topic_num": 17,
  "procedural_stage": "PRE_SENTENCA",
  "financial": {
    "requested_amount": 16788.18,
    "paid_amount_by_beneficiary": 16788.18,
    "material_damage_amount": 6788.18,
    "moral_damage_amount": 10000.00,
    "sucumbence_amount": 0.00,
    "has_fiscal_receipt": true,
    "receipts_found": [],
    "evidence": {
      "document_type": "NOTA_FISCAL",
      "page_number": 31,
      "bounding_box": [100.0, 100.0, 200.0, 900.0],
      "text_snippet": "Boleto Safra R$ 6.788,18",
      "ocr_engine": "PyMuPDF",
      "confidence_score": 1.0
    }
  },
  "treatment": {
    "treatment_type": "ASSISTENCIAL",
    "cid_10": null,
    "has_medical_report": false,
    "has_school_aide_request": false,
    "evidence": {
      "document_type": "LAUDO_MEDICO",
      "page_number": 1
    }
  },
  "administrative_denial": {
    "has_administrative_denial": false,
    "evidence": {
      "document_type": "NEGATIVA_OPERADORA",
      "page_number": 1
    }
  },
  "topics": {
    "topic_17": {
      "requirements_met": false,
      "has_prohibition": true,
      "evidence": {
        "document_type": "PETICAO_INICIAL",
        "page_number": 1
      }
    }
  },
  "dossier_pages_count": 35
}
```
