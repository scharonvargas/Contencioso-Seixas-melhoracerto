# Seixas AI — Plataforma de Validação Automatizada de Acordos de Reembolso em Saúde

## 1. Visão Geral do Produto
O **Seixas AI** é uma plataforma SaaS projetada para automatizar a leitura, classificação, extração de evidências e validação determinística de processos judiciais de reembolso de tratamentos de saúde contra operadoras de planos de saúde, com base **EXCLUSIVA** na norma interna vigente da empresa.

## 2. Princípios Fundamentais Inegociáveis
1. **Zero Regras Hardcode / Decisão Exclusivamente no PDF da Norma Ativa**: É expressamente PROIBIDO ter qualquer regra de negócio, teto, valor, alçada, método clínico, vedação ou parâmetro de acordo fixado em código. Todas as regras derivam de forma 100% dinâmica do arquivo PDF da Norma/Manual que o usuário sobe no sistema. Como a norma muda periodicamente, o sistema re-compila o PDF ativo e aplica estrita e exclusivamente as regras extraídas do documento vigente.
2. **Motor de Regras Determinístico Agnostico**: O LLM **nunca decide** "paga" ou "não paga". O LLM atua unicamente como extrator de fatos documentais estruturados (*Case Fact Model*). O veredito é emitido por código determinístico que executa a árvore JSON-Logic compilada da Norma Ativa.
3. **Evidence-First**: Nenhum fato financeiro ou clínico existe sem rastreamento espacial exato: `document_id`, `page_number`, `bounding_box` e `text_snippet` comprovado.
4. **Tríade Booleana (`PASS`, `FAIL`, `UNKNOWN`, `CONDITIONALLY_ELIGIBLE`)**: Se uma evidência obrigatória não for encontrada ou a confiança for baixa, a regra é avaliada como `UNKNOWN`, encaminhando o caso para a fila prioritária de *Human-in-the-Loop* (HITL).
5. **Norma Única Ativa com Transição Atômica**: Apenas uma versão da norma está ativa por vez no tenant. A atualização da norma não exige reprocessamento de OCR dos processos judiciais já analisados.

## 3. Escala e Dimensionamento
- **Volume Nominal**: 100 processos/dia × 500 páginas/processo = 50.000 páginas/dia (1.500.000 páginas/mês).
- **Cenário de Pico**: Até 100.000 páginas/dia.
- **Infraestrutura**: VPS Linux dedicadas com Docker Compose distribuído, PostgreSQL 16 + RLS, MinIO S3, RabbitMQ e workers escaláveis de CPU.
