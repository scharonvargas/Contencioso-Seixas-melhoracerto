"""
src/api/routes/policies.py
Rotas REST para gestão, upload e diff de Normas Internas e Manuais de Acordo.
"""

from fastapi import APIRouter, HTTPException, UploadFile, File, Form
from pydantic import BaseModel
from typing import Dict, Any, List, Optional
import hashlib
from sqlalchemy.sql import func
from src.rule_engine.semantic_diff import PolicySemanticDiff
from src.rule_engine.policy_compiler import DynamicPolicyCompiler
from src.core.database import SessionLocal
from src.models.entities import Policy, PolicyVersion, Tenant, generate_uuid

router = APIRouter(prefix="/policies", tags=["Gestão de Normas Internas"])

class ActivatePolicyRequest(BaseModel):
    version_id: str
    tenant_id: str = "tenant_saude_001"

@router.get("/active")
async def get_active_policy(tenant_id: Optional[str] = None):
    """
    Retorna a única versão da norma interna vigente (status = 'ACTIVE') cadastrada para o tenant.
    """
    db = SessionLocal()
    try:
        t_id = tenant_id or "tenant_saude_001"
        tenant = db.query(Tenant).filter(Tenant.slug == "operadora-saude-padrao").first()
        if not tenant_id and tenant:
            t_id = tenant.id

        active_ver = (
            db.query(PolicyVersion)
            .filter(PolicyVersion.tenant_id == t_id, PolicyVersion.status == "ACTIVE")
            .order_by(PolicyVersion.activated_at.desc(), PolicyVersion.created_at.desc())
            .first()
        )

        if not active_ver:
            # Se não houver ativa para este tenant específico, busca primeira com status ACTIVE deste tenant
            active_ver = (
                db.query(PolicyVersion)
                .filter(PolicyVersion.tenant_id == t_id)
                .order_by(PolicyVersion.created_at.desc())
                .first()
            )
            if active_ver and active_ver.status == "ACTIVE":
                pass
            elif not active_ver:
                return {"status": "NO_ACTIVE_POLICY", "message": f"Nenhuma norma ativa cadastrada para o tenant '{t_id}'."}

        if not active_ver or active_ver.status != "ACTIVE":
            return {"status": "NO_ACTIVE_POLICY", "message": f"Nenhuma norma ativa cadastrada para o tenant '{t_id}'."}

        structured = active_ver.structured_rules or {}
        rules_list = structured.get("all_rules") or structured.get("rules", [])
        if not rules_list and "topics" in structured:
            rules_list = [r for t in structured["topics"] for r in t.get("rules", [])]

        topics_list = structured.get("topics", [])
        return {
            "id": active_ver.id,
            "version": active_ver.version,
            "status": active_ver.status,
            "structured_rules": structured,
            "topics": topics_list,
            "total_topics": len(topics_list),
            "rules": rules_list,
            "total_rules": len(rules_list)
        }
    finally:
        db.close()


class CreateDraftPolicyRequest(BaseModel):
    policy_name: str = "Manual de Acordos"
    version: str
    rules: List[Dict[str, Any]]
    tenant_id: str = "tenant_saude_001"

@router.post("/draft")
async def create_policy_draft(request: CreateDraftPolicyRequest):
    """
    Cria uma nova versão da norma em estado DRAFT a partir de regras estruturadas (JSON).
    """
    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "operadora-saude-padrao").first()
        t_id = tenant.id if tenant else request.tenant_id

        policy = db.query(Policy).filter(Policy.tenant_id == t_id).first()
        if not policy:
            policy = Policy(id=generate_uuid(), tenant_id=t_id, name=request.policy_name)
            db.add(policy)
            db.commit()

        p_version = db.query(PolicyVersion).filter(
            PolicyVersion.tenant_id == t_id,
            PolicyVersion.version == request.version
        ).first()

        if p_version:
            p_version.structured_rules = {
                "policy_version_id": request.version,
                "rules": request.rules
            }
            p_version.status = "DRAFT"
            db.commit()
            return {
                "id": p_version.id,
                "version_id": p_version.id,
                "version": p_version.version,
                "status": "DRAFT",
                "total_rules": len(request.rules)
            }

        new_version_id = generate_uuid()
        p_version = PolicyVersion(
            id=new_version_id,
            tenant_id=t_id,
            policy_id=policy.id,
            version=request.version,
            status="DRAFT",
            file_hash_sha256="manual_json_draft",
            pdf_storage_path=f"policies/{t_id}/{new_version_id}.json",
            structured_rules={
                "policy_version_id": request.version,
                "rules": request.rules
            }
        )
        db.add(p_version)
        db.commit()

        return {
            "id": new_version_id,
            "version_id": new_version_id,
            "version": request.version,
            "status": "DRAFT",
            "total_rules": len(request.rules)
        }
    finally:
        db.close()

@router.post("/upload-pdf")
async def upload_policy_pdf(
    file: UploadFile = File(...),
    version: Optional[str] = Form(default=None),
    policy_name: Optional[str] = Form(default="Manual de Acordos de Saúde"),
    tenant_id: Optional[str] = Form(default="tenant_saude_001")
):
    """
    Recebe o PDF do Manual / Norma Interna submetido pelo usuário, extrai 100% dos critérios
    dinamicamente sem regras prévias em código e salva como DRAFT para revisão humana.
    """
    if not file or not file.filename:
        raise HTTPException(status_code=400, detail="Nenhum arquivo PDF selecionado.")

    import pathlib
    safe_filename = pathlib.Path(file.filename).name
    if not safe_filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Apenas arquivos no formato PDF são permitidos.")

    pdf_bytes = await file.read()
    if not pdf_bytes or len(pdf_bytes) == 0:
        raise HTTPException(status_code=400, detail="Arquivo PDF vazio ou corrompido.")

    if not pdf_bytes.startswith(b"%PDF-"):
        raise HTTPException(status_code=400, detail="Arquivo inválido: Magic Bytes do cabeçalho PDF não identificados.")

    try:
        file_hash = hashlib.sha256(pdf_bytes).hexdigest()
        raw_text = DynamicPolicyCompiler.extract_text_from_pdf(pdf_bytes)
        
        effective_version = version if (version and len(version.strip()) > 0) else f"V-{file_hash[:6].upper()}"

        raw_lower = raw_text.lower()
        if "requisitos" in raw_lower or "parâmetros" in raw_lower or "parametros" in raw_lower or "instrução de trabalho" in raw_lower or "regras gerais" in raw_lower or "assistencial" in raw_lower:
            compiled_corp = DynamicPolicyCompiler.compile_corporate_manual(
                pdf_text=raw_text,
                policy_name=policy_name or "Manual de Parâmetros de Acordos",
                version=effective_version,
                file_hash=file_hash
            )
            structured_rules = {
                "policy_version_id": effective_version,
                "topics": [t.model_dump() for t in compiled_corp.topics],
                "general_rules": compiled_corp.general_rules,
                "rules": compiled_corp.all_rules
            }
            extracted_count = len(compiled_corp.all_rules)
            policy_title = compiled_corp.policy_name
            rules_list = compiled_corp.all_rules
        else:
            compiled = DynamicPolicyCompiler.compile_from_pdf_text(
                pdf_text=raw_text,
                policy_name=policy_name or "Manual de Acordos",
                version=effective_version,
                file_hash=file_hash
            )
            structured_rules = {
                "policy_version_id": effective_version,
                "rules": [r.model_dump() for r in compiled.rules]
            }
            extracted_count = compiled.total_criteria_extracted
            policy_title = compiled.policy_name
            rules_list = [r.model_dump() for r in compiled.rules]

        db = SessionLocal()
        try:
            tenant = db.query(Tenant).filter(Tenant.slug == "operadora-saude-padrao").first()
            t_id = tenant.id if tenant else (tenant_id or "default_tenant")

            policy = db.query(Policy).filter(Policy.tenant_id == t_id).first()
            if not policy:
                policy = Policy(id=generate_uuid(), tenant_id=t_id, name=policy_title)
                db.add(policy)
                db.commit()

            # Desativa SOMENTE as outras versões deste mesmo tenant de forma atômica
            db.query(PolicyVersion).filter(PolicyVersion.tenant_id == t_id).update({"status": "INACTIVE"})

            # Busca se já existe uma versão com este nome para o mesmo tenant
            p_version = db.query(PolicyVersion).filter(
                PolicyVersion.tenant_id == t_id,
                PolicyVersion.version == effective_version
            ).first()

            if p_version:
                new_version_id = p_version.id
                p_version.policy_id = policy.id
                p_version.file_hash_sha256 = file_hash
                p_version.status = "ACTIVE"
                p_version.structured_rules = structured_rules
                p_version.activated_at = func.now()
                db.commit()
            else:
                new_version_id = generate_uuid()
                p_version = PolicyVersion(
                    id=new_version_id,
                    tenant_id=t_id,
                    policy_id=policy.id,
                    version=effective_version,
                    status="ACTIVE",
                    file_hash_sha256=file_hash,
                    pdf_storage_path=f"policies/{t_id}/{new_version_id}.pdf",
                    structured_rules=structured_rules,
                    activated_at=func.now()
                )
                db.add(p_version)
                db.commit()

            topics_res = structured_rules.get("topics", [])
            return {
                "status": "SUCCESS",
                "version_id": new_version_id,
                "version": effective_version,
                "policy_name": policy.name,
                "topics": topics_res,
                "total_topics": len(topics_res),
                "extracted_criteria_count": extracted_count,
                "total_criteria_extracted": extracted_count,
                "rules": rules_list
            }
        finally:
            db.close()


    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Falha ao processar e compilar PDF do Manual: {str(e)}")

@router.get("/{version_id}/diff")
async def get_policy_diff_for_version(version_id: str):
    """
    Calcula a diferença semântica entre a norma atualmente ACTIVE e a versão informada.
    """
    db = SessionLocal()
    try:
        active_ver = db.query(PolicyVersion).filter(PolicyVersion.status == "ACTIVE").first()
        target_ver = db.query(PolicyVersion).filter(
            (PolicyVersion.id == version_id) | (PolicyVersion.version == version_id)
        ).first()

        if not target_ver:
            raise HTTPException(status_code=404, detail="Versão de destino não encontrada.")

        source_rules = active_ver.structured_rules.get("rules", []) if active_ver else []
        target_rules = target_ver.structured_rules.get("rules", [])

        base_name = active_ver.version if active_ver else "NENHUMA"
        diff = PolicySemanticDiff.compare_policies(
            base_policy_rules=source_rules,
            target_policy_rules=target_rules,
            base_ver=base_name,
            target_ver=target_ver.version
        )

        return diff.model_dump()
    finally:
        db.close()

@router.post("/{version_id}/activate")
async def activate_policy_version(version_id: str):
    """
    Ativação Atômica de Norma:
    Desativa a versão ACTIVE anterior e ativa a nova versão em uma única transação atômica.
    """
    db = SessionLocal()
    try:
        target_version = db.query(PolicyVersion).filter(
            (PolicyVersion.id == version_id) | (PolicyVersion.version == version_id)
        ).first()

        if not target_version:
            raise HTTPException(status_code=404, detail="Versão da norma não encontrada.")

        current_active = db.query(PolicyVersion).filter(
            PolicyVersion.tenant_id == target_version.tenant_id,
            PolicyVersion.status == "ACTIVE"
        ).all()

        for old_ver in current_active:
            old_ver.status = "INACTIVE"
            old_ver.deactivated_at = func.now()

        target_version.status = "ACTIVE"
        target_version.activated_at = func.now()
        db.commit()

        return {
            "status": "ACTIVE",
            "activated_version_id": target_version.id,
            "version": target_version.version,
            "total_rules": len(target_version.structured_rules.get("rules", []))
        }
    finally:
        db.close()
