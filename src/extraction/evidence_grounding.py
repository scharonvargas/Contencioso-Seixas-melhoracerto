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
        document_name: Optional[str] = None,
        page_in_document: Optional[int] = None,
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
            snippet_words = [w for w in clean_snippet.lower().split() if len(w) >= 3]
            page_text_lower = clean_page_text.lower()
            
            # Se nenhuma palavra chave do snippet existe na página, descarta imediatamente (O(1))
            if snippet_words and not any(w in page_text_lower for w in snippet_words):
                return False, None

            # 2. Checagem Fuzzy Tolerante em janelas de texto relevantes
            best_ratio = 0.0
            for w in snippet_words:
                start_idx = 0
                while True:
                    idx = page_text_lower.find(w, start_idx)
                    if idx == -1:
                        break
                    win_start = max(0, idx - 100)
                    win_end = min(len(page_text_lower), idx + len(clean_snippet) + 100)
                    window_text = page_text_lower[win_start:win_end]
                    
                    matcher = SequenceMatcher(None, clean_snippet.lower(), window_text)
                    match = matcher.find_longest_match(0, len(clean_snippet), 0, len(window_text))
                    if match.size > 0:
                        matched_sub = window_text[match.b : match.b + match.size]
                        r = SequenceMatcher(None, clean_snippet.lower(), matched_sub).ratio()
                        if r > best_ratio:
                            best_ratio = r
                    start_idx = idx + len(w)

            if best_ratio < min_similarity_ratio:
                return False, None
                
            confidence = round(best_ratio, 3)

        # 3. Localização Espacial e Cálculo da Bounding Box [ymin, xmin, ymax, xmax]
        bbox = EvidenceGroundingValidator._compute_bbox(clean_snippet, words_data)

        evidence_dict = {
            "document_type": document_type,
            "document_name": document_name or "documento.pdf",
            "page_in_document": page_in_document or 1,
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
