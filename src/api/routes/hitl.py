"""
src/api/routes/hitl.py
Rotas REST para gestão da fila Human-in-the-Loop (HITL) persistida no banco de dados.
"""

from fastapi import APIRouter, HTTPException, Depends
from typing import List, Optional
from pydantic import BaseModel
from sqlalchemy.sql import func
from src.core.database import SessionLocal
from src.models.entities import HumanReview, Process, Evaluation, AuditLog, generate_uuid

router = APIRouter(prefix="/hitl", tags=["Human in the Loop"])

class HITLReviewItem(BaseModel):
    review_id: str
    process_id: str
    cnj_number: str
    reason: str
    status: str
    created_at: str

class OperatorResolutionPayload(BaseModel):
    decision: str  # APPROVED_AGREEMENT, REJECTED_AGREEMENT
    operator_notes: str

@router.get("/queue", response_model=List[HITLReviewItem])
async def list_hitl_queue(tenant_id: Optional[str] = None):
    """
    Lista a fila prioritária de processos reais que exigem revisão humana persistida no banco.
    """
    db = SessionLocal()
    try:
        query = db.query(HumanReview, Process).join(Process, HumanReview.process_id == Process.id)
        if tenant_id:
            query = query.filter(HumanReview.tenant_id == tenant_id)
        
        open_reviews = query.filter(HumanReview.status == "OPEN").order_by(HumanReview.created_at.desc()).all()
        
        results = []
        for review, proc in open_reviews:
            created_str = review.created_at.isoformat() if review.created_at else "2026-08-24T00:00:00Z"
            results.append(HITLReviewItem(
                review_id=review.id,
                process_id=proc.id,
                cnj_number=proc.cnj_number,
                reason=review.review_reason,
                status=review.status,
                created_at=created_str
            ))
        return results
    finally:
        db.close()

@router.post("/{review_id}/resolve")
async def resolve_hitl_item(review_id: str, payload: OperatorResolutionPayload):
    """
    Registra a intervenção e decisão humana definitiva com trilha de auditoria forense.
    """
    db = SessionLocal()
    try:
        review = db.query(HumanReview).filter(
            (HumanReview.id == review_id) | (HumanReview.process_id == review_id)
        ).first()

        if not review:
            raise HTTPException(status_code=404, detail="Item de revisão não encontrado.")

        review.status = "RESOLVED"
        review.operator_decision = payload.decision
        review.operator_notes = payload.operator_notes
        review.resolved_at = func.now()

        # Atualiza status do processo
        proc = db.query(Process).filter(Process.id == review.process_id).first()
        if proc:
            proc.status = "HUMAN_RESOLVED"

        # Registra no log de auditoria
        audit = AuditLog(
            id=generate_uuid(),
            tenant_id=review.tenant_id,
            event_type="HITL_RESOLUTION",
            entity_name="HumanReview",
            entity_id=review.id,
            payload={
                "decision": payload.decision,
                "operator_notes": payload.operator_notes,
                "process_id": review.process_id
            }
        )
        db.add(audit)
        db.commit()

        return {
            "status": "success",
            "message": "Revisão resolvida com sucesso e auditada.",
            "review_id": review.id,
            "decision": payload.decision
        }
    finally:
        db.close()
