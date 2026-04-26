# Archivo: models/medico.py
from beanie import Document
from typing import Optional

class Medico(Document):
    nombre_completo: str
    especialidad: str
    matricula_profesional: str
    telefono: Optional[str] = None

    class Settings:
        name = "catalogo_medicos"