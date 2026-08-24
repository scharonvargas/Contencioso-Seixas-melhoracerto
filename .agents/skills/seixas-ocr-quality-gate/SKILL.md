---
name: seixas-ocr-quality-gate
description: "Quality Gate de OCR e extração documental: validação de confiança, cascade engine (nativo -> OCR -> preprocess), detecção de ilegibilidade e roteamento HITL."
---

# Seixas OCR Quality Gate

Esta skill estabelece o controle de qualidade do pipeline de OCR e ingestão de documentos no Seixas AI.

---

## 🔍 Pipeline de Extração em Cascata

```text
[PDF Upload]
     │
     ├── 1. Tentativa de Texto Nativo (PyMuPDF / pdfplumber)
     │        └── Sucesso com confiança alta? ──> [Fatos Extraídos]
     │
     ├── 2. Fallback: OCR Direto (Tesseract / EasyOCR / Vision)
     │        └── Confiança >= 0.85? ──────────> [Fatos Extraídos]
     │
     ├── 3. Pré-processamento de Imagem (Deskew, Denoise, Binarização)
     │        └── Re-executar OCR ─────────────> [Fatos Extraídos]
     │
     └── 4. Falha / Baixa Confiança (< 0.70)
              └── Estado: UNKNOWN ─────────────> [Fila HITL]
```

---

## 🚫 Proibições e Requisitos Mandatórios

1. **Confiança Real**:
   - É proibido atribuir score arbitrário (ex: `confidence = 0.85`) quando a extração falhar ou o texto for ruidoso.
2. **Registro de Falhas**:
   - Páginas ilegíveis devem ter seu status registrado no `execution_trace` para auditoria.
3. **Preservação de Layout e Coordenadas**:
   - As bounding boxes devem manter a referência exata da página renderizada em 150/300 DPI.
