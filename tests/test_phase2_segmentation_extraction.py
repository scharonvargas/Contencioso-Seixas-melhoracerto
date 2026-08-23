import pytest
from src.segmentation.segmenter import DocumentSegmenter, DocumentCategory
from src.extraction.evidence_grounding import EvidenceGroundingValidator
from src.extraction.schemas import CaseFactModel, MedicalTreatmentFact, FinancialReimbursementFact, AdministrativeDenialFact

def test_document_segmenter_classification():
    text_peticao = "EXCELENTÍSSIMO SENHOR DOUTOR JUIZ DE DIREITO. Ação Ordinária de Reembolso..."
    category = DocumentSegmenter.classify_page(text_peticao)
    assert category == DocumentCategory.PETICAO_INICIAL

    text_nf = "DANFE - Documento Auxiliar da Nota Fiscal de Serviços Eletrônica. Prestador: Hospital..."
    category_nf = DocumentSegmenter.classify_page(text_nf)
    assert category_nf == DocumentCategory.NOTA_FISCAL

def test_evidence_grounding_valid_snippet():
    raw_page_text = "O autor realizou tratamento de Terapia ABA no valor de R$ 25.000,00 comprovado pela NF 1234."
    words_data = [
        {"text": "Terapia", "bbox": [100.0, 150.0, 120.0, 220.0]},
        {"text": "ABA", "bbox": [100.0, 230.0, 120.0, 280.0]},
        {"text": "25.000,00", "bbox": [100.0, 400.0, 120.0, 500.0]}
    ]
    
    valid, evidence = EvidenceGroundingValidator.validate_and_create_evidence(
        extracted_snippet="Terapia ABA no valor de R$ 25.000,00",
        page_raw_text=raw_page_text,
        words_data=words_data,
        document_type="NOTA_FISCAL",
        page_number=14
    )
    
    assert valid is True
    assert evidence is not None
    assert evidence["page_number"] == 14
    assert evidence["bounding_box"][0] == 100.0

def test_evidence_grounding_hallucination_prevention():
    raw_page_text = "O autor realizou tratamento de fisioterapia motora."
    
    # LLM alucina um procedimento que não existe no texto da página
    valid, evidence = EvidenceGroundingValidator.validate_and_create_evidence(
        extracted_snippet="Cirurgia Cardíaca de Alta Complexidade",
        page_raw_text=raw_page_text,
        words_data=[],
        document_type="LAUDO_MEDICO",
        page_number=5
    )
    
    assert valid is False
    assert evidence is None
