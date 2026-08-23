from pydantic import BaseModel, Field
from typing import List, Optional, Any, Dict
from enum import Enum
from datetime import date

class ProceduralStage(str, Enum):
    PRE_SENTENCA = "PRE_SENTENCA"
    POS_SENTENCA_RECURSAL = "POS_SENTENCA_RECURSAL"
    EXECUCAO = "EXECUCAO"
    UNKNOWN = "UNKNOWN"

class DocumentRole(str, Enum):
    CURRENT_PROCESS_EVENT = "CURRENT_PROCESS_EVENT"
    CURRENT_PROCESS_EVIDENCE = "CURRENT_PROCESS_EVIDENCE"
    RELATED_PROCESS_DOCUMENT = "RELATED_PROCESS_DOCUMENT"
    QUOTED_JURISPRUDENCE = "QUOTED_JURISPRUDENCE"
    MEDICAL_DOCUMENT = "MEDICAL_DOCUMENT"
    ADMINISTRATIVE_DOCUMENT = "ADMINISTRATIVE_DOCUMENT"
    INTERNAL_DOCUMENT = "INTERNAL_DOCUMENT"
    AGREEMENT_DOCUMENT = "AGREEMENT_DOCUMENT"
    PAYMENT_DOCUMENT = "PAYMENT_DOCUMENT"
    UNKNOWN_DOCUMENT_ROLE = "UNKNOWN_DOCUMENT_ROLE"

class FactProvenance(str, Enum):
    CLAIMED_FACT = "CLAIMED_FACT"
    DOCUMENTED_FACT = "DOCUMENTED_FACT"
    INTERNAL_CONFIRMED_FACT = "INTERNAL_CONFIRMED_FACT"
    JUDICIAL_FINDING = "JUDICIAL_FINDING"
    OPERATIVE_ORDER = "OPERATIVE_ORDER"

class FactStatus(str, Enum):
    KNOWN = "KNOWN"
    UNKNOWN = "UNKNOWN"
    CONFLICTING = "CONFLICTING"

class EvaluationStatus(str, Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"
    NOT_APPLICABLE = "NOT_APPLICABLE"

class OverallEligibility(str, Enum):
    ELIGIBLE = "ELIGIBLE"
    NOT_ELIGIBLE = "NOT_ELIGIBLE"
    UNDETERMINED = "UNDETERMINED"
    CONDITIONALLY_ELIGIBLE = "CONDITIONALLY_ELIGIBLE"

class OperationalStatus(str, Enum):
    READY_TO_NEGOTIATE = "READY_TO_NEGOTIATE"
    REQUIRES_DATA = "REQUIRES_DATA"
    REQUIRES_COMPLIANCE = "REQUIRES_COMPLIANCE"
    REQUIRES_INTERNAL_APPROVAL = "REQUIRES_INTERNAL_APPROVAL"
    HUMAN_REVIEW = "HUMAN_REVIEW"

class EvidenceSource(BaseModel):
    document_id: Optional[str] = "doc_main"
    document_type: str
    page_number: int
    bounding_box: List[float] = Field(..., description="[ymin, xmin, ymax, xmax] normalizados de 0 a 1000")
    text_snippet: str = Field(..., description="Trecho literal onde o fato foi extraído")
    ocr_engine: str = "PyMuPDF"
    confidence_score: float = 1.0

class EvidenceItem(BaseModel):
    evidence_id: str
    document_id: str
    document_role: DocumentRole = DocumentRole.CURRENT_PROCESS_EVIDENCE
    process_number: str
    page: Optional[int] = None
    bounding_box: Optional[List[float]] = None
    source_type: str = "PRIMARY_DOCUMENT"
    text_excerpt: str = ""

class ExtractedFactItem(BaseModel):
    fact_key: str
    value: Any = None
    data_type: str = "string"
    unit: Optional[str] = None
    status: FactStatus = FactStatus.KNOWN
    confidence: float = 1.0
    provenance: FactProvenance = FactProvenance.DOCUMENTED_FACT
    evidence_ids: List[str] = Field(default_factory=list)

class RuleEvaluationItem(BaseModel):
    rule_id: str
    status: EvaluationStatus = EvaluationStatus.PASS
    effect: str = "ALLOW"
    blocking: bool = False
    expected: Any = None
    actual: Any = None
    evidence_ids: List[str] = Field(default_factory=list)
    reason: Optional[str] = None

class AnalysisMetadata(BaseModel):
    process_number: str
    policy_version_id: str
    analysis_cutoff_at: Optional[str] = None
    analysis_mode: str = "ELIGIBILITY_ANALYSIS"

class ProcessClassification(BaseModel):
    category: str
    theme: str
    stage: ProceduralStage = ProceduralStage.PRE_SENTENCA
    confidence: float = 1.0

class AnalysisResult(BaseModel):
    eligibility: OverallEligibility
    operational_status: OperationalStatus
    confidence: float = 1.0

class AgreementTermsBreakdown(BaseModel):
    allowed: List[str] = Field(default_factory=list)
    allowed_with_limits: List[Dict[str, Any]] = Field(default_factory=list)
    not_allowed: List[str] = Field(default_factory=list)
    requires_approval: List[str] = Field(default_factory=list)

class MissingInformationItem(BaseModel):
    fact_key: str
    required_by_rule: str
    reason: str
    suggested_source: Optional[str] = None

class ConflictItem(BaseModel):
    fact_key: str
    candidates: List[Dict[str, Any]] = Field(default_factory=list)
    impact: str = "HIGH"

class ComprehensiveAnalysisResponse(BaseModel):
    analysis: AnalysisMetadata
    classification: ProcessClassification
    facts: List[ExtractedFactItem]
    rule_evaluations: List[RuleEvaluationItem]
    result: AnalysisResult
    agreement_terms: AgreementTermsBreakdown
    missing_information: List[MissingInformationItem] = Field(default_factory=list)
    conflicts: List[ConflictItem] = Field(default_factory=list)
    alerts: List[str] = Field(default_factory=list)
    evidence: List[EvidenceItem] = Field(default_factory=list)
    decision_explanation: str

# Legacy fact models maintained for backwards-compatibility with tests
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

