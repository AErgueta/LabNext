# Archivo: routes/resultados.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from typing import Dict
from beanie import PydanticObjectId

from models.muestra import Muestra, EventoTracking
from models.orden import Orden
from models.estudio import Estudio
from models.resultado import ResultadoMuestra
from services.validador_clinico import procesar_resultados_estudio
from utils.seguridad import verificar_token
from datetime import datetime

router = APIRouter()

# 1. EL MOLDE DE ENTRADA (Lo que envía la Máquina o el Frontend)
class ResultadoCreate(BaseModel):
    muestra_id: PydanticObjectId
    estudio_nombre: str
    valores: Dict[str, float]  # Ej: {"Glucosa Basal": 115.0, "Colesterol Total": 210.5}

@router.post("/", response_model=dict)
async def registrar_resultados(
    datos: ResultadoCreate,
    usuario_actual: dict = Depends(verificar_token)
):
    # 1. Validar que el tubo (Muestra) exista físicamente
    muestra_db = await Muestra.get(datos.muestra_id)
    if not muestra_db:
        raise HTTPException(status_code=404, detail="El tubo especificado no existe.")

    # 2. Buscar la Orden original para obtener la EDAD y SEXO del paciente
    orden_db = await Orden.get(muestra_db.orden_id)
    if not orden_db:
        raise HTTPException(status_code=404, detail="No se encontró la orden asociada a esta muestra.")

    # 3. Buscar las reglas del catálogo para este estudio
    estudio_db = await Estudio.find_one(Estudio.nombre_estudio == datos.estudio_nombre)
    if not estudio_db:
        raise HTTPException(status_code=404, detail=f"El estudio {datos.estudio_nombre} no existe en el catálogo.")

    # 4. EL CEREBRO CLÍNICO: Cruzar los valores crudos con los rangos
    # Aquí le pasamos la edad y sexo que sacamos del paciente en el paso 2
    detalles_clinicos = procesar_resultados_estudio(
        estudio_db=estudio_db,
        valores_enviados=datos.valores,
        edad_paciente=orden_db.paciente.edad_anos,
        sexo_paciente=orden_db.paciente.sexo
    )

    if not detalles_clinicos:
        raise HTTPException(status_code=400, detail="No se pudo procesar ningún analito con los valores enviados.")

    # 5. Guardar la "Fotografía Legal" del resultado
    nuevo_resultado = ResultadoMuestra(
        muestra_id=muestra_db.id,
        orden_id=orden_db.id,
        estudio_nombre=datos.estudio_nombre,
        resultados=detalles_clinicos,
        bioquimico_validador=usuario_actual["username"]
    )
    await nuevo_resultado.insert()

    # 6. Actualizar el Tracking Logístico (El tubo ya se procesó)
    evento_procesado = EventoTracking(
        estado="Procesada",
        fecha_hora=datetime.now(),
        usuario=usuario_actual["username"],
        sede_id=orden_db.sede_id,
        observaciones=f"Resultados validados para {datos.estudio_nombre}"
    )
    muestra_db.estado_actual = "Procesada"
    muestra_db.historial_tracking.append(evento_procesado)
    await muestra_db.save()

    # 7. Respuesta de éxito
    return {
        "mensaje": "Resultados procesados y validados con éxito",
        "alertas": any(detalle.fuera_de_rango for detalle in detalles_clinicos), # Avisa rápido si hay algo anormal
        "resultado_id": str(nuevo_resultado.id),
        "detalles": detalles_clinicos
    }