from pydantic import BaseModel

# Nuevo modelo para que el usuario elija el flujo por tipo de muestra
class ConfiguracionTubo(BaseModel):
    tipo_muestra: str
    flujo_id: str  # El ID del flujo seleccionado por el usuario en el combo de la interfaz