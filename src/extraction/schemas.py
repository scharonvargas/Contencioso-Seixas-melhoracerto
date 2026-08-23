from pydantic import BaseModel, Field
from typing import List, Optional
from enum import Enum
from datetime import date

class ProceduralStage(str, Enum):
    PRE_SENTENCA = "PRE_SENTENCA"
    POS_SENTENCA_RECURSAL = "POS_SENTENCA_RECURSAL"
    EXECUCAO = "EXECUCAO"

class EvidenceSource(BaseModel):
    document_id: Optional[str] = "doc_main"
    document_type: str
    page_number: int
    bounding_box: List[float] = Field(..., description="[ymin, xmin, ymax, xmax] normalizados de 0 a 1000")
    text_snippet: str = Field(..., description="Trecho literal onde o fato foi extraído")
    ocr_engine: str = "PyMuPDF"
    confidence_score: float = 1.0

class MedicalTreatmentFact(BaseModel):
    treatment_type: str = Field(..., description="Tipo do procedimento ou tratamento")
    cid_10: Optional[str] = Field(None, description="Classificação Internacional de Doenças")
    prescribing_doctor: Optional[str] = None
    prescribing_crm: Optional[str] = None
    is_urgent: bool = False
    urgency_lexicon_detected: bool = False
    urgency_matched_term: Optional[str] = None
    tea_methods_detected: List[str] = Field(default_factory=list, description="Métodos de TEA identificados (ABA, Denver, etc.)")
    has_valid_medical_prescription: bool = False
    has_school_aide_request: bool = Field(False, description="Pedido de Acompanhamento Terapêutico (AT) Escolar / Mediação")
    evidence: Optional[EvidenceSource] = None

class FinancialReimbursementFact(BaseModel):
    requested_amount: float = Field(..., description="Valor total da ação judicial")
    paid_amount_by_beneficiary: Optional[float] = Field(None, description="Valor comprovadamente desembolsado")
    material_damage_amount: float = Field(0.0, description="Rubrica A: Dano Material comprovado por recibo/NF")
    moral_damage_amount: float = Field(0.0, description="Rubrica B: Dano Moral pleiteado/condenado")
    sucumbence_amount: float = Field(0.0, description="Honorários sucumbenciais")
    has_fiscal_receipt: bool = Field(False, description="Existência de Nota Fiscal / Recibo idôneo")
    fiscal_receipt_number: Optional[str] = None
    provider_cnpj_or_cpf: Optional[str] = None
    evidence: Optional[EvidenceSource] = None

class AdministrativeDenialFact(BaseModel):
    has_administrative_denial: bool = Field(False, description="Houve negativa administrativa prévia da operadora")
    protocol_number: Optional[str] = None
    denial_date: Optional[str] = None
    evidence: Optional[EvidenceSource] = None

class CaseFactModel(BaseModel):
    process_id: str
    tenant_id: str
    cnj_number: str
    beneficiary_name: str
    beneficiary_cpf: Optional[str] = None
    operator_name: str
    procedural_stage: str = Field("PRE_SENTENCA", description="PRE_SENTENCA, POS_SENTENCA_RECURSAL, EXECUCAO")
    sentenced_amount: Optional[float] = Field(None, description="Valor da condenação líquida de 1º grau")
    is_joint_litigation: bool = Field(False, description="Existência de litisconsórcio passivo com outros corréus")
    operator_share_percentage: float = Field(1.0, description="Cota-parte de responsabilidade da operadora (ex: 0.5 para 50%)")
    treatment: MedicalTreatmentFact
    financial: FinancialReimbursementFact
    administrative_denial: AdministrativeDenialFact
    pipeline_version: str = "1.0.0"

