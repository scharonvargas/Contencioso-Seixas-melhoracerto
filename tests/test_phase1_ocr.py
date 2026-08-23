import pytest
import fitz
import numpy as np
from src.ingestion.quality_assessor import PageQualityAssessor
from src.ocr.opencv_preprocessor import OpenCVDocumentPreprocessor
from src.ocr.cascade_engine import OCRCascadeEngine

def test_page_quality_assessor_native_pdf():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Petição Inicial do Processo Judicial de Reembolso de Saúde. O autor requer o pagamento de despesas médicas devidamente comprovadas por notas fiscais idôneas juntadas aos autos.")
    
    assessment = PageQualityAssessor.assess_page(page)
    assert assessment["is_native_valid"] is True
    assert assessment["recommended_engine"] == "NATIVE_PYMUPDF"
    assert assessment["char_count"] > 30

def test_opencv_preprocessor_deskew():
    img = np.ones((300, 300, 3), dtype=np.uint8) * 255
    deskewed = OpenCVDocumentPreprocessor.deskew(img)
    assert deskewed.shape == img.shape

def test_ocr_cascade_engine_tier0():
    doc = fitz.open()
    page = doc.new_page()
    page.insert_text((50, 50), "Laudo Médico Pericial. Paciente portador de CID-10 F84.0 em tratamento contínuo.")
    
    engine = OCRCascadeEngine()
    result = engine.process_page(page, page_number=1)
    
    assert result["tier"] == "TIER_0_NATIVE"
    assert result["engine"] == "PyMuPDF"
    assert result["mean_confidence"] == 1.0
    assert len(result["words_data"]) > 0
    assert "CID-10" in result["raw_text"]
