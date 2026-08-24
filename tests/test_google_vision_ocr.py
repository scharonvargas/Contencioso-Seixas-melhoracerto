"""
tests/test_google_vision_ocr.py
Testes unitários para o cliente Google Cloud Vision API e sua integração no OCRCascadeEngine.
"""

import pytest
import fitz
from unittest.mock import MagicMock, patch
from src.ocr.google_vision_client import GoogleVisionOCRClient
from src.ocr.cascade_engine import OCRCascadeEngine

def test_google_vision_client_response_parsing():
    client = GoogleVisionOCRClient(api_key="mock_test_key_123")
    assert client.is_available() is True

    mock_response_data = {
        "fullTextAnnotation": {
            "text": "DANFE NOTA FISCAL ELETRONICA VALOR R$ 1.500,00",
            "pages": [
                {
                    "blocks": [
                        {
                            "paragraphs": [
                                {
                                    "words": [
                                        {
                                            "symbols": [{"text": "D"}, {"text": "A"}, {"text": "N"}, {"text": "F"}, {"text": "E"}],
                                            "confidence": 0.99,
                                            "boundingBox": {
                                                "vertices": [
                                                    {"x": 100, "y": 50},
                                                    {"x": 200, "y": 50},
                                                    {"x": 200, "y": 80},
                                                    {"x": 100, "y": 80}
                                                ]
                                            }
                                        },
                                        {
                                            "symbols": [{"text": "R"}, {"text": "$"}],
                                            "confidence": 0.98,
                                            "boundingBox": {
                                                "vertices": [
                                                    {"x": 210, "y": 50},
                                                    {"x": 250, "y": 50},
                                                    {"x": 250, "y": 80},
                                                    {"x": 210, "y": 80}
                                                ]
                                            }
                                        }
                                    ]
                                }
                            ]
                        }
                    ]
                }
            ]
        }
    }

    parsed = client._parse_vision_response(mock_response_data, width=1000, height=1000)

    assert "DANFE NOTA FISCAL" in parsed["raw_text"]
    assert len(parsed["words_data"]) == 2
    
    word1 = parsed["words_data"][0]
    assert word1["text"] == "DANFE"
    assert word1["confidence"] == 0.99
    # BBox: [ymin, xmin, ymax, xmax] -> [50.0, 100.0, 80.0, 200.0]
    assert word1["bbox"] == [50.0, 100.0, 80.0, 200.0]

    assert parsed["mean_confidence"] >= 0.98
    assert "Google Cloud Vision" in parsed["engine"]

def test_ocr_cascade_engine_with_google_vision_tier():
    # Cria uma página sem texto nativo (scan simulado)
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)
    # Não insere texto nativo

    mock_vision_client = MagicMock()
    mock_vision_client.is_available.return_value = True
    mock_vision_client.process_image_bytes.return_value = {
        "raw_text": "LAUDO MEDICO PERICIAL REQUISITOS TEA ABA COMPROVADOS",
        "words_data": [
            {"text": "LAUDO", "confidence": 0.99, "bbox": [10.0, 20.0, 30.0, 50.0]},
            {"text": "MEDICO", "confidence": 0.98, "bbox": [10.0, 60.0, 30.0, 100.0]}
        ],
        "mean_confidence": 0.985,
        "engine": "Google Cloud Vision (DOCUMENT_TEXT_DETECTION)"
    }

    engine = OCRCascadeEngine(vision_client=mock_vision_client)
    res = engine.process_page(page, page_number=1)

    assert res["tier"] == "TIER_2_MULTIMODAL_VISION"
    assert "Google Cloud Vision" in res["engine"]
    assert "LAUDO MEDICO" in res["raw_text"]
    assert res["mean_confidence"] >= 0.98
    assert res["requires_hitl"] is False
    assert len(res["words_data"]) == 2

def test_ocr_cascade_engine_fallback_when_vision_unavailable():
    doc = fitz.open()
    page = doc.new_page(width=600, height=800)

    mock_vision_client = MagicMock()
    mock_vision_client.is_available.return_value = False

    engine = OCRCascadeEngine(vision_client=mock_vision_client)
    res = engine.process_page(page, page_number=1)

    assert res["tier"] == "TIER_1_UNPROCESSED_SCANNED"
    assert res["requires_hitl"] is True

def test_openrouter_vision_client_generate_words_data():
    from src.ocr.openrouter_vision_client import OpenRouterVisionOCRClient
    client = OpenRouterVisionOCRClient(api_key="mock_key")
    assert client.is_available() is True
    
    text = "DANFE NOTA FISCAL ELETRONICA\nVALOR TOTAL R$ 1.500,00"
    words_data = client._generate_words_data(text, width=1000, height=1000)
    
    assert len(words_data) >= 6
    assert words_data[0]["text"] == "DANFE"
    assert words_data[0]["confidence"] == 0.98
    assert len(words_data[0]["bbox"]) == 4

