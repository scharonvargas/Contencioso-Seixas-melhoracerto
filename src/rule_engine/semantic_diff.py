"""
src/rule_engine/semantic_diff.py
Comparador estruturado e semântico entre versões da Norma Interna.
"""

from typing import Dict, Any, List
from pydantic import BaseModel, Field

class RuleDiff(BaseModel):
    rule_code: str
    title: str
    diff_type: str  # "ADDED", "REMOVED", "MODIFIED"
    details: str

class PolicyDiffResult(BaseModel):
    base_version: str
    target_version: str
    rules_added: List[RuleDiff]
    rules_removed: List[RuleDiff]
    rules_modified: List[RuleDiff]
    summary: str

class PolicySemanticDiff:
    @staticmethod
    def compare_policies(base_policy_rules: List[dict], target_policy_rules: List[dict], base_ver: str, target_ver: str) -> PolicyDiffResult:
        base_map = {r["rule_code"]: r for r in base_policy_rules}
        target_map = {r["rule_code"]: r for r in target_policy_rules}

        added: List[RuleDiff] = []
        removed: List[RuleDiff] = []
        modified: List[RuleDiff] = []

        # 1. Regras adicionadas
        for code, rule in target_map.items():
            if code not in base_map:
                added.append(RuleDiff(
                    rule_code=code,
                    title=rule.get("title", code),
                    diff_type="ADDED",
                    details=f"Nova regra criada: {rule.get('description', '')}"
                ))

        # 2. Regras removidas
        for code, rule in base_map.items():
            if code not in target_map:
                removed.append(RuleDiff(
                    rule_code=code,
                    title=rule.get("title", code),
                    diff_type="REMOVED",
                    details=f"Regra descontinuada na versão {target_ver}."
                ))

        # 3. Regras modificadas
        for code, t_rule in target_map.items():
            if code in base_map:
                b_rule = base_map[code]
                changes = []
                
                if t_rule.get("condition") != b_rule.get("condition"):
                    changes.append("Condição lógica alterada")
                if t_rule.get("mandatory") != b_rule.get("mandatory"):
                    changes.append(f"Obrigatoriedade alterada de {b_rule.get('mandatory')} para {t_rule.get('mandatory')}")
                if t_rule.get("required_evidence_fields") != b_rule.get("required_evidence_fields"):
                    changes.append("Requisitos de comprovação documental alterados")

                if changes:
                    modified.append(RuleDiff(
                        rule_code=code,
                        title=t_rule.get("title", code),
                        diff_type="MODIFIED",
                        details="; ".join(changes)
                    ))

        summary = (
            f"Comparação entre {base_ver} e {target_ver}: "
            f"{len(added)} adicionadas, {len(removed)} removidas, {len(modified)} alteradas."
        )

        return PolicyDiffResult(
            base_version=base_ver,
            target_version=target_ver,
            rules_added=added,
            rules_removed=removed,
            rules_modified=modified,
            summary=summary
        )
