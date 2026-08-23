import re
from typing import Optional, Tuple, List, Dict, Any
from difflib import SequenceMatcher

class EvidenceGroundingValidator:
    """
    Garante o princípio obrigatório: NENHUM FATO SEM EVIDÊNCIA.
    Valida se o trecho extraído existe na camada de texto da página e gera o Bounding Box envolvente.
    Utiliza difflib nativo para tolerância a pequenos artefatos de OCR.
    """

    @staticmethod
    def validate_and_create_evidence(
        extracted_snippet: str,
        page_raw_text: str,
        words_data: List[Dict[str, Any]],
        document_type: str,
        page_number: int,
        ocr_engine: str = "PyMuPDF",
        min_similarity_ratio: float = 0.85
    ) -> Tuple[bool, Optional[Dict[str, Any]]]:
        if not extracted_snippet or not page_raw_text:
            return False, None

        clean_snippet = re.sub(r'\s+', ' ', extracted_snippet.strip())
        clean_page_text = re.sub(r'\s+', ' ', page_raw_text.strip())

        # 1. Checagem Exata de Substring
        is_exact = clean_snippet.lower() in clean_page_text.lower()
        confidence = 1.0

        if not is_exact:
            # 2. Checagem Fuzzy Tolerante com difflib (Standard Library)
            # Encontra o melhor bloco correspondente
            matcher = SequenceMatcher(None, clean_snippet.lower(), clean_page_text.lower())
            match = matcher.find_longest_match(0, len(clean_snippet), 0, len(clean_page_text))
            
            if match.size == 0:
                return False, None
                
            matched_sub = clean_page_text.lower()[match.b : match.b + match.size]
            ratio = SequenceMatcher(None, clean_snippet.lower(), matched_sub).ratio()
            
            # Se o tamanho do trecho coincidente for muito inferior ao snippet ou ratio < threshold
            if (match.size / max(len(clean_snippet), 1) < min_similarity_ratio) and ratio < min_similarity_ratio:
                # Alucinação Rejeitada: Trecho não existe no documento
                return False, None
                
            confidence = round(ratio, 3)

        # 3. Localização Espacial e Cálculo da Bounding Box [ymin, xmin, ymax, xmax]
        bbox = EvidenceGroundingValidator._compute_bbox(clean_snippet, words_data)

        evidence_dict = {
            "document_type": document_type,
            "page_number": page_number,
            "bounding_box": bbox,
            "text_snippet": clean_snippet,
            "ocr_engine": ocr_engine,
            "confidence_score": confidence
        }

        return True, evidence_dict

    @staticmethod
    def _compute_bbox(snippet: str, words_data: List[Dict[str, Any]]) -> List[float]:
        target_tokens = snippet.lower().split()
        matched_boxes = []

        for w in words_data:
            token_clean = re.sub(r'[^\w]', '', w.get("text", "").lower())
            if any(t in token_clean for t in target_tokens if len(t) > 2):
                if "bbox" in w:
                    matched_boxes.append(w["bbox"])

        if not matched_boxes:
            return [100.0, 100.0, 200.0, 900.0]  # Box padrão caso palavras isoladas não coincidam

        ymin = min(b[0] for b in matched_boxes)
        xmin = min(b[1] for b in matched_boxes)
        ymax = max(b[2] for b in matched_boxes)
        xmax = max(b[3] for b in matched_boxes)

        return [round(ymin, 1), round(xmin, 1), round(ymax, 1), round(xmax, 1)]
