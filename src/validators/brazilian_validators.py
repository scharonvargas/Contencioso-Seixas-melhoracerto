import re
from typing import Optional

class BrazilianDomainValidator:
    """
    Validadores matemáticos e determinísticos para integridade de dados judiciais, de saúde e financeiros.
    """

    @staticmethod
    def validate_cpf(cpf: str) -> bool:
        cpf_clean = re.sub(r'\D', '', cpf)
        if len(cpf_clean) != 11 or cpf_clean == cpf_clean[0] * 11:
            return False
        
        for i in range(9, 11):
            val = sum((int(cpf_clean[num]) * ((i + 1) - num)) for num in range(0, i))
            digit = ((val * 10) % 11) % 10
            if int(cpf_clean[i]) != digit:
                return False
        return True

    @staticmethod
    def validate_cnpj(cnpj: str) -> bool:
        cnpj_clean = re.sub(r'\D', '', cnpj)
        if len(cnpj_clean) != 14 or cnpj_clean == cnpj_clean[0] * 14:
            return False
        
        m1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        m2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        d1 = sum(int(cnpj_clean[i]) * m1[i] for i in range(12)) % 11
        d1 = 0 if d1 < 2 else 11 - d1
        
        d2 = sum(int(cnpj_clean[i]) * m2[i] for i in range(13)) % 11
        d2 = 0 if d2 < 2 else 11 - d2
        
        return int(cnpj_clean[12]) == d1 and int(cnpj_clean[13]) == d2

    @staticmethod
    def validate_cnj_process_number(cnj: str) -> bool:
        clean_cnj = re.sub(r'\D', '', cnj)
        if len(clean_cnj) != 20:
            return False
        
        num = clean_cnj[0:7]
        dig = clean_cnj[7:9]
        ano = clean_cnj[9:13]
        jtr = clean_cnj[13:16]
        orig = clean_cnj[16:20]
        
        calc_str = f"{num}{ano}{jtr}{orig}{dig}"
        return int(calc_str) % 97 == 1

    @staticmethod
    def parse_brazilian_currency(value_str: str) -> Optional[float]:
        if not value_str:
            return None
        clean_val = re.sub(r'[^\d,.-]', '', value_str)
        if not clean_val:
            return None
        
        if ',' in clean_val and '.' in clean_val:
            clean_val = clean_val.replace('.', '').replace(',', '.')
        elif ',' in clean_val:
            clean_val = clean_val.replace(',', '.')
            
        try:
            return round(float(clean_val), 2)
        except ValueError:
            return None

    @staticmethod
    def validate_cid10(cid: str) -> bool:
        if not cid:
            return False
        pattern = r'^[A-Z][0-9]{2}(\.[0-9]{1,2})?$'
        return bool(re.match(pattern, cid.strip().upper()))

    @staticmethod
    def normalize_text_for_matching(text: str) -> str:
        """Remove acentos, pontuação e converte para minúsculas."""
        if not text:
            return ""
        import unicodedata
        # Remove pontos entre dígitos antes da remoção geral de pontuação (ex: 9.656 -> 9656)
        text_clean_nums = re.sub(r'(?<=\d)\.(?=\d)', '', text)
        nfkd = unicodedata.normalize('NFKD', text_clean_nums)
        clean = "".join([c for c in nfkd if not unicodedata.combining(c)])
        clean = re.sub(r'[^\w\s]', ' ', clean.lower())
        return re.sub(r'\s+', ' ', clean).strip()

    @classmethod
    def match_clinical_urgency_expression(cls, text: str) -> dict:
        """
        Validador determinístico do léxico clínico e legal de urgência/emergência (IT-AMIL-04).
        Elimina falsos negativos para variações canônicas de UTI, risco de morte e base legal.
        """
        normalized = cls.normalize_text_for_matching(text)
        
        urgency_patterns = [
            # 1. UTI / Hospitalar
            r'internacao em uti',
            r'leito de uti',
            r'uti pediatrica',
            r'uti neonatal',
            r'leito de cti',
            r'necessidade e urgencia da internacao',
            r'internacao de urgencia',
            r'internacao em carater de urgencia',
            r'quadro clinico de internacao urgente',
            
            # 2. Risco Clínico
            r'risco de vida',
            r'risco de morte',
            r'risco iminente de morte',
            r'urgencia medica',
            r'emergencia medica',
            r'situacao de emergencia',
            r'situacao de urgencia',
            r'quadro clinico grave',
            r'quadro de emergencia',
            r'perigo de dano irreparavel',
            r'perigo de morte',
            r'urgencia e emergencia',
            r'emergencia e urgencia',
            
            # 3. Dispositivos Legais Canônicos
            r'art(?:igo)?\s*12\s*v\s*c\s*(?:da\s*)?lei\s*9656',
            r'art 12 v c da lei 9656',
            r'artigo 12 inciso v alinea c da lei 9656',
            r'art 35 c da lei 9656',
            r'art(?:igo)?\s*35\s*c\s*(?:da\s*)?lei\s*9656',
            r'sumula 597 do stj',
            r'carencia de 24 horas'
        ]

        matched_terms = []
        for pattern in urgency_patterns:
            if re.search(pattern, normalized):
                matched_terms.append(pattern)

        is_matched = len(matched_terms) > 0
        return {
            "is_urgent": is_matched,
            "matched_terms": matched_terms,
            "primary_evidence": matched_terms[0] if matched_terms else None
        }

    @classmethod
    def validate_tea_medical_evidence(cls, text: str) -> dict:
        """
        Validador de Laudo Médico em 2 Eixos para Terapias Especiais / TEA (IT-AMIL-01).
        Eixo 1: Documento Médico Idôneo (laudo, prescrição, receituário).
        Eixo 2: Método Terapêutico Reconhecido (ABA, Denver, PROMPT, PECS, etc.).
        """
        normalized = cls.normalize_text_for_matching(text)

        medical_doc_patterns = [
            r'laudo medico',
            r'relatorio medico',
            r'prescricao medica',
            r'receituario',
            r'solicitacao medica',
            r'atestado medico',
            r'declaracao medica',
            r'parecer medico',
            r'laudo neurologico',
            r'laudo psiquiatrico'
        ]

        tea_method_patterns = {
            "ABA": r'\baba\b|analise do comportamento aplicada|terapia aba',
            "DENVER": r'\bdenver\b|modelo precoce de denver',
            "PROMPT": r'\bprompt\b',
            "PECS": r'\bpecs\b|sistema de comunicacao por troca de figuras',
            "INTEGRACAO_SENSORIAL": r'integracao sensorial',
            "TERAPIA_OCUPACIONAL": r'terapia ocupacional',
            "PSICOTERAPIA_COMPORTAMENTAL": r'psicoterapia comportamental|terapia cognitivo comportamental',
            "FONOAUDIOLOGIA": r'fonoaudiologia|fonoaudiologica',
            "FISIOTERAPIA_NEUROFUNCIONAL": r'fisioterapia neurofuncional|fisioterapia motora',
            "MUSICOTERAPIA": r'musicoterapia'
        }

        detected_docs = [p for p in medical_doc_patterns if re.search(p, normalized)]
        detected_methods = [name for name, pattern in tea_method_patterns.items() if re.search(pattern, normalized)]

        has_medical_doc = len(detected_docs) > 0
        has_tea_method = len(detected_methods) > 0
        is_valid = has_medical_doc and has_tea_method

        return {
            "is_valid": is_valid,
            "has_medical_doc": has_medical_doc,
            "detected_docs": detected_docs,
            "has_tea_method": has_tea_method,
            "detected_methods": detected_methods
        }

    @staticmethod
    def calculate_judicial_settlement_saving(
        sentenced_amount: float,
        proposal_amount: float,
        operator_share: float = 1.0,
        appeal_risk_fee: float = 0.20
    ) -> dict:
        """
        Calcula a métrica de deságio e economia (Saving) na fase Pós-Sentença / Recursal.
        Avalia o passivo potencial da operadora considerando honorários recursais de sucumbência (padrão 20%).
        """
        if sentenced_amount <= 0:
            return {
                "eligible_desagio": False,
                "reason": "Valor condenatório inválido ou não informado."
            }

        effective_liability = sentenced_amount * operator_share
        potential_appeal_cost = effective_liability * (1.0 + appeal_risk_fee)
        
        desagio_pct = 1.0 - (proposal_amount / effective_liability) if effective_liability > 0 else 0.0
        proposal_ratio = proposal_amount / effective_liability if effective_liability > 0 else 1.0
        
        # Faixa autorizada de deságio: Proposta entre 70% e 85% do valor da condenação (Deságio de 15% a 30%)
        is_within_authorized_range = 0.70 <= proposal_ratio <= 0.85
        
        real_saving_against_sentence = effective_liability - proposal_amount
        real_saving_against_appeal_risk = potential_appeal_cost - proposal_amount

        return {
            "sentenced_amount_total": round(sentenced_amount, 2),
            "operator_share_percentage": operator_share,
            "effective_operator_liability": round(effective_liability, 2),
            "potential_appeal_cost": round(potential_appeal_cost, 2),
            "proposal_amount": round(proposal_amount, 2),
            "proposal_ratio_percentage": round(proposal_ratio * 100, 2),
            "desagio_percentage": round(desagio_pct * 100, 2),
            "is_within_authorized_range": is_within_authorized_range,
            "saving_vs_sentence": round(real_saving_against_sentence, 2),
            "saving_vs_appeal_risk": round(real_saving_against_appeal_risk, 2)
        }

    @classmethod
    def extract_moral_damage_from_text(cls, text: str, requested_amount: float = 0.0) -> float:
        """
        Extrator determinístico forense para pedidos de Indenização por Danos Morais em peças processuais brasileiras.
        Reconhece montantes numéricos, valores por extenso intercalados, sugestões de arbitramento e pedidos finais.
        """
        if not text:
            return 0.0

        clean_text = re.sub(r'[ \t]+', ' ', text)
        
        patterns = [
            # 1. Danos morais ... R$ XX.XXX,XX ou R$ [Extenso] (R$ XX.XXX,XX)
            r'(?:danos?\s+mora(?:l|is)|repara[çc][aã]o\s+mora(?:l|is)|indeniza[çc][aã]o\s+mora(?:l|is))(?:[^\n\.\;]{1,150}?)R\$\s*(?:[a-zA-ZÀ-ÿ\s]+\s*\(\s*R\$\s*)?([\d.,]+)',
            # 2. R$ XX.XXX,XX ... a título de danos morais
            r'R\$\s*(?:[a-zA-ZÀ-ÿ\s]+\s*\(\s*R\$\s*)?([\d.,]+)(?:[^\n\.\;]{1,100}?)(?:a\s+t[ií]tulo\s+de\s+danos?\s+mora(?:l|is)|por\s+danos?\s+mora(?:l|is)|de\s+danos?\s+mora(?:l|is)|a\s+t[ií]tulo\s+indenizat[oó]rio)',
            # 3. Indenização ... sugerindo-se ... R$ XX.XXX,XX
            r'(?:indeniza[çc][aã]o|condena[çc][aã]o|repara[çc][aã]o)(?:[^\n\.\;]{1,100}?)(?:danos?\s+mora(?:l|is))(?:[^\n\.\;]{1,100}?)R\$\s*(?:[a-zA-ZÀ-ÿ\s]+\s*\(\s*R\$\s*)?([\d.,]+)',
            # 4. Valor de R$ XX.XXX,XX ... danos morais
            r'(?:valor\s+de|quantia\s+de|montante\s+de|patamar\s+de|importe\s+de)\s*R\$\s*(?:[a-zA-ZÀ-ÿ\s]+\s*\(\s*R\$\s*)?([\d.,]+)(?:[^\n\.\;]{1,100}?)(?:danos?\s+mora(?:l|is)|de\s+dano\s+mora(?:l|is))',
            # 5. Sugerindo-se o valor de ... (R$ XX.XXX,XX)
            r'sugerindo-se\s+(?:assim\s+)?(?:o\s+valor\s+de\s+)?R\$\s*(?:[a-zA-ZÀ-ÿ\s]+\s*\(\s*R\$\s*)?([\d.,]+)'
        ]
        
        amounts_found = []
        for pat in patterns:
            matches = re.findall(pat, clean_text, re.IGNORECASE)
            for m in matches:
                parsed = cls.parse_brazilian_currency(m)
                if parsed and parsed > 0:
                    amounts_found.append(parsed)
                    
        if amounts_found:
            return max(amounts_found)
        
        # Se na petição há pedido explícito de danos morais mas sem valor destacado em linha única,
        # e a ação é puramente cominatória / tutela de urgência sem recibo de desembolso material,
        # o valor total da causa representa a pretensão indenizatória
        if any(k in clean_text.lower() for k in ["danos morais", "dano moral", "indenização por danos morais", "reparação por danos morais"]):
            if requested_amount > 0 and not any(k in clean_text.lower() for k in ["nota fiscal", "danfe", "recibo de pagamento"]):
                return requested_amount
                
        return 0.0

    @classmethod
    def score_topic_affinity(cls, norm_full_text: str, topic_dict: dict) -> int:
        """
        Calcula pontuação semântica e léxica de afinidade entre o processo judicial
        e um tópico específico da norma ativa, cobrindo todos os temas corporativos de saúde e contratos.
        """
        if not norm_full_text or not topic_dict:
            return 0

        t_num = topic_dict.get("topic_number", 0)
        t_name = topic_dict.get("topic_name", "")
        norm_t_name = cls.normalize_text_for_matching(t_name)
        reqs = topic_dict.get("requirements", [])
        prohibs = topic_dict.get("prohibitions", [])
        norm_reqs = " ".join([cls.normalize_text_for_matching(r) for r in reqs + prohibs])

        score = 0

        # Mapeamento canônico abrangente de temas
        # 1. Terapias Especiais / TEA / ABA
        if any(k in norm_t_name for k in ["terapia", "especia", "aba", "tea", "autis"]):
            if re.search(r'\b(?:aba|denver|prompt|pecs|espectro autista|autismo|f84|terapia especial|acompanhamento terapeutico|integracao sensorial|terapia ocupacional|psicomotricidade|neuropsicopedagogia)\b', norm_full_text):
                score += 450

        # 2. Home Care / Internação Domiciliar
        if any(k in norm_t_name for k in ["home care", "domiciliar", "cuidador", "pad"]):
            if re.search(r'\b(?:home care|internacao domiciliar|atendimento domiciliar|pad|plano de atencao domiciliar|cuidador domiciliar|assistencia domiciliar|oxigenoterapia domiciliar)\b', norm_full_text):
                score += 450

        # 3. Medicamentos / Fármacos / Antineoplásicos
        if any(k in norm_t_name for k in ["medicament", "farmaco", "antineoplas", "droga", "anvisa"]):
            if re.search(r'\b(?:antineoplasico|farmaco|medicamento importado|anvisa|fora dut|fora rol|alto custo|quimioterapico|dupilumabe|pembrolizumabe|off label|medicamento|fornecimento de medicamento)\b', norm_full_text):
                score += 400

        # 4. Tratamento em Prestador Particular / Reembolso
        if any(k in norm_t_name for k in ["reembolso", "prestador particular", "desembolso", "restitui"]):
            if re.search(r'\b(?:reembolso de despesas|reembolso de consulta|reembolso de cirurgia|reembolso de honorarios|reembolso medico|reembolso hospitalar|tabela de reembolso|restituicao de despesas|pedido de reembolso)\b', norm_full_text):
                score += 450
            elif "reembolso" in norm_full_text and not re.search(r'\b(?:boleto falso|golpe do boleto|fraude de boleto|boleto adulterado)\b', norm_full_text):
                score += 250

        # 5. Carência / Urgência em Carência
        if any(k in norm_t_name for k in ["carencia"]):
            if re.search(r'\b(?:carencia|prazo de carencia|carencia de 24 horas|cumprimento de carencia|periodo de carencia)\b', norm_full_text):
                score += 350

        # 6. Procedimentos Cirúrgicos Eletivos / Rol / DUT / ADI 7265
        if any(k in norm_t_name for k in ["cirurg", "eletiv", "rol", "dut", "adi 7265"]):
            if re.search(r'\b(?:cirurgia eletiva|procedimento cirurgico|adi 7265|rol ans|dut ans|negativa de cirurgia|cobertura cirurgica|cirurgia bariatrica|gastroplastia|procedimento eletivo)\b', norm_full_text):
                score += 400

        # 7. Próteses, Órteses e Materiais Especiais (OPME)
        if any(k in norm_t_name for k in ["opme", "protese", "ortese", "material", "materiais"]):
            if re.search(r'\b(?:opme|protese|ortese|material especial|material cirurgico|stent|parafuso pedicular|tela cirurgica|fornecedor homologado)\b', norm_full_text):
                score += 450

        # 8. Exames de Alta Complexidade / PET-SCAN / TAVI
        if any(k in norm_t_name for k in ["exame", "pet", "tavi", "alta complexidade", "genetico"]):
            if re.search(r'\b(?:pet-scan|pet scan|pet ct|tavi|exame genetico|ressonancia magnetica|tomografia computadorizada|foundation one|exame de alta complexidade)\b', norm_full_text):
                score += 450

        # 9. Indisponibilidade de Rede Credenciada
        if any(k in norm_t_name for k in ["indisponibilidade", "rede", "prestador"]):
            if re.search(r'\b(?:indisponibilidade de rede|falta de vaga|ausencia de prestador|ausencia de rede credenciada|rede insuficiente|inexistencia de prestador credenciado|sem rede no municipio)\b', norm_full_text):
                score += 450

        # 10. Reajustes Anuais / Sinistralidade / Coletivos
        if any(k in norm_t_name for k in ["reajuste", "sinistralidade", "aumento", "vpmh", "anual"]):
            if re.search(r'\b(?:reajuste anual|sinistralidade|reajuste por sinistralidade|aumento abusivo|indice ans|reajuste coletivo|vpmh)\b', norm_full_text):
                score += 400

        # 11. Procedimentos Especiais (Lente / Órtese Craniana / Bomba de Insulina)
        if any(k in norm_t_name for k in ["lente", "calota", "craniana", "bomba", "insulina", "especia", "peniana"]):
            if re.search(r'\b(?:lente intraocular|ortese craniana|calota craniana|capacetinho|bomba de insulina|tema 1316 stj|protese peniana|plagiocefalia)\b', norm_full_text):
                score += 450

        # 12. Reajuste Faixa Etária e Parecer Atuarial
        if any(k in norm_t_name for k in ["faixa etaria", "etaria", "atuarial", "idade", "59 anos"]):
            if re.search(r'\b(?:reajuste por faixa etaria|reajuste de faixa etaria|reajuste 59 anos|reajuste aos 59|mudanca de faixa etaria|parecer atuarial|reajuste etario)\b', norm_full_text):
                score += 450

        # 13. Contratos PME porte 1 / Empresarial
        if any(k in norm_t_name for k in ["pme", "porte 1", "pequena empresa", "empresarial", "corporativo"]):
            if re.search(r'\b(?:pme porte 1|plano pme|contrato empresarial|plano corporativo|plano coletivo empresarial|pequena e media empresa|contrato pme)\b', norm_full_text):
                score += 400

        # 14. Cancelamento por Inadimplência / Falha Notificação Prévia
        if any(k in norm_t_name for k in ["cancelamento", "notificacao", "inadimplencia"]):
            if re.search(r'\b(?:cancelamento por inadimplencia|falha na notificacao previa|falta de notificacao|notificacao previa|rescisao por inadimplemento|cancelamento indevido|sem notificacao previa)\b', norm_full_text):
                score += 400

        # 15. Cancelamento a Pedido da Operadora / Rescisão Unilateral
        if any(k in norm_t_name for k in ["rescisao", "unilateral", "a pedido da operadora", "imotivada"]):
            if re.search(r'\b(?:rescisao unilateral|cancelamento a pedido da operadora|denuncia unilateral|rescisao imotivada|cancelamento unilateral)\b', norm_full_text):
                score += 400

        # 16. Reativação Contratual / Regularização CNPJ / Movimentação Cadastral
        if any(k in norm_t_name for k in ["reativacao", "cnpj", "movimentacao", "cadastro", "dependente", "inclusao", "regularizacao"]):
            if re.search(r'\b(?:reativacao contratual|reativacao do plano|baixa do cnpj|cnpj baixado|cnpj inapto|inaptidao do cnpj|movimentacao cadastral|inclusao de dependente|exclusao de dependente|inclusao de beneficiario)\b', norm_full_text):
                score += 450

        # 17. Fraude de Boleto / Boleto Falso
        if any(k in norm_t_name for k in ["fraude", "boleto", "golpe"]):
            if re.search(r'\b(?:boleto falso|golpe do boleto|fraude de boleto|fatura falsa|boleto adulterado|boleto fraudado|estelionatario|golpista)\b', norm_full_text):
                score += 650

        # 18. Troca de Titularidade / Migração para Plano Individual
        if any(k in norm_t_name for k in ["titularidade", "individual", "migracao"]):
            if re.search(r'\b(?:troca de titularidade|migracao para plano individual|manutencao de plano individual|plano individual|transferencia de titularidade)\b', norm_full_text):
                score += 400

        # 19. Manutenção de Beneficiário Demitido/Aposentado (Art. 30/31 Lei 9656)
        if any(k in norm_t_name for k in ["demitido", "aposentado", "artigo 30", "artigo 31", "art 30", "art 31"]):
            if re.search(r'\b(?:beneficiario demitido|beneficiario aposentado|artigo 30|artigo 31|art 30 da lei 9656|art 31 da lei 9656|manutencao de plano demitido|manutencao de plano aposentado|demissao sem justa causa)\b', norm_full_text):
                score += 450

        # 20. Danos Morais Exclusivos / Negativação Indevida
        if any(k in norm_t_name for k in ["danos morais", "dano moral", "indenizacao", "negativacao"]):
            if re.search(r'\b(?:negativacao indevida|inscricao indevida|spc|serasa|exclusivo dano moral|acao de indenizacao por danos morais|dano moral puro)\b', norm_full_text):
                score += 400

        # 21. Cobrança de Mensalidades em Aberto
        if any(k in norm_t_name for k in ["cobranca", "mensalidade", "debito"]):
            if re.search(r'\b(?:cobranca de mensalidade|mensalidades em aberto|cobranca indevida de mensalidade|faturas em aberto|execucao de mensalidades|acao de cobranca)\b', norm_full_text):
                score += 400

        # 22. Cruzamento genérico com palavras-chave presentes no próprio título e requisitos do tema na norma
        topic_keywords = [w for w in norm_t_name.split() if len(w) >= 4 and w not in ["para", "com", "dos", "das", "tema", "acordo", "sobre", "pelo", "pela"]]
        for kw in topic_keywords:
            if kw in norm_full_text:
                score += 50

        return score

