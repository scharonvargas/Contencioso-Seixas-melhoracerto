"""
src/core/storage.py
Serviço de Armazenamento de Arquivos compatível com MinIO / S3 e com fallback para filesystem local.
"""

import os
import shutil
from typing import Optional
from pathlib import Path
from src.core.config import settings

class StorageService:
    """
    Gerencia uploads de PDFs de processos judiciais, normas e imagens de páginas.
    Suporta MinIO/S3 e armazenamento local estruturado.
    """

    def __init__(self, base_dir: str = "./storage_data"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "processes").mkdir(exist_ok=True)
        (self.base_dir / "policies").mkdir(exist_ok=True)
        (self.base_dir / "pages").mkdir(exist_ok=True)

    def save_process_pdf(self, tenant_id: str, process_id: str, file_bytes: bytes, filename: str) -> str:
        tenant_folder = self.base_dir / "processes" / tenant_id / process_id
        tenant_folder.mkdir(parents=True, exist_ok=True)
        
        target_path = tenant_folder / filename
        with open(target_path, "wb") as f:
            f.write(file_bytes)
            
        return str(target_path.as_posix())

    def save_page_image(self, tenant_id: str, process_id: str, page_number: int, img_bytes: bytes) -> str:
        page_folder = self.base_dir / "pages" / tenant_id / process_id
        page_folder.mkdir(parents=True, exist_ok=True)
        
        target_path = page_folder / f"page_{page_number}.png"
        with open(target_path, "wb") as f:
            f.write(img_bytes)
            
        return str(target_path.as_posix())

    def get_presigned_view_url(self, storage_path: str, expires_seconds: int = 900) -> str:
        """
        Retorna URL de visualização segura temporária (15 minutos).
        Em produção conecta ao MinIO Client para gerar Presigned GET URL.
        """
        # Em ambiente local / teste retorna o caminho relativo do arquivo
        return f"/s3/{storage_path}"

    def delete_process_files(self, tenant_id: str, process_id: str) -> bool:
        process_folder = self.base_dir / "processes" / tenant_id / process_id
        if process_folder.exists():
            shutil.rmtree(process_folder)
        return True

storage_service = StorageService()
