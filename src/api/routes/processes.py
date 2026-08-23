"""
src/api/routes/processes.py
Rotas REST para upload, listagem e auditoria de Processos Judiciais.
"""

from fastapi import APIRouter, UploadFile, File, Form, HTTPException
from typing import List, Optional, Dict, Any
from pydantic import BaseModel
from src.core.database import SessionLocal
from src.models.entities import Process, Evaluation, PolicyVersion, DocumentPage, ExtractedFact, Evidence, Tenant, generate_uuid
from src.services.process_service import ProcessExecutionService

router = APIRouter(prefix="/processes", tags=["Processos Judiciais"])

class ProcessDetailResponse(BaseModel):
    process_id: str
    cnj_number: str
    beneficiary_name: str
    operator_name: str
    total_pages: int
    status: str
    verdict: Optional[str] = None
    summary: Optional[str] = None
    identified_theme: Optional[str] = None
    policy_version: Optional[str] = None
    rules: List[Dict[str, Any]] = []

@router.get("", response_model=List[ProcessDetailResponse])
@router.get("/", response_model=List[ProcessDetailResponse])
async def list_processes():
    """
    Lista todos os processos judiciais reais cadastrados e avaliados no banco de dados.
    """
    db = SessionLocal()
    try:
        processes = db.query(Process).order_by(Process.created_at.desc()).all()
        results = []
        for p in processes:
            eval_record = db.query(Evaluation).filter(Evaluation.process_id == p.id).first()
            p_ver = db.query(PolicyVersion).filter(PolicyVersion.id == eval_record.policy_version_id).first() if eval_record else None
            theme_fact = db.query(ExtractedFact).filter(ExtractedFact.process_id == p.id, ExtractedFact.fact_key == "identified_theme").first()
            identified_theme = theme_fact.normalized_value if theme_fact else None

            results.append(ProcessDetailResponse(
                process_id=p.id,
                cnj_number=p.cnj_number,
                beneficiary_name=p.beneficiary_name or "Beneficiário",
                operator_name=p.operator_name or "Operadora de Saúde",
                total_pages=p.total_pages,
                status=p.status,
                verdict=eval_record.overall_result if eval_record else "PENDING",
                summary=eval_record.decision_summary if eval_record else "Em processamento",
                identified_theme=identified_theme,
                policy_version=p_ver.version if p_ver else None,
                rules=eval_record.rules_results if eval_record and eval_record.rules_results else []
            ))
        return results
    finally:
        db.close()

@router.get("/{process_id}")
async def get_process_details(process_id: str):
    """
    Retorna os detalhes completos de auditoria e regras avaliadas para um processo real.
    """
    db = SessionLocal()
    try:
        proc = db.query(Process).filter(Process.id == process_id).first()
        if not proc:
            raise HTTPException(status_code=404, detail="Processo não encontrado.")

        eval_record = db.query(Evaluation).filter(Evaluation.process_id == proc.id).first()
        p_ver = db.query(PolicyVersion).filter(PolicyVersion.id == eval_record.policy_version_id).first() if eval_record else None

        theme_fact = db.query(ExtractedFact).filter(ExtractedFact.process_id == proc.id, ExtractedFact.fact_key == "identified_theme").first()
        identified_theme = theme_fact.normalized_value if theme_fact else None

        facts_records = db.query(ExtractedFact).filter(ExtractedFact.process_id == proc.id).all()
        facts_dict = {}
        for fr in facts_records:
            facts_dict[fr.fact_key] = fr.fact_value

        pages_records = db.query(DocumentPage).filter(DocumentPage.process_id == proc.id).order_by(DocumentPage.page_number.asc()).all()
        pages_list = []
        for pr in pages_records:
            pages_list.append({
                "page_number": pr.page_number,
                "document_name": pr.document_name or "documento.pdf",
                "page_in_document": pr.page_in_document or pr.page_number,
                "segment_type": pr.segment_type or "OUTROS",
                "raw_text": pr.raw_text or "",
                "quality_score": pr.quality_score,
                "has_native_text": pr.has_native_text,
                "words_data": pr.words_data or []
            })

        return {
            "process_id": proc.id,
            "cnj_number": proc.cnj_number,
            "beneficiary_name": proc.beneficiary_name,
            "operator_name": proc.operator_name,
            "total_pages": proc.total_pages,
            "status": proc.status,
            "verdict": eval_record.overall_result if eval_record else "PENDING",
            "summary": eval_record.decision_summary if eval_record else "Em processamento",
            "identified_theme": identified_theme,
            "policy_version": p_ver.version if p_ver else "2026.1",
            "total_pages_stored": len(pages_records),
            "pages": pages_list,
            "facts": facts_dict,
            "rules": eval_record.rules_results if eval_record and eval_record.rules_results else []
        }
    finally:
        db.close()

@router.post("/upload")
async def upload_judicial_process(
    files: Optional[List[UploadFile]] = File(default=None),
    file: Optional[UploadFile] = File(default=None),
    cnj_number: Optional[str] = Form(default=None),
    beneficiary_name: Optional[str] = Form(default="Beneficiário dos Autos"),
    operator_name: Optional[str] = Form(default="Grupo Amil")
):
    """
    Recebe um ou múltiplos arquivos PDF reais que compõem o processo judicial,
    processa todas as páginas no motor OCR em cascata, cruza evidências entre as peças
    (Petição Inicial, Laudos Médicos, Notas Fiscais, Negativas) e emite o veredito determinístico.
    """
    all_uploads = []
    if files:
        all_uploads.extend(files)
    if file:
        all_uploads.append(file)

    if not all_uploads:
        raise HTTPException(status_code=400, detail="Nenhum arquivo PDF foi selecionado.")

    pdf_files_payload = []
    for f in all_uploads:
        if not f.filename:
            continue
        if not f.filename.lower().endswith(".pdf"):
            raise HTTPException(status_code=400, detail=f"O arquivo '{f.filename}' não é um PDF válido.")
        pdf_bytes = await f.read()
        if not pdf_bytes or len(pdf_bytes) == 0:
            raise HTTPException(status_code=400, detail=f"O arquivo '{f.filename}' está vazio ou corrompido.")
        pdf_files_payload.append({
            "bytes": pdf_bytes,
            "filename": f.filename
        })

    if not pdf_files_payload:
        raise HTTPException(status_code=400, detail="Nenhum PDF válido para processamento.")

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "operadora-saude-padrao").first()
        tenant_id = tenant.id if tenant else "default_tenant"

        proc_id = generate_uuid()
        effective_cnj = cnj_number if (cnj_number and len(cnj_number) > 5) else f"000{generate_uuid()[:4]}-50.2025.8.26.0100"

        proc = db.query(Process).filter(
            Process.tenant_id == tenant_id,
            Process.cnj_number == effective_cnj
        ).first()

        if not proc:
            proc = Process(
                id=proc_id,
                tenant_id=tenant_id,
                cnj_number=effective_cnj,
                beneficiary_name=beneficiary_name or "Beneficiário dos Autos",
                operator_name=operator_name or "Grupo Amil",
                status="PROCESSING"
            )
            db.add(proc)
            db.commit()
        else:
            proc.status = "PROCESSING"
            proc_id = proc.id
            db.commit()

        # Executa esteira completa multi-documento
        service = ProcessExecutionService(db=db)
        result = service.process_and_evaluate_multi(
            tenant_id=tenant_id,
            process_id=proc_id,
            pdf_files=pdf_files_payload
        )

        return {
            "status": "SUCCESS",
            "process_id": proc_id,
            "cnj_number": effective_cnj,
            "beneficiary_name": beneficiary_name or "Beneficiário dos Autos",
            "operator_name": operator_name or "Grupo Amil",
            "documents_count": result.get("documents_count", len(pdf_files_payload)),
            "documents_summary": result.get("documents_summary", []),
            "total_pages": result["total_pages"],
            "policy_version": result["policy_version"],
            "identified_theme": result.get("identified_theme"),
            "verdict": result["verdict"],
            "summary": result["summary"],
            "rules": result["rules"]
        }
    finally:
        db.close()
