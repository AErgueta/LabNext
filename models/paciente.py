# Archivo: models/paciente.py
from beanie import Document, Indexed, Link
from pydantic import EmailStr, Field
from datetime import datetime
from typing import Optional, Annotated 
from models.convenio import Convenio

class Paciente(Document):
    ci: Annotated[str, Indexed(unique=True)]
    nombre_completo: str
    fecha_nacimiento: datetime
    sexo: str  # "M" o "F"
    
    telefono: Optional[str] = None
    email: Optional[EmailStr] = None  # <-- Cambiado a Optional para evitar fallos si viene vacío
    
    tipo_paciente_default: str = "Particular" 
    convenio_predeterminado: Optional[Link[Convenio]] = None
    
    fecha_registro: Annotated[datetime, Field(default_factory=datetime.now)] = Field(default_factory=datetime.now)

    class Settings:
        name = "pacientes"