"""
src/ocr/google_vision_client.py
Cliente de OCR de Alta Fidelidade via Google Cloud Vision API (DOCUMENT_TEXT_DETECTION).
Fornece extração hierárquica de texto, palavras, símbolos e Bounding Boxes espaciais para Evidence Grounding.
"""

import os
import json
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from src.core.config import settings

class GoogleVisionOCRClient:
    """
    Cliente REST de alta performance para o Google Cloud Vision API.
    Utiliza preferencialmente a API Key direta para evitar overhead de autenticação OAuth2,
    com suporte transparente ao formato de Bounding Boxes [ymin, xmin, ymax, xmax] (0 a 1000).
    """

    ENDPOINT_URL = "https://vision.googleapis.com/v1/images:annotate"

    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "GOOGLE_VISION_API_KEY", None) or getattr(settings, "GEMINI_API_KEY", None) or os.getenv("GOOGLE_VISION_API_KEY") or os.getenv("GEMINI_API_KEY")

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def process_image_bytes(self, image_bytes: bytes, width: int = 1, height: int = 1) -> Optional[Dict[str, Any]]:
        """
        Envia os bytes da imagem (PNG/JPEG) para a Vision API e extrai texto denso com Bounding Boxes.
        """
        if not self.is_available():
            return None

        url = f"{self.ENDPOINT_URL}?key={self.api_key}"
        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "requests": [
                {
                    "image": {
                        "content": b64_image
                    },
                    "features": [
                        {
                            "type": "DOCUMENT_TEXT_DETECTION",
                            "maxResults": 1
                        }
                    ],
                    "imageContext": {
                        "languageHints": ["pt", "en"]
                    }
                }
            ]
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=12.0) as resp:
                result_json = json.loads(resp.read().decode("utf-8"))
                responses = result_json.get("responses", [])
                if not responses:
                    return None
                
                resp_data = responses[0]
                if "error" in resp_data:
                    return None

                return self._parse_vision_response(resp_data, width=width, height=height)
        except Exception:
            return None

    def _parse_vision_response(self, response_data: Dict[str, Any], width: int, height: int) -> Dict[str, Any]:
        """
        Converte a anotação hierárquica do Google Vision para o formato canônico de Evidence Grounding.
        """
        full_text_annotation = response_data.get("fullTextAnnotation", {})
        raw_text = full_text_annotation.get("text", "")
        
        words_data: List[Dict[str, Any]] = []
        confidences: List[float] = []

        w = max(width, 1)
        h = max(height, 1)

        pages = full_text_annotation.get("pages", [])
        for page in pages:
            for block in page.get("blocks", []):
                for paragraph in block.get("paragraphs", []):
                    for word in paragraph.get("words", []):
                        symbols = word.get("symbols", [])
                        word_text = "".join([s.get("text", "") for s in symbols])
                        word_confidence = word.get("confidence", 0.95)
                        confidences.append(word_confidence)

                        # Extrai Bounding Box do polígono
                        bbox_obj = word.get("boundingBox", {})
                        vertices = bbox_obj.get("vertices", []) or bbox_obj.get("normalizedVertices", [])

                        if len(vertices) >= 2:
                            # Se os vértices forem normalizados (0.0 a 1.0)
                            is_normalized = all(v.get("x", 0) <= 1.0 and v.get("y", 0) <= 1.0 for v in vertices if "x" in v or "y" in v)
                            
                            if is_normalized:
                                x0 = min(v.get("x", 0.0) for v in vertices) * 1000
                                y0 = min(v.get("y", 0.0) for v in vertices) * 1000
                                x1 = max(v.get("x", 0.0) for v in vertices) * 1000
                                y1 = max(v.get("y", 0.0) for v in vertices) * 1000
                            else:
                                raw_x0 = min(v.get("x", 0) for v in vertices)
                                raw_y0 = min(v.get("y", 0) for v in vertices)
                                raw_x1 = max(v.get("x", 0) for v in vertices)
                                raw_y1 = max(v.get("y", 0) for v in vertices)

                                x0 = (raw_x0 / w) * 1000
                                y0 = (raw_y0 / h) * 1000
                                x1 = (raw_x1 / w) * 1000
                                y1 = (raw_y1 / h) * 1000

                            words_data.append({
                                "text": word_text,
                                "confidence": round(word_confidence, 4),
                                "bbox": [
                                    round(min(max(y0, 0), 1000), 1),
                                    round(min(max(x0, 0), 1000), 1),
                                    round(min(max(y1, 0), 1000), 1),
                                    round(min(max(x1, 0), 1000), 1)
                                ]
                            })

        mean_conf = sum(confidences) / len(confidences) if confidences else (1.0 if raw_text else 0.0)

        return {
            "raw_text": raw_text,
            "words_data": words_data,
            "mean_confidence": round(mean_conf, 4),
            "engine": "Google Cloud Vision (DOCUMENT_TEXT_DETECTION)"
        }
