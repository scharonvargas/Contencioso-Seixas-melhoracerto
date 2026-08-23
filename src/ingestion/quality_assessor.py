"""
src/ingestion/quality_assessor.py
Avaliador de qualidade de página com suporte a fallback resiliente quando OpenCV (cv2) não estiver disponível.
"""

import numpy as np
import fitz  # PyMuPDF
from typing import Dict, Any

try:
    import cv2
    HAS_CV2 = True
except Exception:
    HAS_CV2 = False

class PageQualityAssessor:
    """
    Avalia a qualidade de uma página de processo judicial para decidir a melhor rota de extração:
    NATIVE (PyMuPDF) -> LOCAL_OCR (Docling/PaddleOCR) -> PREPROC_OCR -> VLM_FALLBACK.
    """

    @staticmethod
    def assess_page(page: fitz.Page, dpi: int = 150) -> Dict[str, Any]:
        # 1. Análise da Camada Nativa de Texto
        text = page.get_text("text")
        char_count = len(text.strip())
        words = page.get_text("words")
        
        non_printable = sum(1 for c in text if not c.isprintable() and c not in '\n\r\t')
        garbage_ratio = non_printable / max(char_count, 1)
        
        # Critério de texto nativo confiável: qualquer página com texto real não corrompido
        is_native_valid = (
            char_count > 0 and
            garbage_ratio <= 0.15
        )
        
        if is_native_valid:
            return {
                "recommended_engine": "NATIVE_PYMUPDF",
                "is_native_valid": True,
                "char_count": char_count,
                "garbage_ratio": round(garbage_ratio, 4),
                "blur_variance": None,
                "is_blurry": False,
                "needs_preprocessing": False
            }

        # 2. Análise da Imagem Renderizada (para Scans / Fotos)
        pix = page.get_pixmap(dpi=dpi)
        img_bytes = pix.tobytes("png")
        
        if HAS_CV2:
            img_np = cv2.imdecode(np.frombuffer(img_bytes, np.uint8), cv2.IMREAD_GRAYSCALE)
            if img_np is not None:
                laplacian_var = float(cv2.Laplacian(img_np, cv2.CV_64F).var())
                contrast_std = float(np.std(img_np))
                is_blurry = laplacian_var < 100.0
                needs_contrast = contrast_std < 40.0
                needs_preprocessing = is_blurry or needs_contrast
                
                return {
                    "recommended_engine": "PREPROC_OCR" if needs_preprocessing else "LOCAL_OCR",
                    "is_native_valid": False,
                    "char_count": char_count,
                    "garbage_ratio": round(garbage_ratio, 4),
                    "blur_variance": round(laplacian_var, 2),
                    "contrast_std": round(contrast_std, 2),
                    "is_blurry": is_blurry,
                    "needs_preprocessing": needs_preprocessing
                }

        # Fallback sem cv2
        return {
            "recommended_engine": "LOCAL_OCR",
            "is_native_valid": False,
            "char_count": char_count,
            "garbage_ratio": round(garbage_ratio, 4),
            "blur_variance": 150.0,
            "contrast_std": 50.0,
            "is_blurry": False,
            "needs_preprocessing": False
        }
