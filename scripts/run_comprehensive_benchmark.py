"""
scripts/run_comprehensive_benchmark.py
Executa uma bateria completa de 5 processos judiciais reais/sintéticos contra o
Manual de Parâmetros de Acordos ativo no Seixas AI, auditando cada decisão.
"""

import os
import requests
import json
import fitz

BASE_URL = "http://127.0.0.1:8000"

def create_pdf(pages_data, filepath):
    doc = fitz.open()
    for p_title, p_lines in pages_data:
        page = doc.new_page()
        text = f"{p_title}\n\n" + "\n".join(p_lines)
        page.insert_text((50, 60), text, fontsize=11)
    doc.save(filepath)
    doc.close()
    return filepath

def generate_benchmark_processes():
    os.makedirs("scratch/benchmark", exist_ok=True)
    
    # Processo 1: Reembolso Regular com Comprovante (Elegível)
    p1 = create_pdf([
        ("PETIÇÃO INICIAL - AÇÃO DE REEMBOLSO", [
            "AUTOR: Ana Claudia Silva",
            "RÉU: Grupo Amil Assistência Médica Internacional S/A",
            "OBJETO: Cobrança de despesas médicas não reembolsadas.",
            "A autora realizou consultas e exames de urgência fora da rede no valor de R$ 4.800,00.",
            "Valor da Causa: R$ 4.800,00."
        ]),
        ("NOTA FISCAL DE PRESTAÇÃO DE SERVIÇOS MÉDICOS", [
            "TOMADOR: Ana Claudia Silva",
            "PRESTADOR: Centro Médico Especializado",
            "VALOR TOTAL DOS SERVIÇOS: R$ 4.800,00",
            "SITUAÇÃO: PAGO / QUITADO VIA PIX."
        ]),
        ("RESPOSTA ADMINISTRATIVA / NEGATIVA", [
            "Prezada Beneficiária,",
            "Informamos a negativa do pedido de reembolso sob protocolo nº 489201."
        ])
    ], "scratch/benchmark/proc_01_reembolso_regular.pdf")

    # Processo 2: Terapias Especiais ABA - Prestador Particular com Reembolso Integral (Hipótese VEDADA no Tema 1)
    p2 = create_pdf([
        ("PETIÇÃO INICIAL - AÇÃO DE OBRIGAÇÃO DE FAZER COM PEDIDO DE REEMBOLSO INTEGRAL", [
            "AUTOR: Menor Representado por Gabriel Toledo",
            "RÉU: Grupo Amil",
            "DIAGNÓSTICO: Transtorno do Espectro Autista (CID-10 F84.0).",
            "PEDIDO: Cobertura por meio de reembolso integral em prestador particular não credenciado (Clínica NeuroSaber).",
            "Valor da Causa: R$ 38.000,00."
        ]),
        ("LAUDO MÉDICO PERICIAL", [
            "Paciente com TEA necessita de terapia ABA 20 horas semanais.",
            "Indicação de tratamento em clínica particular da preferência da família."
        ])
    ], "scratch/benchmark/proc_02_terapias_prestador_particular.pdf")

    # Processo 3: Medicamento Off-Label / Sem Registro ANVISA (Hipótese VEDADA no Tema 3)
    p3 = create_pdf([
        ("PETIÇÃO INICIAL - FORNECIMENTO DE MEDICAMENTO OFF-LABEL", [
            "AUTOR: Roberto Mendes",
            "RÉU: Grupo Amil",
            "PEDIDO: Fornecimento de medicamento importado sem registro na ANVISA e de uso off-label experimental.",
            "Valor da Causa: R$ 85.000,00."
        ]),
        ("RECEITUÁRIO E LAUDO MÉDICO", [
            "Indicação de fármaco importado dos EUA sem nacionalização ou registro na Anvisa para uso experimental."
        ])
    ], "scratch/benchmark/proc_03_medicamento_sem_anvisa.pdf")

    # Processo 4: Cancelamento com Falha na Notificação Prévia (Elegível com dano moral até R$ 6.750,00)
    p4 = create_pdf([
        ("PETIÇÃO INICIAL - AÇÃO DECLARATÓRIA DE NULIDADE DE CANCELAMENTO", [
            "AUTOR: Maria Aparecida Santos",
            "RÉU: Grupo Amil",
            "FATO: Cancelamento de plano individual/PF sem o envio ou recebimento de notificação prévia de inadimplência.",
            "PEDIDO: Reativação do plano de saúde + danos morais no valor de R$ 6.000,00.",
            "Valor da Causa: R$ 6.000,00."
        ])
    ], "scratch/benchmark/proc_04_cancelamento_sem_notificacao.pdf")

    # Processo 5: Fraude de Boleto Pré-Condenação (Hipótese VEDADA no Tema 13)
    p5 = create_pdf([
        ("PETIÇÃO INICIAL - AÇÃO DE INEXIGIBILIDADE DE DÉBITO", [
            "AUTOR: Carlos Eduardo Paiva",
            "RÉU: Grupo Amil",
            "FATO: Fraude de boleto bancário falso emitido por terceiro golpista.",
            "FASE PROCESSUAL: Fase inicial (pré-condenação / pré-sentença).",
            "Valor da Causa: R$ 3.500,00."
        ])
    ], "scratch/benchmark/proc_05_fraude_boleto_pre_sentenca.pdf")

    return [
        {"id": "PROC-01", "cnj": "5001111-11.2025.8.26.0100", "name": "Ana Claudia Silva", "file": p1, "expected": "ELIGIBLE", "theme": "Reembolso"},
        {"id": "PROC-02", "cnj": "5002222-22.2025.8.26.0100", "name": "Gabriel Toledo (Menor)", "file": p2, "expected": "INELIGIBLE", "theme": "Terapias Especiais"},
        {"id": "PROC-03", "cnj": "5003333-33.2025.8.26.0100", "name": "Roberto Mendes", "file": p3, "expected": "INELIGIBLE", "theme": "Medicamentos"},
        {"id": "PROC-04", "cnj": "5004444-44.2025.8.26.0100", "name": "Maria Aparecida Santos", "file": p4, "expected": "ELIGIBLE", "theme": "Cancelamento"},
        {"id": "PROC-05", "cnj": "5005555-55.2025.8.26.0100", "name": "Carlos Eduardo Paiva", "file": p5, "expected": "INELIGIBLE", "theme": "Fraude de boleto"}
    ]

def run_benchmark():
    procs = generate_benchmark_processes()
    results = []

    print(f"\n=======================================================")
    print(f"BENCHMARK DE AUDITORIA — 5 PROCESSOS VS MANUAL OFICIAL")
    print(f"=======================================================\n")

    # Verifica se servidor externo está ativo; se não, usa TestClient in-process
    use_test_client = False
    client = None
    try:
        r = requests.get(f"{BASE_URL}/health", timeout=1.0)
        if r.status_code != 200:
            use_test_client = True
    except Exception:
        use_test_client = True

    if use_test_client:
        print("[INFO] Servidor externo não detectado na porta 8000. Executando in-process via FastAPI TestClient...\n")
        import sys
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from fastapi.testclient import TestClient
        from src.api.main import app
        client = TestClient(app)

    for p in procs:
        print(f"[*] Testando {p['id']} - {p['cnj']} ({p['name']})...")
        with open(p['file'], 'rb') as f:
            file_bytes = f.read()
            files = [('files', (os.path.basename(p['file']), file_bytes, 'application/pdf'))]
            data = {
                'cnj_number': p['cnj'],
                'beneficiary_name': p['name'],
                'operator_name': 'Grupo Amil'
            }
            
            if use_test_client:
                res = client.post("/processes/upload", files=[('files', (os.path.basename(p['file']), file_bytes, 'application/pdf'))], data=data)
            else:
                res = requests.post(f"{BASE_URL}/processes/upload", files=[('files', (os.path.basename(p['file']), open(p['file'], 'rb'), 'application/pdf'))], data=data)
            
            if res.status_code != 200:
                print(f"  [ERRO] Upload falhou: {res.text}")
                continue
                
            res_data = res.json()
            proc_id = res_data.get('process_id')
            
            # Detalhes
            if use_test_client:
                det_res = client.get(f"/processes/{proc_id}")
            else:
                det_res = requests.get(f"{BASE_URL}/processes/{proc_id}")
            det_data = det_res.json() if det_res.status_code == 200 else {}

            verdict = res_data.get('verdict')
            summary = res_data.get('summary')
            theme = res_data.get('identified_theme')
            rules = res_data.get('rules', [])

            results.append({
                "id": p["id"],
                "cnj": p["cnj"],
                "beneficiary": p["name"],
                "expected_theme": p["theme"],
                "identified_theme": theme,
                "expected_verdict": p["expected"],
                "system_verdict": verdict,
                "summary": summary,
                "total_pages": res_data.get("total_pages"),
                "rules": rules,
                "pages_detail": det_data.get("pages", [])
            })
            print(f"  -> Veredito Sistema: {verdict} (Esperado: {p['expected']}) | Tema: {theme}")

    return results

if __name__ == "__main__":
    res = run_benchmark()
    with open("scratch/benchmark_results.json", "w", encoding="utf-8") as f:
        json.dump(res, f, ensure_ascii=False, indent=2)
    print("\n[OK] Benchmark concluído com sucesso!")
