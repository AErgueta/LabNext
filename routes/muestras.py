# Archivo: routes/muestras.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from beanie import PydanticObjectId
from datetime import datetime
import random # Lo usaremos temporalmente para generar un código al azar

from models.muestra import Muestra, EventoTracking
from models.flujo_muestra import FlujoMuestra
# Asegúrate de que esta ruta coincida con donde tienes tu archivo de seguridad
from utils.seguridad import verificar_token 

router = APIRouter()

# Este es el "molde" de lo que el frontend nos debe enviar
class MuestraCreate(BaseModel):
    orden_id: PydanticObjectId
    flujo_id: PydanticObjectId
    tipo_muestra: str # Ej: "Suero", "Orina"
    sede_id: PydanticObjectId # En qué sucursal están tomando la muestra

@router.post("/", response_model=Muestra)
async def registrar_nueva_muestra(
    datos: MuestraCreate,
    usuario_actual: dict = Depends(verificar_token) # <-- ¡MAGIA! Sacamos al usuario del token
):
    # 1. Validar que el flujo que nos envían realmente existe
    flujo = await FlujoMuestra.get(datos.flujo_id)
    if not flujo:
        raise HTTPException(status_code=404, detail="El flujo configurado no existe")

    # 2. Generar el Código de Barras Único (Simulado por ahora)
    # En un futuro lo haremos secuencial (Ej: MUE-2026-00001)
    codigo_generado = f"MUE-{random.randint(10000, 99999)}"

    # 3. Crear el primer evento de la huella de auditoría
    evento_inicial = EventoTracking(
        estado="Recolectada", 
        fecha_hora=datetime.now(),
        usuario=usuario_actual["username"], # Queda registrado quién hizo el clic
        sede_id=datos.sede_id,
        observaciones="Toma de muestra inicial en recepción"
    )

    # 4. Ensamblar el tubo físico
    nueva_muestra = Muestra(
        codigo_barras=codigo_generado,
        orden_id=datos.orden_id,
        flujo_id=datos.flujo_id,
        tipo_muestra=datos.tipo_muestra,
        estado_actual="Recolectada",
        historial_tracking=[evento_inicial]
    )

    # 5. Guardar en la base de datos
    await nueva_muestra.insert()
    
    return nueva_muestra