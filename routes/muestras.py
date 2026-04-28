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
from typing import Optional, List

router = APIRouter()

# Este es el "molde" de lo que el frontend nos debe enviar
class MuestraCreate(BaseModel):
    orden_id: PydanticObjectId
    flujo_id: PydanticObjectId
    tipo_muestra: str # Ej: "Suero", "Orina"
    sede_id: PydanticObjectId # En qué sucursal están tomando la muestra

class AvanceMuestra(BaseModel):
    nuevo_estado: str
    sede_id: PydanticObjectId # En qué sede física le hicieron el escaneo
    observaciones: Optional[str] = None

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


@router.post("/{codigo_barras}/avanzar", response_model=Muestra)
async def avanzar_estado_muestra(
    codigo_barras: str,
    datos: AvanceMuestra,
    usuario_actual: dict = Depends(verificar_token)
):
    # 1. Buscar el tubo físico en la BD
    muestra = await Muestra.find_one(Muestra.codigo_barras == codigo_barras)
    if not muestra:
        raise HTTPException(status_code=404, detail="Muestra no encontrada")

    # 2. Buscar el mapa de reglas (Flujo)
    flujo = await FlujoMuestra.get(muestra.flujo_id)

    # 3. EL CANDADO LÓGICO: ¿Está permitido este movimiento?
    transiciones_permitidas = flujo.transiciones_validas.get(muestra.estado_actual, [])
    if datos.nuevo_estado not in transiciones_permitidas:
        raise HTTPException(
            status_code=400, 
            detail=f"Movimiento ilegal. No puedes pasar de '{muestra.estado_actual}' a '{datos.nuevo_estado}'."
        )

    # --- 3.5. NUEVO: LA REGLA ESTRICTA DE RECHAZO ---
    # Si intentan rechazarla y el campo observaciones está vacío o no existe (None)
    if datos.nuevo_estado == "Rechazada" and not datos.observaciones:
        raise HTTPException(
            status_code=422, # Unprocessable Entity
            detail="Operación bloqueada. Es obligatorio explicar el motivo del rechazo en el campo 'observaciones' (Ej: Muestra coagulada)."
        )
    # ------------------------------------------------

    # 4. Crear el nuevo registro de auditoría
    nuevo_evento = EventoTracking(
        estado=datos.nuevo_estado,
        usuario=usuario_actual["username"],
        sede_id=datos.sede_id,
        observaciones=datos.observaciones
    )

    # 5. La Inserción en MongoDB
    muestra.historial_tracking.append(nuevo_evento)
    muestra.estado_actual = datos.nuevo_estado      
    
    await muestra.save()

    return muestra

@router.get("/", response_model=List[Muestra])
async def listar_muestras(
    estado: Optional[str] = None,
    orden_id: Optional[PydanticObjectId] = None,
    # El guardia sigue vigilando quién pide esta información
    usuario_actual: dict = Depends(verificar_token) 
):
    # 1. Preparamos los filtros vacíos
    filtros = {}
    
    # 2. Si el frontend nos pide un estado específico, lo agregamos al filtro
    if estado:
        filtros["estado_actual"] = estado
        
    # 3. Si el frontend busca una orden específica, también filtramos por eso
    if orden_id:
        filtros["orden_id"] = orden_id

    # 4. Buscamos en la base de datos aplicando los filtros
    # Si no mandan ningún filtro, devolverá todas las muestras
    muestras = await Muestra.find(filtros).to_list()
    
    return muestras