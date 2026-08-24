# AGENTS.md — Diretrizes Inegociáveis do Seixas AI

Este documento estabelece as regras fundamentais de arquitetura, domínio e governança para todos os agentes e desenvolvedores que atuam no **Seixas AI**.

---

## 🔒 SYSTEM — GLOBAL SAFETY CONTRACT

> [!CRITICAL]
> **Você participa de um sistema de análise de processos baseado em políticas internas versionadas.**
>
> ### PRINCÍPIOS INVIOLÁVEIS:
>
> 1. **A política de negócio é DINÂMICA.**
> 2. **Nenhuma regra histórica é válida por padrão.**
> 3. **Nunca utilizar regras de outra PolicyVersion.**
> 4. **Nunca utilizar legislação, jurisprudência, doutrina, internet ou conhecimento jurídico do modelo para determinar elegibilidade.**
> 5. **Nunca inventar fatos ausentes.**
> 6. **Ausência de evidência NÃO significa evidência de ausência.**
> 7. **UNKNOWN é diferente de FALSE.**
> 8. **Pedido é diferente de fato.**
> 9. **Alegação é diferente de documento comprobatório.**
> 10. **Fundamentação judicial é diferente de dispositivo.**
> 11. **Documento de outro processo não pode alterar os eventos do processo atual.**
> 12. **Jurisprudência citada não é evento do processo atual.**
> 13. **Valor da causa, valor do pedido, valor do procedimento, RCA, condenação e proposta são fatos diferentes.**
> 14. **Não utilizar acordo posterior ou comprovante de pagamento para concluir retrospectivamente que um processo era elegível.**
> 15. **Nenhum fato crítico pode ser utilizado sem evidência rastreável.**
> 16. **O LLM NÃO possui autoridade para criar, alterar ou ignorar regras da PolicyVersion.**
> 17. **O LLM NÃO deve tomar a decisão final de elegibilidade quando essa decisão puder ser executada pelo Rule Engine.**
> 18. **Se uma informação necessária não puder ser comprovada, retornar UNKNOWN.**
> 19. **Se houver conflito entre evidências relevantes, retornar CONFLICTING.**
> 20. **Sempre preservar provenance e evidence_ids.**
>
> *Nunca tente obter a resposta "mais provável".*
> *Seu objetivo é produzir dados suficientemente comprovados para que o sistema tome uma decisão auditável.*

---

## 🔒 REGRA SUPREMA E INEGOCIÁVEL (ZERO HARDCODED RULES)

1. **Fonte Única no PDF da Norma Ativa**: Todas as regras, tetos financeiros, alçadas, requisitos de cobertura, vedações, temas, percentuais de saving e condicionantes **SEMPRE** derivam exclusivamente do arquivo PDF da Norma/Instrução de Trabalho que o usuário faz upload no sistema.
2. **Dinamismo Temporal**: A norma corporativa muda de tempos em tempos (trimestralmente, anualmente ou sob demanda). O sistema deve re-compilar dinamicamente qualquer PDF de norma submetido e respeitar estrita e exclusivamente as regras contidas no PDF que estiver no estado `ACTIVE` no banco.
3. **Papel do Código vs. Papel da Norma**:
   - O **Código** (`src/`) implementa apenas:
     - Motor de execução determinístico (interpretador agnóstico de árvores JSON-Logic).
     - Pipeline de OCR e Evidence Grounding (garantia espacial de não-alucinação).
     - Validadores estruturais/matemáticos de integridade de dados (CPF, CNPJ, Moeda, CNJ).
   - A **Norma Ativa** (PDF compilado) define:
     - O que paga, o que não paga, quanto paga, quais métodos são permitidos, quais são vedados e quais as condições exigidas.
4. **Zero Viés / Zero Análise Jurídica Externa**: O sistema e o LLM não realizam jurisprudência, doutrina ou regras externas. Apenas a Norma Ativa em vigor rege a decisão.

---

## 📐 Princípios de Engenharia

1. **Evidence-First**: Nenhum fato documental existe sem `document_id`, `page_number`, `bounding_box` e `text_snippet` validado.
2. **Tríade Booleana**: Todo critério avalia em `PASS`, `FAIL` ou `UNKNOWN`. Qualquer incerteza encaminha o caso para a fila de *Human-in-the-Loop* (HITL).
3. **Transição Atômica de Norma**: Apenas uma versão de norma está `ACTIVE` por tenant. Alterar a norma não reprocessa OCRs antigos (*Zero Reprocessing*).
4. **Testes Automatizados Determinísticos**: Toda nova funcionalidade deve ser acompanhada de testes TDD garantindo conformidade sem quebrar as 28 suítes existentes.
5. **Rastreabilidade Forense Multi-Fases**: Todas as 6 fases da análise (Ingestão, Segmentação, Extração, Classificação de Tema, Avaliação de Regras e Veredito) devem ser registradas no `execution_trace` e persistidas em disco para auditoria completa.

