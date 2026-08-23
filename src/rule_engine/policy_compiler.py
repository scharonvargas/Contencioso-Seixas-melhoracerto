"""
src/rule_engine/policy_compiler.py
Compilador 100% Dinâmico de Normas/Manuais Corporativos de Acordos em PDF.
Extrai de forma agnóstica e estruturada todos os Temas, Requisitos, Parâmetros de Acordo,
Vedações Pré-Sentença e Regras de Saving a partir do texto do PDF.
"""

import re
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field
import fitz

class DynamicTopicRule(BaseModel):
    topic_number: int = Field(..., description="Número do tema/item no manual (ex: 1, 2, 3...)")
    topic_name: str = Field(..., description="Nome do tema (ex: Terapias Especiais, Home Care, Medicamento, Reembolso...)")
    category: str = Field("ASSISTENCIAL", description="Assistencial, Não Assistencial, ou Geral")
    requirements: List[str] = Field(default_factory=list, description="Requisitos exigidos para celebração do acordo")
    agreement_parameters: List[str] = Field(default_factory=list, description="Parâmetros de valor, dano moral, sucumbência e obrigação de fazer")
    post_sentence_rules: List[str] = Field(default_factory=list, description="Regras pós-sentença e saving exigido")
    prohibitions: List[str] = Field(default_factory=list, description="Hipóteses em que o acordo é expressamente VEDADO")
    mandatory_clauses: List[str] = Field(default_factory=list, description="Minutas ou cláusulas obrigatórias exigidas pelo tema")
    rules: List[Dict[str, Any]] = Field(default_factory=list, description="Árvore de regras JSON-Logic gerada dinamicamente")

class CompiledCorporatePolicy(BaseModel):
    policy_name: str
    company_name: str
    version: str
    file_hash_sha256: str
    total_topics: int
    general_rules: List[str]
    topics: List[DynamicTopicRule]
    all_rules: List[Dict[str, Any]]

class DynamicRule(BaseModel):
    rule_code: str
    title: str
    description: str
    mandatory: bool = True
    condition: Dict[str, Any]
    required_evidence_fields: List[str] = Field(default_factory=list)
    failure_message_template: str

class CompiledPolicy(BaseModel):
    policy_name: str
    version: str
    file_hash_sha256: str
    total_criteria_extracted: int
    rules: List[DynamicRule]

    @classmethod
    def compile_from_pdf_text(
        cls,
        pdf_text: str,
        policy_name: str = "Norma Interna",
        version: str = "1.0",
        file_hash: str = "custom_hash"
    ):
        clauses = re.findall(
            r'(?:Critério|Regra|Cláusula|Item|Artigo)\s*(\d+)[\s.:-]+([^\n]+(?:\n(?!(?:Critério|Regra|Cláusula|Item|Artigo)\s*\d+)[^\n]+)*)',
            pdf_text,
            re.IGNORECASE
        )
        rules = []
        if clauses:
            for idx, (num, clause_text) in enumerate(clauses):
                clause_clean = clause_text.strip()
                first_line = clause_clean.split("\n")[0].strip()
                rule_code = f"CRITERIO_{int(num):03d}"
                field_key = f"facts.criterio_{int(num):03d}"
                
                amount_match = re.search(r'R\$\s*([\d.,]+)', clause_clean)
                if amount_match:
                    from src.validators.brazilian_validators import BrazilianDomainValidator
                    parsed_amt = BrazilianDomainValidator.parse_brazilian_currency(amount_match.group(1))
                    if parsed_amt:
                        condition = {"<=": [{"var": "financial.requested_amount"}, parsed_amt]}
                        req_evidence = ["financial"]
                        fail_msg = f"Valor pleiteado excede o limite estipulado na norma (R$ {parsed_amt:,.2f})."
                    else:
                        condition = {"==": [{"var": f"{field_key}.comprovado"}, True]}
                        req_evidence = [field_key]
                        fail_msg = f"Critério {num} da norma não comprovado documentalmente."
                else:
                    condition = {"==": [{"var": f"{field_key}.comprovado"}, True]}
                    req_evidence = [field_key]
                    fail_msg = f"Critério {num} da norma não comprovado documentalmente."

                rules.append(DynamicRule(
                    rule_code=rule_code,
                    title=first_line[:80],
                    description=clause_clean,
                    mandatory=True,
                    condition=condition,
                    required_evidence_fields=req_evidence,
                    failure_message_template=fail_msg
                ))
        else:
            paragraphs = [p.strip() for p in pdf_text.split("\n\n") if len(p.strip()) > 40]
            for idx, p in enumerate(paragraphs[:10]):
                rule_code = f"NORMA_ITEM_{idx+1:03d}"
                first_line = p.split("\n")[0][:80]
                rules.append(DynamicRule(
                    rule_code=rule_code,
                    title=first_line,
                    description=p,
                    mandatory=True,
                    condition={"==": [{"var": f"facts.item_{idx+1:03d}.comprovado"}, True]},
                    required_evidence_fields=[f"facts.item_{idx+1:03d}"],
                    failure_message_template=f"Critério '{first_line}' não atendido."
                ))

        return CompiledPolicy(
            policy_name=policy_name,
            version=version,
            file_hash_sha256=file_hash,
            total_criteria_extracted=len(rules),
            rules=rules
        )

class DynamicPolicyCompiler:
    """
    Compila o PDF de Instrução de Trabalho / Manual de Acordos em regras estruturadas
    e operacionais sem nenhuma regra hardcoded em código.
    """

    @staticmethod
    def extract_text_from_pdf(pdf_bytes: bytes) -> str:
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        pages_text = []
        for p in doc:
            pages_text.append(p.get_text("text"))
        return "\n\n".join(pages_text)

    @classmethod
    def compile_from_pdf_text(
        cls,
        pdf_text: str,
        policy_name: str = "Norma Interna",
        version: str = "1.0",
        file_hash: str = "custom_hash"
    ):
        return CompiledPolicy.compile_from_pdf_text(pdf_text, policy_name, version, file_hash)

    @classmethod
    def compile_corporate_manual(
        cls,
        pdf_text: str,
        policy_name: str = "Instrução de Trabalho — Acordos",
        version: str = "2026.1",
        file_hash: str = "custom_hash"
    ) -> CompiledCorporatePolicy:
        
        # Limpa marcas d'água e cabeçalhos repetitivos
        cleaned_text = re.sub(r'Informações Internas', '', pdf_text, flags=re.IGNORECASE)

        # Identifica empresa emissora
        company_match = re.search(r'(?:Grupo\s+([A-Za-z0-9\s]+)|Operadora\s+([A-Za-z0-9\s]+)|Amil)', cleaned_text[:500], re.IGNORECASE)
        company_name = company_match.group(0).strip() if company_match else "Operadora de Saúde"

        # Extração de Regras Gerais do Manual
        general_match = re.search(r'Regras gerais:\s*(.*?)(?=Regras especiais|\n\s*[•\-]\s*Assistencial|$)', cleaned_text, re.DOTALL | re.IGNORECASE)
        if general_match:
            general_rules = [
                re.sub(r'^\d+\.\s*', '', line).strip()
                for line in general_match.group(1).split('\n')
                if len(line.strip()) > 8
            ]
        else:
            general_rules = cls._extract_bullet_points(cleaned_text, r'Regras Gerais(?:[\s\w-]+)?:\s*(.*?)(?=(?:Atributos|Regras especiais|$))')

        topics: List[DynamicTopicRule] = []
        all_rules: List[Dict[str, Any]] = []

        # 1. Tenta extração via tópicos numerados estruturados (1. Terapias Especiais:, 2. Home Care:, etc.)
        numbered_topic_pattern = re.compile(
            r'(?:^|\n)\s*(\d{1,3})\.\s+([A-Za-zÀ-ÖØ-öø-ÿ\s\(\)/,\-]{3,120}):\s*\n(.*?)(?=(?:(?:\n\s*\d{1,3}\.\s+[A-Za-zÀ-ÖØ-öø-ÿ\s\(\)/,\-]{3,120}:)|(?:\n\s*Rotinas e Atualização)|(?:\n\s*Atributos do Documento)|$))',
            re.DOTALL
        )
        numbered_matches = list(numbered_topic_pattern.finditer(cleaned_text))

        if len(numbered_matches) >= 2:
            seen_topics = set()
            for m in numbered_matches:
                topic_num = int(m.group(1))
                if topic_num in seen_topics:
                    continue
                seen_topics.add(topic_num)

                raw_title = (m.group(2) or "").strip()
                topic_title = raw_title if (raw_title and len(raw_title) >= 3 and not raw_title.lower().startswith("requisitos")) else f"Tema {topic_num}"

                content = (m.group(3) or "").strip()
                reqs = cls._extract_bullet_points(content, r'Requisitos:(.*?)(?=(?:Parâmetros do Acordo:|Acordos Pós|Não permitido|CLÁUSULA|$))')
                params = cls._extract_bullet_points(content, r'Parâmetros do Acordo:(.*?)(?=(?:Acordos Pós|Não permitido|Requisitos:|CLÁUSULA|$))')
                post_sentence = cls._extract_bullet_points(content, r'Acordos Pós(?:[\s\w-]+)?:\s*(.*?)(?=(?:Não permitido|Parâmetros|Requisitos:|CLÁUSULA|$))')
                prohibitions = cls._extract_bullet_points(content, r'Não permitido(?:[\s\w-]+)?:\s*(.*?)(?=(?:Acordos Pós|Parâmetros|Requisitos:|CLÁUSULA|$))')
                clauses = cls._extract_bullet_points(content, r'CLÁUSULA OBRIGATÓRIA(?:[\s\w-]+)?:\s*(.*?)(?=(?:Acordos Pós|Parâmetros|Requisitos:|Não permitido|$))')

                # Categorização dinâmica e contextual
                is_non_assistential = any(
                    k in (content + " " + topic_title).lower()
                    for k in ["reajuste", "cancelamento", "movimentação", "inativo", "boleto", "fraude", "protesto", "mensalidade", "cadastro", "documento", "rescisão"]
                )
                category = "NÃO ASSISTENCIAL" if is_non_assistential else "ASSISTENCIAL"

                topic_logic_rules = cls._build_topic_logic(topic_num, topic_title, reqs, params, prohibitions)
                all_rules.extend(topic_logic_rules)

                topics.append(DynamicTopicRule(
                    topic_number=topic_num,
                    topic_name=topic_title,
                    category=category,
                    requirements=reqs,
                    agreement_parameters=params,
                    post_sentence_rules=post_sentence,
                    prohibitions=prohibitions,
                    mandatory_clauses=clauses,
                    rules=topic_logic_rules
                ))
        else:
            # 2. Fallback para seções ou marcadores com bullets (• ou -)
            bullet_splits = re.split(r'\n\s*[•\-]\s*', cleaned_text)
            if len(bullet_splits) > 1:
                for idx, section in enumerate(bullet_splits[1:], 1):
                    lines = [l.strip() for l in section.strip().split('\n') if l.strip()]
                    if not lines:
                        continue
                    raw_title = lines[0].strip()
                    clean_title = re.sub(r'\s*\(.*?\)$', '', raw_title).strip()
                    topic_title = clean_title if (clean_title and len(clean_title) >= 2) else f"Tema {idx}"

                    is_non_assistential = any(
                        k in (section + " " + topic_title).lower()
                        for k in ["reajuste", "cancelamento", "movimentação", "inativo", "boleto", "fraude", "protesto", "mensalidade", "cadastro", "documento", "rescisão"]
                    )
                    category = "NÃO ASSISTENCIAL" if is_non_assistential else "ASSISTENCIAL"

                    pre_sentence = cls._extract_bullet_points(section, r'Acordos pré-(?:sentença|condenação):\s*(.*?)(?=(?:Exceções:|Acordos pós|Não faremos|Obs:|$))')
                    post_sentence = cls._extract_bullet_points(section, r'Acordos pós(?:[\s\w-]+)?:\s*(.*?)(?=(?:Exceções:|Obs:|$))')
                    prohibitions = cls._extract_bullet_points(section, r'(?:Exceções:|Não faremos acordos?)\s*(.*?)(?=(?:Acordos|Obs:|$))')
                    
                    params = pre_sentence + post_sentence

                    topic_logic_rules = cls._build_topic_logic(idx, topic_title, pre_sentence, params, prohibitions)
                    all_rules.extend(topic_logic_rules)

                    topics.append(DynamicTopicRule(
                        topic_number=idx,
                        topic_name=topic_title,
                        category=category,
                        requirements=pre_sentence,
                        agreement_parameters=params,
                        post_sentence_rules=post_sentence,
                        prohibitions=prohibitions,
                        mandatory_clauses=[],
                        rules=topic_logic_rules
                    ))


        return CompiledCorporatePolicy(
            policy_name=policy_name,
            company_name=company_name,
            version=version,
            file_hash_sha256=file_hash,
            total_topics=len(topics),
            general_rules=general_rules,
            topics=topics,
            all_rules=all_rules
        )

    @classmethod
    def _extract_bullet_points(cls, text: str, section_regex: str) -> List[str]:
        match = re.search(section_regex, text, re.DOTALL | re.IGNORECASE)
        if not match:
            return []
        
        section_text = match.group(1).strip()
        # Divide por marcadores (>, -, •, *, ou novas linhas significativas)
        items = []
        for line in section_text.split("\n"):
            cleaned = re.sub(r'^[>\-•*§\d\.)\s]+', '', line).strip()
            if len(cleaned) > 5 and not cleaned.lower().startswith("informações internas"):
                items.append(cleaned)
        return items

    @classmethod
    def _build_topic_logic(
        cls,
        topic_num: int,
        topic_name: str,
        requirements: List[str],
        parameters: List[str],
        prohibitions: List[str]
    ) -> List[Dict[str, Any]]:
        """
        Converte os requisitos e vedações extraídos do tema em regras JSON-Logic.
        """
        rules = []

        # 1. Regra de Limite de Alto Custo (ex: procedimentos acima de R$ 100.000,00)
        high_cost_matches = re.findall(r'(?:superior\s+a|acima\s+de)\s+R\$\s*([\d.,]+)', " ".join(requirements + prohibitions), re.IGNORECASE)
        if high_cost_matches:
            from src.validators.brazilian_validators import BrazilianDomainValidator
            for hm in high_cost_matches:
                p_val = BrazilianDomainValidator.parse_brazilian_currency(hm)
                if p_val and p_val >= 50000.0:
                    rules.append({
                        "rule_code": f"TEMA_{topic_num:02d}_ALTO_CUSTO_MAXIMO",
                        "title": f"Teto de Alto Custo ({topic_name})",
                        "mandatory": True,
                        "condition": {"<=": [{"var": "financial.requested_amount"}, p_val]},
                        "required_evidence_fields": ["financial"],
                        "failure_message_template": f"Custo do procedimento excede o teto de alto custo de R$ {p_val:,.2f} sem prévia autorização."
                    })
                    break

        # 2. Regras de Evidências Específicas baseadas no texto dos requisitos
        reqs_lower = " ".join(requirements).lower()
        
        if any(k in reqs_lower for k in ["nota fiscal", "recibo", "desembolso", "comprovante de pagamento", "comprovante de despesa"]):
            rules.append({
                "rule_code": f"TEMA_{topic_num:02d}_EXIGE_DESEMBOLSO",
                "title": f"Comprovação de Desembolso / Nota Fiscal ({topic_name})",
                "mandatory": True,
                "condition": {"==": [{"var": "financial.has_fiscal_receipt"}, True]},
                "required_evidence_fields": ["financial"],
                "failure_message_template": f"Ausência de comprovação de desembolso financeiro (Nota Fiscal / Recibo) para {topic_name}."
            })

        if any(k in reqs_lower for k in ["laudo médico", "relatório médico", "prescrição médica", "indicação médica"]):
            rules.append({
                "rule_code": f"TEMA_{topic_num:02d}_EXIGE_LAUDO_MEDICO",
                "title": f"Laudo / Relatório Médico ({topic_name})",
                "mandatory": True,
                "condition": {"==": [{"var": "treatment.has_medical_report"}, True]},
                "required_evidence_fields": ["treatment"],
                "failure_message_template": f"Ausência de relatório ou laudo médico circunstanciado para {topic_name}."
            })

        if any(k in reqs_lower for k in ["negativa", "recusa prévia", "indeferimento administrativo", "protocolo"]):
            rules.append({
                "rule_code": f"TEMA_{topic_num:02d}_EXIGE_NEGATIVA",
                "title": f"Comprovação de Negativa Prévia ({topic_name})",
                "mandatory": True,
                "condition": {"==": [{"var": "administrative_denial.has_administrative_denial"}, True]},
                "required_evidence_fields": ["administrative_denial"],
                "failure_message_template": f"Ausência de comprovante de recusa prévia da operadora para {topic_name}."
            })

        # 3. Regra de Vedações Expressas do Tema
        if prohibitions:
            rules.append({
                "rule_code": f"TEMA_{topic_num:02d}_VEDACOES_EXPRESSAS",
                "title": f"Ausência de Hipóteses Vedadas ({topic_name})",
                "mandatory": True,
                "condition": {"==": [{"var": f"topics.topic_{topic_num:02d}.has_prohibition"}, False]},
                "required_evidence_fields": [f"topics.topic_{topic_num:02d}"],
                "failure_message_template": f"Processo incide em hipótese expressamente vedada pelo manual: {'; '.join(prohibitions[:2])}."
            })

        # 4. Regra de Requisitos Positivos Gerais do Tema
        rules.append({
            "rule_code": f"TEMA_{topic_num:02d}_REQUISITOS_CONFORMIDADE",
            "title": f"Cumprimento dos Requisitos ({topic_name})",
            "mandatory": True,
            "condition": {"==": [{"var": f"topics.topic_{topic_num:02d}.requirements_met"}, True]},
            "required_evidence_fields": [f"topics.topic_{topic_num:02d}"],
            "failure_message_template": f"Não atendimento aos requisitos obrigatórios do tema {topic_name}."
        })

        return rules
