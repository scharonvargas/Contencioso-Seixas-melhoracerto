from fastapi import APIRouter, HTTPException
from typing import List, Optional
from pydantic import BaseModel

router = APIRouter(prefix="/hitl", tags=["Human in the Loop"])

class HITLReviewItem(BaseModel):
    review_id: str
    process_id: str
    cnj_number: str
    reason: str # LOW_OCR_CONFIDENCE, MISSING_EVIDENCE, CONFLICTING_FACTS
    status: str # OPEN, RESOLVED
    created_at: str

class OperatorResolutionPayload(BaseModel):
    decision: str # APPROVED_AGREEMENT, REJECTED_AGREEMENT
    operator_notes: str

_HITL_QUEUE = [
    {
        "review_id": "rev_001",
        "process_id": "proc_1001",
        "cnj_number": "0001234-56.2025.8.26.0100",
        "reason": "MISSING_EVIDENCE (Nota Fiscal não localizada com confiança > 85%)",
        "status": "OPEN",
        "created_at": "2026-08-22T20:00:00Z"
    }
]

@router.get("/queue", response_model=List[HITLReviewItem])
async def list_hitl_queue():
    """Lista a fila prioritária de processos que exigem revisão humana."""
    return [r for r in _HITL_QUEUE if r["status"] == "OPEN"]

@router.post("/{review_id}/resolve")
async def resolve_hitl_item(review_id: str, payload: OperatorResolutionPayload):
    """Registra a intervenção e decisão humana definitiva."""
    item = next((r for r in _HITL_QUEUE if r["review_id"] == review_id), None)
    if not item:
        raise HTTPException(status_code=404, detail="Item de revisão não encontrado.")

    item["status"] = "RESOLVED"
    item["operator_decision"] = payload.decision
    item["operator_notes"] = payload.operator_notes

    return {"status": "success", "message": "Revisão resolvida com sucesso."}
