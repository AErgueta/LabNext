# Archivo: models/convenio.py
from beanie import Document
from typing import Optional

class Convenio(Document):
    nombre: str
    tipo: str # Opciones: "Seguro" o "Empresa"
    
    # --- LÓGICA PARA SEGUROS ---
    # Ej: Paciente paga 0.30 (30%) y el Seguro paga 0.70 (70%)
    porcentaje_copago_paciente: Optional[float] = 0.0
    porcentaje_cobertura_seguro: Optional[float] = 0.0
    
    # --- LÓGICA PARA EMPRESAS/CLÍNICAS ---
    # Ej: 0.20 (20% de descuento directo al total)
    porcentaje_descuento: Optional[float] = 0.0

    class Settings:
        name = "catalogo_convenios"