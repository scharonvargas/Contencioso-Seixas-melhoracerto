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
            for idx, p in enumerate(paragraphs):
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

CANONICAL_TOPIC_NAMES = {
    1: 'Terapias Especiais (TEA / ABA)',
    2: 'Home Care (Internação Domiciliar)',
    3: 'Medicamento (Antineoplásico / Fora Rol)',
    4: 'Carência (Urgência e Emergência)',
    5: 'Rol de Procedimentos e DUT (ADI 7265)',
    6: 'Atraso na Autorização',
    7: 'Pool de Cobertura (PET-SCAN / OPME / TAVI)',
    8: 'Rede de Atendimento (Indisponibilidade)',
    9: 'Internação Psiquiátrica',
    10: 'OPME e Junta Médica (Bomba de Insulina / Órtese)',
    11: 'Reajuste (Faixa Etária / Sinistralidade)',
    12: 'Cancelamento PME e Empresarial (Aviso Prévio / Multa)',
    13: 'Demais Cancelamentos (Inadimplência / Falha Notificação)',
    14: 'Rescisão Unilateral de Planos Coletivos Por Adesão',
    15: 'Cancelamento de Contrato Por Baixa do CNPJ',
    16: 'Movimentação Cadastral (Inclusão / Exclusão de Beneficiário)',
    17: 'Fraude de Boleto (Boleto Falso)',
    18: 'Reembolso (Prestador Particular)',
    19: 'Negativação do Nome (Sustação de Protesto / Dano Moral)',
    20: 'Documentos Obrigatórios (Exibição de Documentos)',
    21: 'Mensalidade (Cobrança e Reprocessamento de Faturas)'
}

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
            txt = p.get_text("text")
            if not txt or len(txt.strip()) == 0:
                # Fallback para OCR caso a política seja digitalizada/escaneada
                from src.ocr.cascade_engine import OCRCascadeEngine
                ocr = OCRCascadeEngine()
                res = ocr.process_page(p, page_number=p.number + 1)
                txt = res.get("raw_text", "")
            pages_text.append(txt)
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
            general_rules = cls._extract_clean_items(cleaned_text, r'Regras Gerais(?:[\s\w-]+)?:\s*', r'(?:Atributos|Regras especiais|Rotinas|$)')

        topics: List[DynamicTopicRule] = []
        all_rules: List[Dict[str, Any]] = []

        # 1. ESTRATÉGIA PRIMÁRIA: Tópicos Numerados Estruturados (1 a 21)
        # Suporta formatos com '1. Terapias Especiais:', '10. OPME e Junta Médica', '1.\nRequisitos:', etc.
        anchor_pattern = re.compile(
            r'(?:^|\n)\s*(\d{1,2})\.\s*(?:([^\n]{2,120}))?',
            re.MULTILINE
        )
        matches = list(anchor_pattern.finditer(cleaned_text))
        valid_anchors = []
        seen_numbers = set()

        for m in matches:
            num = int(m.group(1))
            if 1 <= num <= 21 and num not in seen_numbers:
                raw_title = (m.group(2) or "").strip()
                # Descarta numerações de metadados / rodapés
                if any(k in raw_title.lower() for k in [
                    'data da elaboração', 'última revisão', 'elaboração:', 'revisores:', 
                    'área responsável', 'todas os casos elegíveis'
                ]):
                    continue
                seen_numbers.add(num)
                valid_anchors.append({
                    'number': num,
                    'raw_title': raw_title,
                    'start': m.start(),
                    'end': m.end()
                })

        valid_anchors.sort(key=lambda x: x['start'])

        if len(valid_anchors) >= 2:
            for i, a in enumerate(valid_anchors):
                topic_num = a['number']
                raw_t = a['raw_title']
                start_pos = a['start']

                if i + 1 < len(valid_anchors):
                    end_pos = valid_anchors[i + 1]['start']
                else:
                    end_pos = len(cleaned_text)

                section = cleaned_text[start_pos:end_pos].strip()

                # Limpa e sanitiza o título do tema
                clean_title = re.sub(r'[:\s]+$', '', raw_t).strip()
                if not clean_title or len(clean_title) < 3 or clean_title.lower().startswith('requisitos') or clean_title.lower().startswith('parâmetros') or len(clean_title.split()) > 10:
                    topic_title = CANONICAL_TOPIC_NAMES.get(topic_num, f"Tema {topic_num}")
                else:
                    topic_title = clean_title

                is_non_assistential = any(
                    k in (section + " " + topic_title).lower()
                    for k in ["reajuste", "cancelamento", "movimentação", "inativo", "boleto", "fraude", "protesto", "mensalidade", "cadastro", "documento", "rescisão", "sustação", "pme"]
                )
                category = "NÃO ASSISTENCIAL" if is_non_assistential else "ASSISTENCIAL"

                stop_reqs = r'(?:Par[aâ]metros\s+do\s+Acordo|Acordos\s+P[oó]s|N[aã]o\s+permitid[oa]|Exce[çc][oõ]es|N[aã]o\s+faremos|CL[AÁ]USULA|P[oó]s\s+senten[çc]a|OBS|Atributos|$)'
                pre_sentence = cls._extract_clean_items(
                    section,
                    r'(?:Requisitos|Faremos\s+acordos?|Acordos\s+pr[eé][\s-]*(?:senten[çc]a|condena[çc][aão-z]+))[^:\n]*:\s*',
                    stop_reqs
                )

                params = cls._extract_clean_items(
                    section,
                    r'Par[aâ]metros\s+do\s+Acordo[^:\n]*:\s*',
                    r'(?:Acordos\s+P[oó]s|P[oó]s\s+senten[çc]a|N[aã]o\s+permitid[oa]|Exce[çc][oõ]es|N[aã]o\s+faremos|CL[AÁ]USULA|OBS|Atributos|$)'
                )

                post_sentence = cls._extract_clean_items(
                    section,
                    r'(?:Acordos\s+P[oó]s[\s-]*(?:senten[çc]a|condena[çc][aão-z]+|ac[oó]rd[aã]o|inst[aâ]ncia[s]?)?|P[oó]s[\s-]*(?:senten[çc]a|condena[çc][aão-z]+))[^:\n]*:\s*',
                    r'(?:N[aã]o\s+permitid[oa]|Exce[çc][oõ]es|N[aã]o\s+faremos|CL[AÁ]USULA|Par[aâ]metros|OBS|Atributos|$)'
                )

                prohibitions = cls._extract_clean_items(
                    section,
                    r'(?:N[aã]o\s+permitid[oa]|Exce[çc][oõ]es|N[aã]o\s+faremos\s+acordo[s]?|N[aã]o\s+indicad[oa])[^:\n]*:\s*',
                    r'(?:Acordos\s+P[oó]s|Par[aâ]metros|Requisitos|CL[AÁ]USULA|OBS|Atributos|$)'
                )

                clauses = cls._extract_clean_items(
                    section,
                    r'CL[AÁ]USULA\s+OBRIGAT[OÓ]RIA[^:\n]*:\s*',
                    r'(?:Acordos\s+P[oó]s|Par[aâ]metros|Requisitos|N[aã]o\s+permitid[oa]|OBS|Atributos|$)'
                )

                # Detecta vedações inline
                if not prohibitions and re.search(r'N[aã]o\s+faremos\s+acordo\s+em\s+casos?\s+pr[eé]', section, re.IGNORECASE):
                    prohibitions.append("Não faremos acordo em casos pré-sentença.")

                inline_prohibs = re.findall(r'([^\n]+N[aã]o\s+fazemos\s+em\s+nenhuma\s+hip[oó]tese[^\n]+)', section, re.IGNORECASE)
                if inline_prohibs:
                    prohibitions.extend([ip.strip() for ip in inline_prohibs])

                for r_item in pre_sentence + post_sentence:
                    if re.search(r'n[aã]o\s+(?:fazer\s+acordo[s]?|cobrir|realizar\s+acordos?|fechar\s+acordo)|somente\s+com\s+senten[çc]a|vedad[ao]|sem\s+possibilidade\s+futura', r_item, re.IGNORECASE):
                        if r_item not in prohibitions:
                            prohibitions.append(r_item)

                combined_params = pre_sentence + params + post_sentence
                topic_logic_rules = cls._build_topic_logic(topic_num, topic_title, pre_sentence, combined_params, prohibitions)
                all_rules.extend(topic_logic_rules)

                topics.append(DynamicTopicRule(
                    topic_number=topic_num,
                    topic_name=topic_title,
                    category=category,
                    requirements=pre_sentence,
                    agreement_parameters=params,
                    post_sentence_rules=post_sentence,
                    prohibitions=prohibitions,
                    mandatory_clauses=clauses,
                    rules=topic_logic_rules
                ))

        # 2. ESTRATÉGIA SECUNDÁRIA: Marcadores com bullets (•)
        elif len(bullet_matches := list(re.finditer(r'(?:^|\n)\s*[•]\s*([^\n]+)', cleaned_text))) >= 3:
            for idx, m in enumerate(bullet_matches, 1):
                start_pos = m.start()
                end_pos = bullet_matches[idx].start() if idx < len(bullet_matches) else len(cleaned_text)
                raw_title = m.group(1).strip()
                clean_title = re.sub(r'\s*\(.*?\)$', '', raw_title).strip()
                topic_title = clean_title if (clean_title and len(clean_title) >= 2) else CANONICAL_TOPIC_NAMES.get(idx, f"Tema {idx}")
                section = cleaned_text[start_pos:end_pos].strip()

                is_non_assistential = any(
                    k in (section + " " + topic_title).lower()
                    for k in ["reajuste", "cancelamento", "movimentação", "inativo", "boleto", "fraude", "protesto", "mensalidade", "cadastro", "documento", "rescisão"]
                )
                category = "NÃO ASSISTENCIAL" if is_non_assistential else "ASSISTENCIAL"

                stop_headings = r'(?:Acordos\s+p[oó]s|Exce[çc][oõ]es|N[aã]o\s+faremos|N[aã]o\s+permitido|CL[AÁ]USULA|Obs:|$)'
                pre_sentence = cls._extract_clean_items(
                    section,
                    r'(?:Acordos\s+pr[eé][\s-]*(?:senten[çc]a|condena[çc][aão-z]+)|Requisitos|Faremos\s+acordos\s+nas\s+seguintes\s+hip[oó]teses):\s*',
                    stop_headings
                )
                
                prohibitions = cls._extract_clean_items(
                    section,
                    r'(?:Exce[çc][oõ]es|N[aã]o\s+faremos\s+acordos?|N[aã]o\s+faremos\s+acordo|N[aã]o\s+permitido|N[aã]o\s+indicado\s+para\s+acordo):\s*',
                    r'(?:Acordos\s+p[oó]s|Acordos\s+pr[eé]|CL[AÁ]USULA|Obs:|$)'
                )

                if not prohibitions and re.search(r'N[aã]o\s+faremos\s+acordo\s+em\s+casos?\s+pr[eé]', section, re.IGNORECASE):
                    prohibitions = ["Não faremos acordo em casos pré condenação."]

                inline_prohibs = re.findall(r'([^\n]+N[aã]o\s+fazemos\s+em\s+nenhuma\s+hip[oó]tese[^\n]+)', section, re.IGNORECASE)
                if inline_prohibs:
                    prohibitions.extend([ip.strip() for ip in inline_prohibs])

                for r_item in pre_sentence:
                    if re.search(r'n[aã]o\s+fazer\s+acordo|somente\s+com\s+senten[çc]a|vedad[ao]', r_item, re.IGNORECASE):
                        if r_item not in prohibitions:
                            prohibitions.append(r_item)

                post_sentence = cls._extract_clean_items(
                    section,
                    r'Acordos\s+p[oó]s[\s-]*(?:senten[çc]a|condena[çc][aão-z]+|inst[aâ]ncia[s]?)?(?:[\s\w-]+)?:\s*',
                    r'(?:Exce[çc][oõ]es|N[aã]o\s+faremos|CL[AÁ]USULA|Obs:|$)'
                )

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
    def _extract_clean_items(cls, text: str, start_pattern: str, stop_pattern: Optional[str] = None) -> List[str]:
        if stop_pattern:
            pattern = rf'{start_pattern}(.*?)(?={stop_pattern}|$)'
        else:
            pattern = rf'{start_pattern}(.*)'
        m = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
        if not m:
            return []
        raw = m.group(1).strip()
        lines = raw.split('\n')
        items = []
        curr = []
        bullet_regex = re.compile(r'^(?:(?:\d+[\.\)])|[•\-*§➤o\u27a4\u2022\u25b6\u25ba\u2794>])\s*')
        for line in lines:
            l = line.strip()
            if not l or l.lower().startswith("informações internas"):
                continue
            if bullet_regex.match(l):
                if curr:
                    items.append(" ".join(curr))
                curr = [bullet_regex.sub('', l).strip()]
            else:
                curr.append(l)
        if curr:
            items.append(" ".join(curr))
        return [it for it in items if len(it) > 3]

    @classmethod
    def _extract_bullet_points(cls, text: str, section_regex: str) -> List[str]:
        match = re.search(section_regex, text, re.DOTALL | re.IGNORECASE)
        if not match:
            return []
        
        section_text = match.group(1).strip()
        items = []
        bullet_regex = re.compile(r'^[>\-•*§➤o\u27a4\u2022\u25b6\u25ba\u2794\d\.\)\s]+')
        for line in section_text.split("\n"):
            cleaned = bullet_regex.sub('', line).strip()
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

        # 1. Regra de Limite Financeiro de Indenização / Dano Moral por Tema extraído dinamicamente do manual
        combined_text = " ".join(requirements + prohibitions + parameters)
        financial_ceiling_matches = re.findall(
            r'(?:pagamento\s+de\s+at[eé]|indeniza[çc][aã]o\s*(?:\(se\s+houver\s+negativa[çc][aã]o\))?\s*de\s+at[eé]|limite\s+de|teto\s+de|at[eé]\s+o\s+limite\s+de|danos?\s+morais?\s*(?:de\s+at[eé]|at[eé])?)\s*R\$\s*([\d.,]+)',
            combined_text,
            re.IGNORECASE
        )
        if financial_ceiling_matches:
            from src.validators.brazilian_validators import BrazilianDomainValidator
            for cm in financial_ceiling_matches:
                ceiling_val = BrazilianDomainValidator.parse_brazilian_currency(cm)
                if ceiling_val and ceiling_val > 0:
                    rules.append({
                        "rule_code": f"TEMA_{topic_num:02d}_TETO_DANO_MORAL",
                        "title": f"Teto de Indenização / Dano Moral ({topic_name})",
                        "mandatory": True,
                        "condition": {"<=": [{"var": "financial.moral_damage_amount"}, ceiling_val]},
                        "required_evidence_fields": ["financial"],
                        "failure_message_template": f"Pedido de indenização / dano moral excede o teto de R$ {ceiling_val:,.2f} estipulado na norma ativa para {topic_name}."
                    })
                    break

        # 1.1 Regra de Limite de Alto Custo (ex: procedimentos acima de R$ 50.000,00)
        high_cost_matches = re.findall(r'(?:superior\s+a|acima\s+de|ultrapassar\s+(?:o\s+montante\s+de)?)\s*(?:R\$\s*)?([\d.,]+)', combined_text, re.IGNORECASE)
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

        # 3. Regra de Vedações Expressas do Tema (Avaliação determinística da ausência de vedações)
        if prohibitions:
            rules.append({
                "rule_code": f"TEMA_{topic_num:02d}_VEDACOES_EXPRESSAS",
                "title": f"Ausência de Hipóteses Vedadas ({topic_name})",
                "mandatory": True,
                "condition": {"==": [{"var": f"topics.topic_{topic_num:02d}.has_prohibition"}, False]},
                "required_evidence_fields": [],
                "failure_message_template": f"Processo incide em hipótese expressamente vedada pelo manual: {'; '.join(prohibitions[:2])}."
            })

        # 4. Regra de Requisitos Positivos Gerais do Tema
        failure_req_desc = f": {'; '.join(requirements[:2])}" if requirements else ""
        rules.append({
            "rule_code": f"TEMA_{topic_num:02d}_REQUISITOS_CONFORMIDADE",
            "title": f"Cumprimento dos Requisitos ({topic_name})",
            "mandatory": True,
            "condition": {"==": [{"var": f"topics.topic_{topic_num:02d}.requirements_met"}, True]},
            "required_evidence_fields": [],
            "failure_message_template": f"Não atendimento aos requisitos obrigatórios do tema {topic_name}{failure_req_desc}."
        })

        return rules

