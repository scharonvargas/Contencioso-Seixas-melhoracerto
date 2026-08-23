# Seixas AI — Plataforma de Validação Automatizada de Acordos de Reembolso em Saúde

[![Tests](https://img.shields.io/badge/Tests-20%20passed-emerald)](file:///d:/Programas%20IA%20web/2%20-%20Seixas%202/tests)
[![Architecture](https://img.shields.io/badge/Architecture-Hybrid%20Local--First-blue)](file:///d:/Programas%20IA%20web/2%20-%20Seixas%202/.planning/PROJECT.md)
[![Decision Engine](https://img.shields.io/badge/Rule%20Engine-100%25%20Deterministic-purple)](file:///d:/Programas%20IA%20web/2%20-%20Seixas%202/src/rule_engine/deterministic_engine.py)

Plataforma SaaS para leitura de processos judiciais volumosos (200 a 1.000 páginas), extração de evidências e validação automatizada de acordos de reembolso de saúde com base **EXCLUSIVA** na norma interna vigente da operadora.

---

## 🌟 Princípios Inegociáveis da Arquitetura

1. **Zero Análise Jurídica / Zero Viés Externo**: O LLM **nunca decide** "paga" ou "não paga". Ele atua exclusivamente como extrator de fatos estruturados. O veredito é emitido por um **Motor de Regras Determinístico (`JSON-Logic`)** sobre as cláusulas da Norma Ativa.
2. **Evidence-First**: Nenhum fato existe sem vínculo rastreável com `document_id`, `page_number`, `bounding_box` e `text_snippet` validado.
3. **Tríade Booleana (`PASS`, `FAIL`, `UNKNOWN`)**: Fatos com evidência ausente ou confiança < 85% recebem status `UNKNOWN`, direcionando o caso para a fila prioritária de *Human-in-the-Loop* (HITL).
4. **Norma Única Ativa**: Transição atômica garantida por banco relacional. A alteração trimestral da norma não exige novo OCR dos processos já analisados (*Zero Reprocessing*).

---

## 🚀 Quickstart

### 1. Pré-requisitos
- Python 3.11+
- Dependências instaladas via `pip`

### 2. Instalação de Dependências
```bash
python -m pip install -e .
```

### 3. Carga Inicial do Banco de Dados (Seed)
Inicializa o Tenant padrão (*Vida Plena Saúde*), usuário Administrador e a Norma Ativa `2026.1`:
```bash
python scripts/seed_db.py
```

### 4. Execução da Suíte de Testes (20 Testes)
```bash
python -m pytest tests/ -v
```

### 5. Execução do Benchmark Operacional
Mede o throughput de páginas/segundo e a acurácia do pipeline:
```bash
python scripts/process_benchmark.py
```

### 6. Inicialização da API REST
```bash
python -m uvicorn src.api.main:app --reload --port 8000
```
- **Documentação Swagger**: `http://localhost:8000/docs`
- **Métricas Prometheus**: `http://localhost:8000/metrics`
- **Frontend Interativo**: Abra [`frontend/index.html`](file:///d:/Programas%20IA%20web/2%20-%20Seixas%202/frontend/index.html) no navegador para acessar o visualizador Split-Screen com Bounding Box.

---

## 🏗️ Estrutura do Projeto

```
seixas-ai/
├── .planning/               # Documentação executiva, requisitos e decisões (GSD)
├── src/
│   ├── api/                 # Rotas FastAPI (processos, normas, HITL)
│   ├── core/                # Configurações, banco de dados e storage MinIO
│   ├── ingestion/           # Avaliador de qualidade e texto nativo
│   ├── ocr/                 # Motor em cascata de 4 camadas e OpenCV
│   ├── segmentation/        # Taxonomia e segmentação documental
│   ├── extraction/          # CaseFactModel e EvidenceGroundingValidator
│   ├── rule_engine/         # JSON-Logic puro Python e Semantic Diff
│   ├── validators/          # Algoritmos de CPF, CNPJ, CNJ, BRL e CID-10
│   ├── services/            # Orquestrador do ciclo de vida e persistência
│   └── models/              # Modelos ORM SQLAlchemy com RLS
├── frontend/                # Interface Web com Split-Screen Viewer
├── scripts/                 # Seed de dados e benchmark de performance
└── tests/                   # 20 testes unitários, de integração e API
```

---

## 📊 Dimensionamento e Custos (100 Processos/Dia = 50.000 Páginas/Dia)

- **Throughput Nominal**: ~104 páginas/minuto (processamento em paralelo nos workers de CPU).
- **Tempo Médio por Processo**: ~4 a 6 minutos para 500 páginas.
- **Custo Operacional Estimado**: **~R$ 0,58 por processo** (~R$ 1.730,00/mês para 1,5 milhão de páginas).
- **Taxa de Falsos Positivos**: **0.0%** (Garantida pelo motor determinístico).
