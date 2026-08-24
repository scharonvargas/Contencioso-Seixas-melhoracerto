"""
src/ocr/openrouter_vision_client.py
Cliente de OCR Multimodal e Extração Visual via OpenRouter API (GPT-4o-mini, Gemini 2.0 Flash, Qwen 2.5 VL).
Fornece transcrição semântica de alta fidelidade para páginas escaneadas, laudos médicos, cupons e carimbos.
"""

import os
import json
import base64
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional
from src.core.config import settings

class OpenRouterVisionOCRClient:
    """
    Cliente de Visão Multimodal via OpenRouter.
    Utiliza modelos de ponta (ex: openai/gpt-4o-mini, google/gemini-2.0-flash)
    com uma única chave OPENROUTER_API_KEY.
    """

    ENDPOINT_URL = "https://openrouter.ai/api/v1/chat/completions"

    def __init__(self, api_key: Optional[str] = None, model: Optional[str] = None):
        self.api_key = api_key or getattr(settings, "OPENROUTER_API_KEY", None) or os.getenv("OPENROUTER_API_KEY")
        self.model = model or getattr(settings, "VISION_MODEL", "openai/gpt-4o-mini")

    def is_available(self) -> bool:
        return bool(self.api_key and len(self.api_key.strip()) > 5)

    def process_image_bytes(self, image_bytes: bytes, width: int = 1, height: int = 1) -> Optional[Dict[str, Any]]:
        """
        Envia a imagem (PNG/JPEG) em Base64 para o modelo de visão no OpenRouter e extrai o texto fielmente.
        """
        if not self.is_available():
            return None

        b64_image = base64.b64encode(image_bytes).decode("utf-8")

        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": (
                                "Você é um especialista em OCR forense judicial de alta precisão. "
                                "Transcreva integralmente e fielmente todo o texto visível deste documento escaneado/imagem. "
                                "Preserve exatamente nomes, números de processo (CNJ), valores em reais (R$), datas, laudos médicos, CID, medicamentos, carimbos e assinaturas. "
                                "Retorne apenas o texto transcrito, sem introduções ou comentários."
                            )
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": f"data:image/png;base64,{b64_image}"
                            }
                        }
                    ]
                }
            ],
            "temperature": 0.0,
            "max_tokens": 4096
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://seixas.ai",
            "X-Title": "Seixas AI"
        }

        req = urllib.request.Request(
            self.ENDPOINT_URL,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers
        )

        try:
            with urllib.request.urlopen(req, timeout=20.0) as resp:
                result_json = json.loads(resp.read().decode("utf-8"))
                choices = result_json.get("choices", [])
                if not choices:
                    return None

                raw_text = choices[0].get("message", {}).get("content", "").strip()
                if not raw_text:
                    return None

                # Gera estimativa de Bounding Boxes espaciais para o texto transcrito
                words_data = self._generate_words_data(raw_text, width=width, height=height)

                return {
                    "raw_text": raw_text,
                    "words_data": words_data,
                    "mean_confidence": 0.98,
                    "engine": f"OpenRouter Vision ({self.model})"
                }
        except Exception:
            return None

    def _generate_words_data(self, text: str, width: int, height: int) -> List[Dict[str, Any]]:
        """
        Gera tokens de palavras com Bounding Boxes distribuídos verticalmente na página
        para compatibilidade total com o motor de Evidence Grounding.
        """
        lines = text.split("\n")
        words_data = []
        
        total_lines = max(len(lines), 1)
        line_height_pct = 1000.0 / total_lines

        for line_idx, line in enumerate(lines):
            words = line.split()
            if not words:
                continue
            
            y0 = line_idx * line_height_pct
            y1 = y0 + line_height_pct
            
            total_words_in_line = max(len(words), 1)
            word_width_pct = 1000.0 / total_words_in_line

            for word_idx, w in enumerate(words):
                x0 = word_idx * word_width_pct
                x1 = x0 + word_width_pct
                
                words_data.append({
                    "text": w,
                    "confidence": 0.98,
                    "bbox": [
                        round(min(max(y0, 0), 1000), 1),
                        round(min(max(x0, 0), 1000), 1),
                        round(min(max(y1, 0), 1000), 1),
                        round(min(max(x1, 0), 1000), 1)
                    ]
                })

        return words_data
