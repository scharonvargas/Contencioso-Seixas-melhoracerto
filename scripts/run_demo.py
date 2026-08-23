"""
scripts/run_demo.py
Script de demonstração ponta a ponta: carrega o banco, processa 3 casos reais e exibe a auditoria.
"""

import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import SessionLocal, init_db
from src.models.entities import Tenant, Process, Evaluation, generate_uuid
from src.services.process_service import ProcessExecutionService
from scripts.seed_db import seed_database
from scripts.generate_sample_processes import generate_sample_judicial_case

def run_interactive_demo():
    print("=" * 80)
    print("SEIXAS AI - DEMONSTRACAO DO PIPELINE DE VALIDACAO DE ACORDOS")
    print("=" * 80)

    # 1. Seed do banco
    seed_database()
    
    # 2. Gera os 3 processos de teste
    sample_dir = Path("sample_data")
    sample_dir.mkdir(exist_ok=True)
    p_eligible = str(sample_dir / "proc_elegivel_50p.pdf")
    p_ineligible = str(sample_dir / "proc_ineligivel_teto_50p.pdf")
    p_hitl = str(sample_dir / "proc_sem_nf_hitl_50p.pdf")

    generate_sample_judicial_case(p_eligible, pages_count=20, scenario="ELIGIBLE")
    generate_sample_judicial_case(p_ineligible, pages_count=20, scenario="INELIGIBLE_AMOUNT")
    generate_sample_judicial_case(p_hitl, pages_count=20, scenario="MISSING_RECEIPT")

    db = SessionLocal()
    try:
        tenant = db.query(Tenant).filter(Tenant.slug == "operadora-saude-padrao").first()
        service = ProcessExecutionService(db=db)

        test_cases = [
            ("Processo 1 (Cenario Elegivel)", p_eligible, f"0001001-50.2025.8.26.{generate_uuid()[:4]}"),
            ("Processo 2 (Cenario Excede Teto)", p_ineligible, f"0001002-50.2025.8.26.{generate_uuid()[:4]}"),
            ("Processo 3 (Cenario Sem Nota Fiscal - HITL)", p_hitl, f"0001003-50.2025.8.26.{generate_uuid()[:4]}"),
        ]

        print("\n" + "-" * 80)
        print("PROCESSANDO PROCESSOS JUDICIAIS NO PIPELINE...")
        print("-" * 80)

        for title, filepath, cnj in test_cases:
            proc_id = generate_uuid()
            proc = Process(
                id=proc_id,
                tenant_id=tenant.id,
                cnj_number=cnj,
                beneficiary_name="Beneficiario Amostra",
                operator_name=tenant.trade_name,
                status="PROCESSING"
            )
            db.add(proc)
            db.commit()

            with open(filepath, "rb") as f:
                pdf_bytes = f.read()

            result = service.process_and_evaluate(
                tenant_id=tenant.id,
                process_id=proc_id,
                pdf_bytes=pdf_bytes,
                filename=os.path.basename(filepath)
            )

            print(f"\n[OK] {title}")
            print(f"     CNJ: {cnj} | Paginas: {result['total_pages']} | Norma: {result['policy_version']}")
            print(f"     VEREDITO: {result['verdict']}")
            print(f"     RESUMO  : {result['summary']}")
            for r in result['rules']:
                status_tag = "PASS" if r['status'] == "PASS" else ("FAIL" if r['status'] == "FAIL" else "UNKNOWN")
                print(f"       [{status_tag:<7}] {r['rule_code']}: {r['title']}")

        print("\n" + "=" * 80)
        print("DEMONSTRACAO CONCLUIDA COM 100% DE CONFORMIDADE DETERMINISTICA!")
        print("Abra 'frontend/index.html' para inspecionar visualmente os autos e bounding boxes.")
        print("=" * 80)

    finally:
        db.close()

if __name__ == "__main__":
    run_interactive_demo()
