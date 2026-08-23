from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import re
from src.rule_engine.json_logic_evaluator import evaluate_json_logic
from src.validators.brazilian_validators import BrazilianDomainValidator

class RuleEvaluationResult(BaseModel):
    rule_code: str
    title: str
    status: str  # "PASS", "FAIL", "UNKNOWN"
    evaluated_value: Any = None
    failure_reason: Optional[str] = None
    evidence_ids: List[str] = Field(default_factory=list)

class DecisionEngineResult(BaseModel):
    process_id: str
    policy_version_id: str
    overall_verdict: str  # "ELIGIBLE", "INELIGIBLE", "REQUIRES_HUMAN_REVIEW", "CONDITIONALLY_ELIGIBLE"
    rule_results: List[RuleEvaluationResult]
    summary: str
    conditional_clauses: List[str] = Field(default_factory=list)
    saving_analysis: Optional[Dict[str, Any]] = None
    segregated_amounts: Optional[Dict[str, float]] = None

class DeterministicRuleEngine:
    """
    Motor de Decisão 100% Determinístico.
    O LLM não toma decisões. O veredito é emitido exclusivamente pela avaliação da árvore JSON-Logic da Norma Ativa.
    """

    def __init__(self, structured_policy: dict):
        self.policy_version_id = structured_policy.get("policy_version_id", "default_policy")
        self.rules = structured_policy.get("rules", [])

    def evaluate(self, process_id: str, case_fact_data: dict) -> DecisionEngineResult:
        rule_results: List[RuleEvaluationResult] = []
        has_critical_failure = False
        has_unknown = False
        conditional_clauses: List[str] = []

        # 1. Enriquecimento Determinístico de Fatos Clínicos e Financeiros
        enriched_facts = self._enrich_facts_deterministically(case_fact_data)
        flat_facts = self._flatten_fact_values(enriched_facts)
        applicable_topic_num = enriched_facts.get("applicable_topic_num")

        # 2. Avaliação de Regras da Norma Ativa
        for rule in self.rules:
            rule_code = rule["rule_code"]
            title = rule["title"]
            condition = rule["condition"]
            required_evidences = rule.get("required_evidence_fields", [])

            # Se for regra de tema específico (TEMA_XX_), avalia apenas se for o tema do processo
            tema_match = re.match(r'TEMA_(\d{1,2})_', rule_code)
            if tema_match and applicable_topic_num is not None:
                rule_topic_num = int(tema_match.group(1))
                if rule_topic_num != applicable_topic_num:
                    continue
            
            # 2.1 Validação de Evidência Obrigatória
            missing_evidence = False
            for req_field in required_evidences:
                evidence_obj = self._extract_nested_value(enriched_facts, f"{req_field}.evidence")
                if not evidence_obj:
                    val = self._extract_nested_value(enriched_facts, req_field)
                    if isinstance(val, dict) and val.get("evidence"):
                        evidence_obj = val.get("evidence")
                if not evidence_obj:
                    missing_evidence = True
                    break

            if missing_evidence:
                rule_results.append(RuleEvaluationResult(
                    rule_code=rule_code,
                    title=title,
                    status="UNKNOWN",
                    failure_reason=f"Evidência documental obrigatória não comprovada para o critério: {title}"
                ))
                has_unknown = True
                continue

            # 2.2 Avaliação Determinística da Expressão Lógica
            try:
                passed = bool(evaluate_json_logic(condition, flat_facts))
                if passed:
                    rule_results.append(RuleEvaluationResult(
                        rule_code=rule_code,
                        title=title,
                        status="PASS"
                    ))
                else:
                    failure_msg = rule.get("failure_message_template", "Critério não atendido.")
                    for k, v in flat_facts.items():
                        failure_msg = failure_msg.replace(f"{{{{{k}}}}}", str(v))

                    rule_results.append(RuleEvaluationResult(
                        rule_code=rule_code,
                        title=title,
                        status="FAIL",
                        failure_reason=failure_msg
                    ))
                    if rule.get("mandatory", True):
                        has_critical_failure = True

            except Exception as e:
                rule_results.append(RuleEvaluationResult(
                    rule_code=rule_code,
                    title=title,
                    status="UNKNOWN",
                    failure_reason=f"Falha técnica na avaliação da regra: {str(e)}"
                ))
                has_unknown = True

        # 3. Análise de Pós-Sentença / Recursal e Memória de Cálculo de Saving
        saving_analysis = None
        procedural_stage = enriched_facts.get("procedural_stage", "PRE_SENTENCA")
        sentenced_amount = enriched_facts.get("sentenced_amount")
        if procedural_stage == "POS_SENTENCA_RECURSAL" or sentenced_amount:
            requested = enriched_facts.get("financial", {}).get("requested_amount", 0.0)
            target_sentenced = sentenced_amount if sentenced_amount else requested
            op_share = enriched_facts.get("operator_share_percentage", 1.0)
            saving_analysis = BrazilianDomainValidator.calculate_judicial_settlement_saving(
                sentenced_amount=target_sentenced,
                proposal_amount=requested,
                operator_share=op_share
            )

        # 4. Tratamento de Vedações Parciais e Acordos Condicionados (A.T. Escolar)
        has_school_aide = enriched_facts.get("treatment", {}).get("has_school_aide_request", False)
        is_conditionally_eligible = False
        if has_school_aide and not has_critical_failure and not has_unknown:
            is_conditionally_eligible = True
            conditional_clauses.append(
                "RENUNCIA_EXPRESSA_AT_ESCOLAR: Proposta autorizada exclusivamente para as terapias clínicas em rede credenciada "
                "(teto normativo), condicionada à expressa e irretratável renúncia da parte autora quanto ao pedido de "
                "Acompanhamento Terapêutico (AT) em ambiente escolar / mediação escolar, nos termos da jurisprudência consolidada "
                "do STJ (REsp 2.064.964/SP e AgInt no REsp 2.122.472/SP)."
            )

        # 5. Consolidação do Veredito Final
        if has_unknown:
            overall_verdict = "REQUIRES_HUMAN_REVIEW"
            summary = "Processo requer revisão humana devido a evidências ausentes ou inconclusivas."
        elif has_critical_failure:
            overall_verdict = "INELIGIBLE"
            failed_titles = [r.title for r in rule_results if r.status == "FAIL"]
            summary = f"Processo não elegível para acordo. Não atende aos critérios: {'; '.join(failed_titles)}."
        elif is_conditionally_eligible:
            overall_verdict = "CONDITIONALLY_ELIGIBLE"
            summary = "Processo elegível para acordo em caráter CONDICIONADO (exige renúncia expressa a A.T. Escolar homologada judicialmente)."
        else:
            overall_verdict = "ELIGIBLE"
            summary = "Processo 100% elegível para celebração de acordo conforme a norma interna vigente."

        segregated_amounts = {
            "requested_amount": enriched_facts.get("financial", {}).get("requested_amount", 0.0),
            "material_damage_amount": enriched_facts.get("financial", {}).get("material_damage_amount", 0.0),
            "moral_damage_amount": enriched_facts.get("financial", {}).get("moral_damage_amount", 0.0),
            "sucumbence_amount": enriched_facts.get("financial", {}).get("sucumbence_amount", 0.0)
        }

        return DecisionEngineResult(
            process_id=process_id,
            policy_version_id=self.policy_version_id,
            overall_verdict=overall_verdict,
            rule_results=rule_results,
            summary=summary,
            conditional_clauses=conditional_clauses,
            saving_analysis=saving_analysis,
            segregated_amounts=segregated_amounts
        )

    def _enrich_facts_deterministically(self, data: dict) -> dict:
        """
        Enriquece fatos clínicos e financeiros via validadores determinísticos em Python puro.
        """
        import copy
        enriched = copy.deepcopy(data)

        treatment = enriched.get("treatment", {})
        if isinstance(treatment, dict):
            # Validação determinística de Urgência
            snippet = treatment.get("evidence", {}).get("text_snippet", "")
            if snippet:
                urgency_res = BrazilianDomainValidator.match_clinical_urgency_expression(snippet)
                if urgency_res["is_urgent"]:
                    treatment["is_urgent"] = True
                    treatment["urgency_lexicon_detected"] = True
                    treatment["urgency_matched_term"] = urgency_res["primary_evidence"]

                tea_res = BrazilianDomainValidator.validate_tea_medical_evidence(snippet)
                if tea_res["is_valid"]:
                    treatment["has_valid_medical_prescription"] = True
                    treatment["tea_methods_detected"] = tea_res["detected_methods"]

        financial = enriched.get("financial", {})
        if isinstance(financial, dict):
            moral = financial.get("moral_damage_amount", 0.0)
            sucumbence = financial.get("sucumbence_amount", 0.0)
            # Capped amount considera apenas moral + sucumbência para teste de teto de alçada
            financial["capped_amount"] = moral + sucumbence if (moral > 0 or sucumbence > 0) else financial.get("requested_amount", 0.0)

        return enriched

    def _extract_nested_value(self, data: dict, path: str) -> Any:
        keys = path.split(".")
        curr = data
        for k in keys:
            if isinstance(curr, dict) and k in curr:
                curr = curr[k]
            else:
                return None
        return curr

    def _flatten_fact_values(self, data: dict, prefix: str = "") -> dict:
        flattened = {}
        for k, v in data.items():
            key = f"{prefix}.{k}" if prefix else k
            if isinstance(v, dict):
                if k != "evidence":
                    flattened[key] = v
                    flattened.update(self._flatten_fact_values(v, key))
            else:
                flattened[key] = v
        return flattened

