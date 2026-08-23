# Requisitos do Sistema — Seixas AI

## Requisitos Funcionais (RF)

### 1. Ingestão e Pré-Processamento (INGEST)
- **RF-ING-01**: O sistema deve receber arquivos PDF de processos judiciais de 200 a 1.000 páginas via upload direto e API REST.
- **RF-ING-02**: O sistema deve detectar automaticamente se a página possui camada de texto nativo válida e não corrompida (>150 caracteres legíveis, <3% de lixo/fontes nulas).
- **RF-ING-03**: O sistema deve calcular o Page Quality Score (DPI, Blur via variância laplaciana, Contraste, Skew) para cada página escaneada.
- **RF-ING-04**: O sistema deve aplicar pré-processamento OpenCV (Deskew, CLAHE, Binarização Sauvola) apenas em páginas degradadas.

### 2. OCR em Cascata (OCR)
- **RF-OCR-01**: Utilizar PyMuPDF para extração nativa direta instantânea (<10ms/pág).
- **RF-OCR-02**: Utilizar Docling / PaddleOCR ONNX como motor de OCR local primário para páginas escaneadas.
- **RF-OCR-03**: Acionar fallback em API de VLM (Gemini 2.0 Flash / GPT-4o-mini) para páginas com confiança média de OCR < 85% ou tabelas médicas complexas.
- **RF-OCR-04**: Gerar coordenadas de Bounding Box normalizadas [0-1000] para todas as palavras reconhecidas.

### 3. Segmentação e Extração Estruturada (SEG/FACT)
- **RF-SEG-01**: Identificar quebras de sub-documentos dentro de um único PDF concatenado (Petição Inicial, Laudos, NFs, Recibos, Negativas, Sentenças).
- **RF-SEG-02**: Descartar da esteira de extração pesada documentos meramente procedimentais (procurações, certidões de juntada).
- **RF-FACT-01**: Extrair o *Case Fact Model* tipado em Pydantic contendo dados do beneficiário, operadora, CID-10, tratamento, valores pleiteados, valores desembolsados e protocolo de negativa.
- **RF-FACT-02**: Validar cada fato com *Evidence Grounding* obrigatório contra a camada de OCR da página. Fatos sem substring correspondente devem ser rejeitados para evitar alucinações.

### 4. Gestão de Normas e Motor de Decisão (POLICY/RULE)
- **RF-POL-01**: Permitir upload de qualquer Manual/Instrução de Trabalho de Acordos em PDF e compilar seus temas, requisitos, vedações e tetos para árvore JSON-Logic 100% dinâmica (sem nenhuma regra hardcoded em código).
- **RF-POL-02**: Exigir aprovação humana formal antes da ativação da versão da norma e exibir semantic diff entre a versão anterior e o novo PDF submetido.
- **RF-POL-03**: Garantir que apenas UMA versão da norma esteja no estado `ACTIVE` por tenant via banco relacional.
- **RF-RULE-01**: Avaliar os critérios da norma ativa exclusivamente a partir da árvore JSON-Logic compilada do PDF vigente contra o *Case Fact Model*.
- **RF-RULE-02**: Emitir veredito estruturado baseado na tríade: `PASS`, `FAIL` ou `UNKNOWN`.
- **RF-RULE-03**: Classificar o processo como `ELIGIBLE`, `INELIGIBLE`, `REQUIRES_HUMAN_REVIEW` ou `CONDITIONALLY_ELIGIBLE`.

### 5. Auditoria e Human-in-the-Loop (HITL/AUDIT)
- **RF-HITL-01**: Rotear para a fila prioritária de revisão humana qualquer processo com confiança < 85%, documento obrigatório ausente ou regra `UNKNOWN`.
- **RF-HITL-02**: Exibir visualizador split-screen: PDF com overlay da Bounding Box da evidência à esquerda e critérios avaliados à direita.
- **RF-AUD-01**: Manter log de auditoria imutável com snapshot da norma usada (`policy_version_id`), fatos, evidências e autor da decisão.

---

## Requisitos Não Funcionais (RNF)

- **RNF-01 (Throughput)**: Suportar vazão nominal de 50.000 páginas/dia (~104 páginas/minuto) e picos de 100.000 páginas/dia.
- **RNF-02 (Latência)**: Processar um processo nominal de 500 páginas em menos de 6 minutos.
- **RNF-03 (Segurança & LGPD)**: Isolamento multi-tenant via Row-Level Security (RLS) no PostgreSQL, criptografia em trânsito (TLS 1.3) e em repouso.
- **RNF-04 (Custos)**: Custo operacional total por processo de 500 páginas inferior a R$ 1,00.
- **RNF-05 (Infraestrutura)**: Operação sobre VPS Linux distribuída via Docker Compose sem dependência mandatória de cloud proprietária.
