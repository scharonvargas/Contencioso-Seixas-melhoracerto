"""
scripts/clean_database.py
Higieniza completamente o banco de dados e o storage, removendo quaisquer dados fictícios,
mantendo exclusivamente o Tenant da Operadora e o Manual Oficial da Amil (16 págs / 21 temas) como Norma ACTIVE.
"""

import sys
import os
import shutil
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.core.database import SessionLocal, init_db
from src.models.entities import (
    Tenant, User, Policy, PolicyVersion, Process,
    DocumentPage, ExtractedFact, Evidence, Evaluation,
    HumanReview, AuditLog, generate_uuid
)
from scripts.seed_corporate_manual import seed_corporate_policy_from_pdf

def clean_and_sanitize():
    print("=" * 80)
    print("INICIANDO HIGIENIZAÇÃO COMPLETA DO SISTEMA (ZERO DADOS FICTÍCIOS)...")
    print("=" * 80)

    # 1. Limpa diretórios de storage de arquivos processados
    for folder in ["storage_data/processes", "storage_data/pages", "test_storage_dir"]:
        p = Path(folder)
        if p.exists():
            shutil.rmtree(p)
            print(f"Diretório limpo: {folder}")
        p.mkdir(parents=True, exist_ok=True)

    init_db()
    db = SessionLocal()
    try:
        # Limpa todas as tabelas transacionais de processos e avaliações
        db.query(AuditLog).delete()
        db.query(HumanReview).delete()
        db.query(Evaluation).delete()
        db.query(Evidence).delete()
        db.query(ExtractedFact).delete()
        db.query(DocumentPage).delete()
        db.query(Process).delete()
        db.query(PolicyVersion).delete()
        db.query(Policy).delete()
        db.commit()
        print("Tabelas limpas com sucesso: 0 processos e normas antigas removidas.")
    finally:
        db.close()

    # 3. Compila e registra o Manual Oficial de Acordos da Amil (21 Temas)
    seed_corporate_policy_from_pdf()

    print("\n" + "=" * 80)
    print("HIGIENIZAÇÃO CONCLUÍDA! O SISTEMA ESTÁ PRONTO PARA CASOS REAIS.")
    print("=" * 80)

if __name__ == "__main__":
    clean_and_sanitize()
