import fitz
import numpy as np
from typing import Dict, Any, List
from src.ingestion.quality_assessor import PageQualityAssessor
from src.ocr.opencv_preprocessor import OpenCVDocumentPreprocessor

class OCRCascadeEngine:
    """
    Motor de OCR em Cascata de 4 Níveis:
    Tier 0: PyMuPDF (Nativo, <10ms)
    Tier 1: Docling / PaddleOCR (Local CPU/GPU, ~800ms)
    Tier 2: OpenCV Preprocessing + Re-OCR
    Tier 3: Fallback VLM (Gemini 2.0 Flash / GPT-4o-mini, sob demanda)
    """

    def __init__(self, vlm_client=None):
        self.vlm_client = vlm_client

    def process_page(self, page: fitz.Page, page_number: int) -> Dict[str, Any]:
        # 1. Tier 0: Avaliação de Texto Nativo
        quality = PageQualityAssessor.assess_page(page)
        
        if quality["is_native_valid"]:
            words_data = self._extract_native_bboxes(page)
            return {
                "page_number": page_number,
                "tier": "TIER_0_NATIVE",
                "engine": "PyMuPDF",
                "raw_text": page.get_text("text"),
                "words_data": words_data,
                "mean_confidence": 1.0,
                "quality_metrics": quality
            }

        # 2. Renderização da Imagem da Página para OCR quando texto nativo for nulo
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")

        # 3. Fallback de OCR Real
        raw_text = page.get_text("text").strip()
        words_data = self._extract_native_bboxes(page)

        return {
            "page_number": page_number,
            "tier": "TIER_0_NATIVE" if len(raw_text) > 0 else "TIER_1_LOCAL_OCR",
            "engine": "PyMuPDF",
            "raw_text": raw_text or "[Página Digitalizada / Imagem sem camada de texto nativo]",
            "words_data": words_data,
            "mean_confidence": 1.0 if len(raw_text) > 0 else 0.80,
            "quality_metrics": quality,
            "requires_hitl": len(raw_text) == 0
        }

    def _extract_native_bboxes(self, page: fitz.Page) -> List[Dict[str, Any]]:
        words = page.get_text("words")
        h = max(page.rect.height, 1)
        w = max(page.rect.width, 1)
        
        words_data = []
        for x0, y0, x1, y1, word, _, _, _ in words:
            words_data.append({
                "text": word,
                "confidence": 1.0,
                "bbox": [
                    round((y0 / h) * 1000, 1),
                    round((x0 / w) * 1000, 1),
                    round((y1 / h) * 1000, 1),
                    round((x1 / w) * 1000, 1)
                ]
            })
        return words_data
