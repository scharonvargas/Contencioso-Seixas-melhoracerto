"""
src/api/main.py
Ponto de entrada da API FastAPI do Seixas AI.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse, Response
from prometheus_client import make_asgi_app
from src.core.config import settings
from src.core.database import init_db
from src.api.routes import processes, policies, hitl
from pathlib import Path

# Inicializa banco de dados e migrações
init_db()

app = FastAPI(
    title=settings.PROJECT_NAME,
    version="1.0.0",
    description="API de Validação Automatizada de Acordos de Reembolso em Saúde com Base em Norma Interna"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Exportador de métricas Prometheus
metrics_app = make_asgi_app()
app.mount("/metrics", metrics_app)

# Registro de Rotas da API
app.include_router(processes.router)
app.include_router(policies.router)
app.include_router(hitl.router)

@app.get("/health", tags=["Infraestrutura"])
async def health_check():
    return {
        "status": "healthy",
        "service": settings.PROJECT_NAME,
        "environment": settings.ENVIRONMENT
    }

# Servidor de Frontend SPA limpo e sem colisão com rotas de API
frontend_dir = Path(__file__).resolve().parent.parent.parent / "frontend"

@app.get("/", tags=["Frontend"])
@app.get("/index.html", tags=["Frontend"])
async def serve_frontend():
    index_file = frontend_dir / "index.html"
    if index_file.exists():
        return FileResponse(str(index_file))
    return Response(content="Seixas AI API em execução.", media_type="text/plain")

@app.get("/favicon.ico", include_in_schema=False)
async def favicon():
    svg_icon = """<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><text y='.9em' font-size='90'>⚖️</text></svg>"""
    return Response(content=svg_icon, media_type="image/svg+xml")

if frontend_dir.exists():
    app.mount("/static", StaticFiles(directory=str(frontend_dir)), name="static")
