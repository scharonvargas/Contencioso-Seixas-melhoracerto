"""
scripts/reprocess_local_database.py
Reprocessa todos os processos existentes na base de dados local (seixas_local.db)
utilizando o motor determinístico e o novo extrator forense contra a norma ativa (2026.1-AMIL-IT-ACORDOS).
"""

import sys
import os
from pathlib import Path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

sys.stdout.reconfigure(encoding="utf-8")

from src.core.config import settings
settings.OPENROUTER_API_KEY = ""

from src.core.database import SessionLocal
from src.models.entities import Process, DocumentPage, ExtractedFact, Evaluation, PolicyVersion, generate_uuid
from src.services.process_service import ProcessExecutionService
from src.rule_engine.deterministic_engine import DeterministicRuleEngine

def reprocess_all():
    db = SessionLocal()
    try:
        # 1. Carrega Norma Ativa
        active_policy = db.query(PolicyVersion).filter(
            PolicyVersion.version == "2026.1-AMIL-IT-ACORDOS",
            PolicyVersion.status == "ACTIVE"
        ).first()

        if not active_policy:
            active_policy = db.query(PolicyVersion).filter(PolicyVersion.status == "ACTIVE").first()

        if not active_policy:
            print("ERRO: Nenhuma norma ativa encontrada. Execute python scripts/seed_corporate_manual.py primeiro.")
            return

        print("=" * 90)
        print(f"REPROCESSANDO BASE LOCAL CONTRA A NORMA ATIVA: {active_policy.version}")
        print(f"Total de Temas na Norma: {active_policy.structured_rules.get('total_topics', 0)}")
        print("=" * 90)

        service = ProcessExecutionService(db)
        engine = DeterministicRuleEngine(active_policy.structured_rules)

        processes = db.query(Process).all()
        print(f"Total de processos encontrados no banco: {len(processes)}\n")

        reprocessed_count = 0
        skipped_count = 0
        summary_results = []

        for p in processes:
            pages = db.query(DocumentPage).filter(DocumentPage.process_id == p.id).order_by(DocumentPage.page_number.asc()).all()
            if not pages:
                skipped_count += 1
                continue

            pages_data = [{
                "page_number": dp.page_number,
                "document_name": dp.document_name,
                "segment_type": dp.segment_type,
                "raw_text": dp.raw_text,
                "words_data": dp.words_data or []
            } for dp in pages]

            # Extrai fatos com extrator atualizado
            facts = service._extract_facts(
                pages_data,
                tenant_id=p.tenant_id,
                process_id=p.id,
                structured_rules=active_policy.structured_rules
            )

            # Avalia deterministricamente
            decision = engine.evaluate(process_id=p.id, case_fact_data=facts)

            # Atualiza ou cria Avaliação (Evaluation)
            existing_eval = db.query(Evaluation).filter(
                Evaluation.process_id == p.id,
                Evaluation.policy_version_id == active_policy.id
            ).first()

            eval_payload = {
                "rule_results": [r.model_dump() for r in decision.rule_results],
                "segregated_amounts": decision.segregated_amounts,
                "summary": decision.summary
            }

            if existing_eval:
                existing_eval.verdict = decision.overall_verdict
                existing_eval.summary = decision.summary
                existing_eval.rules_evaluation_trace = eval_payload
            else:
                new_eval = Evaluation(
                    id=generate_uuid(),
                    tenant_id=p.tenant_id,
                    process_id=p.id,
                    policy_version_id=active_policy.id,
                    verdict=decision.overall_verdict,
                    summary=decision.summary,
                    rules_evaluation_trace=eval_payload
                )
                db.add(new_eval)

            # Atualiza status do processo
            p.status = "EVALUATED"

            # Atualiza ExtractedFact de tema e financeiro
            theme_fact = db.query(ExtractedFact).filter(
                ExtractedFact.process_id == p.id,
                ExtractedFact.fact_key == "identified_theme"
            ).first()
            if theme_fact:
                theme_fact.fact_value = {
                    "theme": facts.get("identified_theme", "Geral"),
                    "applicable_topic_num": facts.get("applicable_topic_num", 1)
                }
                theme_fact.normalized_value = str(facts.get("identified_theme", "Geral"))

            fin_fact = db.query(ExtractedFact).filter(
                ExtractedFact.process_id == p.id,
                ExtractedFact.fact_key == "financial_summary"
            ).first()
            if fin_fact:
                fin_fact.fact_value = facts.get("financial", {})

            reprocessed_count += 1
            
            # Formata resumo
            doc_name = pages[0].document_name or "autos.pdf"
            ben_name = p.beneficiary_name or "N/A"
            theme_name = facts.get("identified_theme", "N/A")
            req_amt = facts.get("financial", {}).get("requested_amount", 0.0)
            moral_amt = facts.get("financial", {}).get("moral_damage_amount", 0.0)

            summary_results.append({
                "process_id": p.id,
                "cnj": p.cnj_number,
                "beneficiary": ben_name,
                "doc_name": doc_name,
                "pages": len(pages),
                "theme": theme_name,
                "req_amount": req_amt,
                "moral_amount": moral_amt,
                "verdict": decision.overall_verdict
            })

        db.commit()

        print(f"SUCESSO: {reprocessed_count} processos reprocessados e persistidos no banco local. ({skipped_count} ignorados sem páginas).\n")
        print("-" * 120)
        print(f"{'CNJ':<26} | {'BENEFICIÁRIO':<22} | {'TEMA':<24} | {'DANO MORAL':<12} | {'VEREDITO':<12}")
        print("-" * 120)

        # Mostra os distintos
        seen_keys = set()
        for r in summary_results:
            key = (r["beneficiary"], r["theme"], r["verdict"], round(r["moral_amount"], 2))
            if key in seen_keys:
                continue
            seen_keys.add(key)
            print(f"{r['cnj']:<26} | {r['beneficiary'][:22]:<22} | {r['theme'][:24]:<24} | R$ {r['moral_amount']:>9,.2f} | {r['verdict']:<12}")

        print("-" * 120)
        print("Todos os vereditos, traces de regras e valores segregados foram atualizados no SQLite.")
        print("=" * 90)

    finally:
        db.close()

if __name__ == "__main__":
    reprocess_all()
