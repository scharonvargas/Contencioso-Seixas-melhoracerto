from enum import Enum
from typing import List, Dict, Any

class DocumentCategory(str, Enum):
    PETICAO_INICIAL = "PETICAO_INICIAL"
    NEGATIVA_OPERADORA = "NEGATIVA_OPERADORA"
    LAUDO_MEDICO = "LAUDO_MEDICO"
    RECEITA_MEDICA = "RECEITA_MEDICA"
    NOTA_FISCAL = "NOTA_FISCAL"
    RECIBO_PAGAMENTO = "RECIBO_PAGAMENTO"
    COMPROVANTE_BANCARIO = "COMPROVANTE_BANCARIO"
    CONTRATO_PLANO = "CONTRATO_PLANO"
    DECISAO_JUDICIAL = "DECISAO_JUDICIAL"
    PROCURACAO = "PROCURACAO"
    CERTIDAO = "CERTIDAO"
    OUTROS = "OUTROS"

# Mapeamento de documentos críticos para a decisão de acordo
RELEVANT_DOCUMENT_CATEGORIES = {
    DocumentCategory.PETICAO_INICIAL,
    DocumentCategory.NEGATIVA_OPERADORA,
    DocumentCategory.LAUDO_MEDICO,
    DocumentCategory.RECEITA_MEDICA,
    DocumentCategory.NOTA_FISCAL,
    DocumentCategory.RECIBO_PAGAMENTO,
    DocumentCategory.COMPROVANTE_BANCARIO,
    DocumentCategory.CONTRATO_PLANO
}

class DocumentSegmenter:
    """
    Segmenta um fluxo contínuo de páginas em sub-documentos e classifica cada um.
    """

    KEYWORDS_MAP = {
        DocumentCategory.PETICAO_INICIAL: ["excelentíssimo", "ação ordinária", "dos fatos", "dos pedidos", "vem à presença"],
        DocumentCategory.NEGATIVA_OPERADORA: ["negativa de cobertura", "solicitação não autorizada", "rol ans", "junta médica", "carta de indeferimento"],
        DocumentCategory.LAUDO_MEDICO: ["relatório médico", "laudo pericial", "atesto para os devidos fins", "cid-10", "quadro clínico"],
        DocumentCategory.NOTA_FISCAL: ["danfe", "nota fiscal de serviços", "tomador do serviço", "prestador", "valor total da nota"],
        DocumentCategory.RECIBO_PAGAMENTO: ["recibo de pagamento", "recebemos de", "a quantia de", "referente a consultas"],
        DocumentCategory.PROCURACAO: ["procuração ad judicia", "outorgante", "outorgado", "poderes da cláusula"],
        DocumentCategory.CERTIDAO: ["certidão de juntada", "certifico e dou fé", "publicação no diário"]
    }

    @classmethod
    def classify_page(cls, text: str) -> DocumentCategory:
        text_lower = text.lower()
        
        scores = {}
        for category, keywords in cls.KEYWORDS_MAP.items():
            matches = sum(1 for kw in keywords if kw in text_lower)
            if matches > 0:
                scores[category] = matches

        if not scores:
            return DocumentCategory.OUTROS

        best_category = max(scores, key=scores.get)
        return best_category

    @classmethod
    def segment_process_pages(cls, pages: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Agrupa páginas contínuas com o mesmo tipo ou detecta novas quebras.
        """
        segments = []
        if not pages:
            return segments

        current_category = cls.classify_page(pages[0].get("raw_text", ""))
        start_page = pages[0]["page_number"]
        current_pages = [pages[0]]

        for p in pages[1:]:
            page_cat = cls.classify_page(p.get("raw_text", ""))
            
            # Se a categoria mudou e não é genérica (OUTROS)
            if page_cat != current_category and page_cat != DocumentCategory.OUTROS:
                segments.append({
                    "category": current_category.value,
                    "start_page": start_page,
                    "end_page": current_pages[-1]["page_number"],
                    "is_relevant": current_category in RELEVANT_DOCUMENT_CATEGORIES,
                    "pages": current_pages
                })
                current_category = page_cat
                start_page = p["page_number"]
                current_pages = [p]
            else:
                current_pages.append(p)

        # Adiciona o último segmento
        segments.append({
            "category": current_category.value,
            "start_page": start_page,
            "end_page": current_pages[-1]["page_number"],
            "is_relevant": current_category in RELEVANT_DOCUMENT_CATEGORIES,
            "pages": current_pages
        })

        return segments
