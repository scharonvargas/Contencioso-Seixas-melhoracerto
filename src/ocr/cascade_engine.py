import fitz
import numpy as np
from typing import Dict, Any, List
from src.ingestion.quality_assessor import PageQualityAssessor
from src.ocr.opencv_preprocessor import OpenCVDocumentPreprocessor
from src.ocr.google_vision_client import GoogleVisionOCRClient
from src.ocr.openrouter_vision_client import OpenRouterVisionOCRClient

class OCRCascadeEngine:
    """
    Motor de OCR em Cascata de 4 Níveis:
    Tier 0: PyMuPDF (Nativo Vetorial, <10ms, Custo R$ 0,00)
    Tier 1: OpenCV Preprocessor (Deskew, normalização de contraste para scans)
    Tier 2: Visão Multimodal & OCR Inteligente (OpenRouter Vision / Google Cloud Vision)
    Tier 3: Fallback VLM / HITL (Revisão Humana quando confiança for insuficiente)
    """

    def __init__(self, vlm_client=None, vision_client=None):
        self.vlm_client = vlm_client
        if vision_client:
            self.vision_client = vision_client
        else:
            openrouter_client = OpenRouterVisionOCRClient()
            google_client = GoogleVisionOCRClient()
            # Prioriza OpenRouter se configurado, ou Google Vision
            if openrouter_client.is_available():
                self.vision_client = openrouter_client
            else:
                self.vision_client = google_client

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
                "quality_metrics": quality,
                "requires_hitl": False
            }

        # 2. Renderização da Imagem da Página para OCR quando texto nativo for nulo ou scan
        pix = page.get_pixmap(dpi=200)
        img_bytes = pix.tobytes("png")

        # 3. Tier 1: Pré-processamento OpenCV (Deskew / Contraste)
        processed_bytes = OpenCVDocumentPreprocessor.process_degraded_page(img_bytes)

        # 4. Tier 2: Visão Multimodal / OCR Inteligente (OpenRouter Vision / Google Cloud Vision)
        if self.vision_client and self.vision_client.is_available():
            vision_res = self.vision_client.process_image_bytes(
                processed_bytes,
                width=pix.width,
                height=pix.height
            )
            if vision_res and len(vision_res.get("raw_text", "").strip()) > 0:
                raw_text = vision_res["raw_text"]
                mean_conf = vision_res.get("mean_confidence", 0.95)
                return {
                    "page_number": page_number,
                    "tier": "TIER_2_MULTIMODAL_VISION",
                    "engine": vision_res.get("engine", "Multimodal Vision OCR"),
                    "raw_text": raw_text,
                    "words_data": vision_res.get("words_data", []),
                    "mean_confidence": mean_conf,
                    "quality_metrics": quality,
                    "requires_hitl": mean_conf < 0.70
                }

        # 5. Fallback quando nenhum provedor de visão estiver disponível
        raw_text = page.get_text("text").strip()
        words_data = self._extract_native_bboxes(page)

        has_text = len(raw_text) > 0
        return {
            "page_number": page_number,
            "tier": "TIER_0_NATIVE" if has_text else "TIER_1_UNPROCESSED_SCANNED",
            "engine": "PyMuPDF",
            "raw_text": raw_text if has_text else "[Página Digitalizada / Ilegível sem OCR]",
            "words_data": words_data,
            "mean_confidence": 1.0 if has_text else 0.0,
            "quality_metrics": quality,
            "requires_hitl": not has_text
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
