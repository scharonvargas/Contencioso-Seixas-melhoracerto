# AGENTS.md — Diretrizes Inegociáveis do Seixas AI

Este documento estabelece as regras fundamentais de arquitetura, domínio e governança para todos os agentes e desenvolvedores que atuam no **Seixas AI**.

---

## 🔒 REGRA SUPREMA E INEVEGÁVEL (ZERO HARDCODED RULES)

> [!CRITICAL]
> **NÃO PODE HAVER NENHUMA REGRA DE NEGÓCIO, TETO OU CRITÉRIO FIXO / HARDCODED NO CÓDIGO.**
> 
> 1. **Fonte Única no PDF da Norma Ativa**: Todas as regras, tetos financeiros, alçadas, requisitos de cobertura, vedações, temas, percentuais de saving e condicionantes **SEMPRE** derivam exclusivamente do arquivo PDF da Norma/Instrução de Trabalho que o usuário faz upload no sistema.
> 2. **Dinamismo Temporal**: A norma corporativa muda de tempos em tempos (trimestralmente, anualmente ou sob demanda). O sistema deve re-compilar dinamicamente qualquer PDF de norma submetido e respeitar estrita e exclusivamente as regras contidas no PDF que estiver no estado `ACTIVE` no banco.
> 3. **Papel do Código vs. Papel da Norma**:
>    - O **Código** (`src/`) implementa apenas:
>      - Motor de execução determinístico (interpretador agnóstico de árvores JSON-Logic).
>      - Pipeline de OCR e Evidence Grounding (garantia espacial de não-alucinação).
>      - Validadores estruturais/matemáticos de integridade de dados (CPF, CNPJ, Moeda, CNJ).
>    - A **Norma Ativa** (PDF compilado) define:
>      - O que paga, o que não paga, quanto paga, quais métodos são permitidos, quais são vedados e quais as condições exigidas.
> 4. **Zero Viés / Zero Análise Jurídica Externa**: O sistema e o LLM não realizam jurisprudência, doutrina ou regras externas. Apenas a Norma Ativa em vigor rege a decisão.

---

## 📐 Princípios de Engenharia

1. **Evidence-First**: Nenhum fato documental existe sem `document_id`, `page_number`, `bounding_box` e `text_snippet` validado.
2. **Tríade Booleana**: Todo critério avalia em `PASS`, `FAIL` ou `UNKNOWN`. Qualquer incerteza encaminha o caso para a fila de *Human-in-the-Loop* (HITL).
3. **Transição Atômica de Norma**: Apenas uma versão de norma está `ACTIVE` por tenant. Alterar a norma não reprocessa OCRs antigos (*Zero Reprocessing*).
4. **Testes Automatizados Determinísticos**: Toda nova funcionalidade deve ser acompanhada de testes TDD garantindo conformidade sem quebrar as 28 suítes existentes.
