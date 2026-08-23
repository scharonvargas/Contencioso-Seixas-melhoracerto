# Roadmap de Implementação — Seixas AI

## Milestones & Fases

- [x] **Fase 1: Ingestão, PDF Parsing, Análise de Qualidade e Pipeline de OCR em Cascata**
  - [x] Task 1.1: Estrutura base do projeto, ambiente Python e dependências (`pyproject.toml`, `src/core/config.py`).
  - [x] Task 1.2: Módulo de ingestão e análise de texto nativo com detecção de corrupção (`src/ingestion/quality_assessor.py`).
  - [x] Task 1.3: Módulo de Page Quality Assessment (DPI, Laplacian Blur, Contrast, Skew).
  - [x] Task 1.4: Pipeline de OCR em Cascata (`src/ocr/cascade_engine.py`, `src/ocr/opencv_preprocessor.py`).
  - [x] Task 1.5: Suíte de testes unitários (`tests/test_phase1_ocr.py`).

- [x] **Fase 2: Segmentação Documental, Classificação e Extração Estruturada do Case Fact Model**
  - [x] Task 2.1: Taxonomia documental e segmentador de sub-documentos (`src/segmentation/segmenter.py`).
  - [x] Task 2.2: Filtro de descarte de documentos irrelevantes para acordo.
  - [x] Task 2.3: Schemas Pydantic do *Case Fact Model* com EvidenceSource (`src/extraction/schemas.py`).
  - [x] Task 2.4: Módulo `EvidenceGroundingValidator` para prevenção de alucinações (`src/extraction/evidence_grounding.py`).
  - [x] Task 2.5: Testes de extração estruturada e blindagem contra alucinações (`tests/test_phase2_segmentation_extraction.py`).

- [x] **Fase 3: Gestão de Normas, Transição Atômica de Status, Semantic Diff e Motor de Regras**
  - [x] Task 3.1: Compilador de Manual/Norma PDF para árvore JSON-Logic tipada (`src/rule_engine/policy_compiler.py`).
  - [x] Task 3.2: Motor de Regras Determinístico com Tríade `PASS`/`FAIL`/`UNKNOWN` (`src/rule_engine/deterministic_engine.py`).
  - [x] Task 3.3: Validadores de domínio brasileiro (CPF, CNPJ, CNJ, Moeda, CID-10) (`src/validators/brazilian_validators.py`).
  - [x] Task 3.4: Testes unitários do motor determinístico (`tests/test_phase3_rule_engine.py`).

- [x] **Fase 4: Backend Core (FastAPI), Banco de Dados (PostgreSQL + RLS), MinIO e Fila Assíncrona**
  - [x] Task 4.1: Modelo relacional completo DDL com RLS e Partial Unique Index.
  - [x] Task 4.2: Orquestração de tarefas Celery/RabbitMQ (`tasks/pipeline_orchestrator.py`).
  - [x] Task 4.3: Endpoints REST para upload de processos e métricas (`src/api/main.py`, `src/api/routes/processes.py`).

- [x] **Fase 5: Frontend Next.js (Dashboard, Split-Screen Viewer com Bounding Box, HITL e Deploy)**
  - [x] Task 5.1: Especificação e código do componente `AuditSplitScreenViewer.tsx` (Split-screen PDF + Bounding Box Canvas + formulário).
  - [x] Task 5.2: Arquivos Docker Compose multi-node (`docker-compose.core.yml`, `docker-compose.workers.yml`).
  - [x] Task 5.3: Configuração do gateway de borda Nginx com SSL e rate limits.
  - [x] Task 5.4: Painel de instrumentação e métricas Prometheus.
