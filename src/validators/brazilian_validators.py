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
