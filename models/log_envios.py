# Archivo: models/log_envios.py
from beanie import Document
from pydantic import EmailStr
from datetime import datetime
from typing import Optional

class LogEnvio(Document):
    orden_id: str
    fecha_envio: datetime = datetime.utcnow()
    destinatario: EmailStr
    estado: str  # "Enviado" o "Error"
    error_msg: Optional[str] = None
    
    class Settings:
        name = "logs_envios"