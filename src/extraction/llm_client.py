from typing import Optional, List, Dict, Any
from pydantic import BaseModel, Field
import json
import logging
import httpx

from src.core.config import settings
from src.extraction.system_prompt import PROCESS_ANALYZER_SYSTEM_PROMPT

logger = logging.getLogger(__name__)

class EvidenceItemSchema(BaseModel):
    document_type: str = Field(..., description="Tipo do documento: PETICAO_INICIAL, LAUDO_MEDICO, NEGATIVA_OPERADORA, SENTENCA, etc.")
    page_number: int = Field(..., description="Número exato da página onde a evidência foi encontrada")
    text_snippet: str = Field(..., description="Trecho textual exato comprobatório")

class FinancialFactSchema(BaseModel):
    requested_amount: float = Field(0.0, description="Valor total da causa / pedido principal")
    paid_amount_by_beneficiary: Optional[float] = Field(0.0, description="Valor desembolsado pelo beneficiário")
    material_damage_amount: float = Field(0.0, description="Dano material comprovado")
    moral_damage_amount: float = Field(0.0, description="Dano moral pleiteado")
    sucumbence_amount: float = Field(0.0, description="Honorários sucumbenciais")
    has_fiscal_receipt: bool = Field(False, description="Se há nota fiscal ou recibo anexado")
    evidence: Optional[EvidenceItemSchema] = None

class TreatmentFactSchema(BaseModel):
    treatment_type: str = Field("ASSISTENCIAL", description="Tipo de tratamento: TERAPIA_ESPECIAL, ASSISTENCIAL, CIRURGIA, MEDICAMENTO, etc.")
    cid_10: Optional[str] = Field(None, description="Código CID-10 identificado (ex: F84.0)")
    is_urgent: bool = Field(False, description="Se há urgência médica caracterizada")
    tea_methods_detected: List[str] = Field(default_factory=list, description="Métodos para TEA como ABA, DENVER, BOBATH")
    has_valid_medical_prescription: bool = Field(False, description="Se há prescrição médica idônea")
    has_school_aide_request: bool = Field(False, description="Se há pedido de AT escolar ou mediação escolar")
    evidence: Optional[EvidenceItemSchema] = None

class AdministrativeDenialSchema(BaseModel):
    has_administrative_denial: bool = Field(False, description="Se houve prévia negativa administrativa pela operadora")
    protocol_number: Optional[str] = Field(None, description="Número de protocolo da negativa")
    evidence: Optional[EvidenceItemSchema] = None

class ProcessExtractedFacts(BaseModel):
    identified_theme: Optional[str] = Field(None, description="Tema do processo identificado na norma ativa")
    applicable_topic_num: Optional[int] = Field(None, description="Número do tópico/tema correspondente na norma")
    procedural_stage: str = Field("PRE_SENTENCA", description="Fase processual: PRE_SENTENCA, POS_SENTENCA_RECURSAL, EXECUCAO")
    sentenced_amount: Optional[float] = Field(None, description="Valor da condenação líquida em 1º grau (se houver sentença)")
    operator_share_percentage: float = Field(1.0, description="Cota-parte da operadora em litisconsórcio (ex: 1.0 = 100%, 0.5 = 50%)")
    financial: FinancialFactSchema
    treatment: TreatmentFactSchema
    administrative_denial: AdministrativeDenialSchema


class OpenRouterExtractionClient:
    def __init__(self, api_key: Optional[str] = None):
        self._explicit_key = api_key
        self.api_key = api_key or getattr(settings, "OPENROUTER_API_KEY", None)
        self.model = getattr(settings, "LLM_MODEL", "openai/gpt-4o-mini")
        self.base_url = "https://openrouter.ai/api/v1"
        
    def is_configured(self) -> bool:
        if self._explicit_key is not None:
            return bool(self._explicit_key and len(str(self._explicit_key).strip()) > 5)
        current_key = getattr(settings, "OPENROUTER_API_KEY", None)
        if current_key is None:
            current_key = self.api_key or ""
        return bool(current_key and len(str(current_key).strip()) > 5)

    def extract_facts(self, process_text: str, policy_summary: str = "") -> Optional[Dict[str, Any]]:
        """
        Executa extração estruturada via OpenRouter com base no System Prompt e nos fatos processuais.
        """
        if not self.is_configured():
            logger.warning("OPENROUTER_API_KEY não configurada. Fallback necessário.")
            return None

        try:
            from openai import OpenAI
            import instructor

            client = instructor.from_openai(
                OpenAI(
                    base_url=self.base_url,
                    api_key=self.api_key,
                    timeout=httpx.Timeout(60.0, connect=10.0),
                ),
                mode=instructor.Mode.JSON
            )

            prompt_user = f"--- TEXTO DO PROCESSO JUDICIAL PARA EXTRAÇÃO ---\n\n{process_text[:50000]}"
            if policy_summary:
                prompt_user = f"--- RESUMO DA NORMA ATIVA ---\n{policy_summary}\n\n" + prompt_user

            logger.info(f"Enviando texto processual para OpenRouter ({self.model})...")
            
            response: ProcessExtractedFacts = client.chat.completions.create(
                model=self.model,
                response_model=ProcessExtractedFacts,
                messages=[
                    {"role": "system", "content": PROCESS_ANALYZER_SYSTEM_PROMPT},
                    {"role": "user", "content": prompt_user}
                ],
                temperature=0.0,
                max_retries=2
            )

            result_dict = response.model_dump()
            logger.info(f"Extração estruturada da IA concluída com sucesso. Tema: {result_dict.get('identified_theme')}")
            return result_dict

        except Exception as e:
            logger.error(f"Erro ao chamar OpenRouter / instructor: {str(e)}", exc_info=True)
            return None
