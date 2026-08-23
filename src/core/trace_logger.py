"""
src/core/trace_logger.py
Sistema de Logging e Rastreabilidade Forense Multi-Fases para Análise de Processos.
Grava cada etapa da ingestão, OCR, extração, classificação de temas e avaliação de regras em arquivo e JSON.
"""

import os
import json
import time
from datetime import datetime, timezone
from typing import List, Dict, Any, Optional

class ProcessTraceLogger:
    def __init__(self, tenant_id: str, process_id: str, cnj_number: Optional[str] = None):
        self.tenant_id = tenant_id
        self.process_id = process_id
        self.cnj_number = cnj_number or "N/A"
        self.start_time = time.time()
        self.events: List[Dict[str, Any]] = []
        self.phases: Dict[str, Dict[str, Any]] = {
            "FASE_1_INGESTAO_OCR": {"status": "PENDING", "logs": [], "metrics": {}},
            "FASE_2_SEGMENTACAO_PECAS": {"status": "PENDING", "logs": [], "metrics": {}},
            "FASE_3_EXTRACAO_FATOS": {"status": "PENDING", "logs": [], "metrics": {}},
            "FASE_4_CLASSIFICACAO_TEMA": {"status": "PENDING", "logs": [], "metrics": {}},
            "FASE_5_AVALIACAO_REGRAS": {"status": "PENDING", "logs": [], "metrics": {}},
            "FASE_6_VEREDITO_FINAL": {"status": "PENDING", "logs": [], "metrics": {}}
        }

    def log(self, phase: str, message: str, level: str = "INFO", details: Optional[Dict[str, Any]] = None):
        """Registra um evento em uma fase específica."""
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        elapsed_ms = int((time.time() - self.start_time) * 1000)
        
        entry = {
            "timestamp": timestamp,
            "elapsed_ms": elapsed_ms,
            "phase": phase,
            "level": level,
            "message": message,
            "details": details or {}
        }
        self.events.append(entry)
        
        if phase in self.phases:
            self.phases[phase]["logs"].append(entry)
            if level == "ERROR":
                self.phases[phase]["status"] = "ERROR"
            elif self.phases[phase]["status"] == "PENDING":
                self.phases[phase]["status"] = "IN_PROGRESS"

    def complete_phase(self, phase: str, status: str = "COMPLETED", metrics: Optional[Dict[str, Any]] = None):
        """Marca uma fase como concluída com métricas."""
        if phase in self.phases:
            self.phases[phase]["status"] = status
            if metrics:
                self.phases[phase]["metrics"].update(metrics)
        self.log(phase, f"Fase finalizada com status: {status}", level="SUCCESS" if status == "COMPLETED" else "WARNING", details=metrics)

    def to_dict(self) -> Dict[str, Any]:
        """Exporta o trace estruturado completo."""
        total_duration_ms = int((time.time() - self.start_time) * 1000)
        return {
            "process_id": self.process_id,
            "cnj_number": self.cnj_number,
            "tenant_id": self.tenant_id,
            "start_time": datetime.fromtimestamp(self.start_time).strftime("%Y-%m-%d %H:%M:%S"),
            "total_duration_ms": total_duration_ms,
            "total_events": len(self.events),
            "phases": self.phases,
            "timeline": self.events
        }

    def save_to_disk(self, log_dir: str = "logs/processes") -> str:
        """Salva os logs detalhados em formato JSON e texto legível na pasta logs/."""
        os.makedirs(log_dir, exist_ok=True)
        
        # 1. Salva arquivo JSON estruturado
        json_path = os.path.join(log_dir, f"{self.process_id}_trace.json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(self.to_dict(), f, ensure_ascii=False, indent=2)
            
        # 2. Salva arquivo de texto legível para auditoria humana rápida
        txt_path = os.path.join(log_dir, f"{self.process_id}.log")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(f"================================================================================\n")
            f.write(f"SEIXAS AI — LOG DE AUDITORIA FORENSE DE PROCESSO JUDICIAL\n")
            f.write(f"Processo ID : {self.process_id}\n")
            f.write(f"Número CNJ  : {self.cnj_number}\n")
            f.write(f"Início      : {datetime.fromtimestamp(self.start_time).strftime('%Y-%m-%d %H:%M:%S')}\n")
            f.write(f"Duração     : {int((time.time() - self.start_time) * 1000)} ms\n")
            f.write(f"================================================================================\n\n")
            
            for p_name, p_data in self.phases.items():
                f.write(f"--- [{p_name}] Status: {p_data['status']} ---\n")
                if p_data.get("metrics"):
                    f.write(f"Métricas: {json.dumps(p_data['metrics'], ensure_ascii=False)}\n")
                for entry in p_data.get("logs", []):
                    f.write(f"  [{entry['elapsed_ms']:05d} ms] [{entry['level']}] {entry['message']}\n")
                    if entry.get("details"):
                        f.write(f"         Detalhes: {json.dumps(entry['details'], ensure_ascii=False)}\n")
                f.write("\n")
                
        return json_path
