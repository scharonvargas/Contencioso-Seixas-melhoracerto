"""
src/models/entities.py
Modelos ORM SQLAlchemy completos para PostgreSQL / SQLite.
"""

from sqlalchemy import (
    Column, String, Text, Boolean, Integer, Float, Numeric, DateTime, ForeignKey, JSON, CheckConstraint, UniqueConstraint
)
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy.sql import func
import uuid

Base = declarative_base()

def generate_uuid():
    return str(uuid.uuid4())

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    corporate_name = Column(String(255), nullable=False)
    trade_name = Column(String(255), nullable=False)
    cnpj = Column(String(14), nullable=False, unique=True)
    slug = Column(String(64), nullable=False, unique=True)
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(32), nullable=False, default="OPERATOR")
    is_active = Column(Boolean, nullable=False, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    __table_args__ = (UniqueConstraint("tenant_id", "email", name="uq_tenant_user_email"),)

class Policy(Base):
    __tablename__ = "policies"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class PolicyVersion(Base):
    __tablename__ = "policy_versions"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    policy_id = Column(String(36), ForeignKey("policies.id"), nullable=False)
    version = Column(String(32), nullable=False)
    status = Column(String(16), nullable=False, default="DRAFT") # DRAFT, ACTIVE, INACTIVE
    file_hash_sha256 = Column(String(64), nullable=False)
    pdf_storage_path = Column(Text, nullable=False)
    structured_rules = Column(JSON, nullable=False)
    diff_from_previous = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    activated_at = Column(DateTime(timezone=True))
    deactivated_at = Column(DateTime(timezone=True))
    approved_by = Column(String(36), ForeignKey("users.id"))
    __table_args__ = (UniqueConstraint("tenant_id", "policy_id", "version", name="uq_tenant_policy_ver"),)

class Process(Base):
    __tablename__ = "processes"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    cnj_number = Column(String(32), nullable=False)
    court_name = Column(String(128))
    beneficiary_name = Column(String(255), nullable=False)
    beneficiary_cpf = Column(String(11))
    operator_name = Column(String(255), nullable=False)
    status = Column(String(32), nullable=False, default="PENDING") # PENDING, PROCESSING, EVALUATED, REQUIRES_HUMAN_REVIEW, ERROR
    total_pages = Column(Integer, nullable=False, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    __table_args__ = (UniqueConstraint("tenant_id", "cnj_number", name="uq_tenant_cnj"),)

class DocumentPage(Base):
    __tablename__ = "document_pages"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    process_id = Column(String(36), ForeignKey("processes.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    document_name = Column(String(255), nullable=True)
    page_in_document = Column(Integer, nullable=True)
    segment_type = Column(String(64), nullable=True) # PETICAO_INICIAL, LAUDO_MEDICO, NOTA_FISCAL, NEGATIVA, etc.
    raw_text = Column(Text, nullable=True)
    words_data = Column(JSON, nullable=True)
    has_native_text = Column(Boolean, nullable=False, default=False)
    quality_score = Column(Float, nullable=False, default=1.0)
    blur_variance = Column(Float)
    image_storage_path = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class ExtractedFact(Base):
    __tablename__ = "extracted_facts"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    process_id = Column(String(36), ForeignKey("processes.id"), nullable=False)
    fact_category = Column(String(64), nullable=False) # FINANCIAL, MEDICAL, ADMINISTRATIVE
    fact_key = Column(String(128), nullable=False)
    fact_value = Column(JSON, nullable=False)
    normalized_value = Column(Text, nullable=False)
    extraction_confidence = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Evidence(Base):
    __tablename__ = "evidences"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    fact_id = Column(String(36), ForeignKey("extracted_facts.id"), nullable=False)
    page_number = Column(Integer, nullable=False)
    bounding_box = Column(JSON, nullable=False) # [ymin, xmin, ymax, xmax]
    exact_text_snippet = Column(Text, nullable=False)
    ocr_engine_used = Column(String(32), nullable=False)
    confidence_score = Column(Float, nullable=False, default=1.0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class Evaluation(Base):
    __tablename__ = "evaluations"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    process_id = Column(String(36), ForeignKey("processes.id"), nullable=False)
    policy_version_id = Column(String(36), ForeignKey("policy_versions.id"), nullable=False)
    overall_result = Column(String(32), nullable=False) # ELIGIBLE, INELIGIBLE, REQUIRES_HUMAN_REVIEW
    total_rules_evaluated = Column(Integer, nullable=False, default=0)
    rules_passed = Column(Integer, nullable=False, default=0)
    rules_failed = Column(Integer, nullable=False, default=0)
    rules_unknown = Column(Integer, nullable=False, default=0)
    decision_summary = Column(Text, nullable=False)
    rules_results = Column(JSON, nullable=True) # Persist evaluation rules
    execution_trace = Column(JSON, nullable=True) # Persist detailed phase-by-phase trace log
    evaluated_at = Column(DateTime(timezone=True), server_default=func.now())

class HumanReview(Base):
    __tablename__ = "human_reviews"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), ForeignKey("tenants.id"), nullable=False)
    process_id = Column(String(36), ForeignKey("processes.id"), nullable=False)
    evaluation_id = Column(String(36), ForeignKey("evaluations.id"), nullable=False)
    status = Column(String(32), nullable=False, default="OPEN") # OPEN, RESOLVED
    review_reason = Column(String(64), nullable=False)
    operator_decision = Column(String(32))
    operator_notes = Column(Text)
    resolved_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class AuditLog(Base):
    __tablename__ = "audit_logs"
    id = Column(String(36), primary_key=True, default=generate_uuid)
    tenant_id = Column(String(36), nullable=False)
    user_id = Column(String(36))
    event_type = Column(String(64), nullable=False)
    entity_name = Column(String(64), nullable=False)
    entity_id = Column(String(36), nullable=False)
    payload = Column(JSON)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
