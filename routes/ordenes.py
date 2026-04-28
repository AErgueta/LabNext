# Archivo: routes/ordenes.py
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from beanie import PydanticObjectId
import random
from models.orden import Orden, PacienteInfo
from services.generador_muestras import generar_tubos_para_orden
from models.estudio import Estudio
from services.evaluador import interpretar_resultado # Importamos nuestra Función Global
from utils.seguridad import verificar_token
from models.muestra import Muestra
from models.resultado import ResultadoMuestra

router = APIRouter()

# @router.post("/ordenes")
# async def crear_orden(orden: Orden, usuario: dict = Depends(verificar_token)):
#     # Al hacer .insert(), Beanie dispara el @before_event automáticamente
#     await orden.insert()
#     return {
#         "status": "success",
#         "numero_orden": orden.numero_orden,
#         "total_calculado": orden.total_pagado # Veremos si el trigger funcionó
#     }

@router.get("/ordenes/")
async def listar_ordenes():
    return await Orden.find_all().to_list()

# --- NUEVA RUTA PARA PROCESAR RESULTADOS ---

@router.post("/ordenes/{numero_orden}/resultados/{clave_analito}")
async def registrar_resultado(numero_orden: str, clave_analito: str, valor: float):
    # 1. Buscamos la orden del paciente en la base de datos
    orden = await Orden.find_one(Orden.numero_orden == numero_orden)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # 2. Buscamos el estudio en el catálogo (Para este ejemplo, tomamos el primero de la lista)
    codigo_estudio = orden.estudios_solicitados[0]
    estudio = await Estudio.find_one(Estudio.codigo_cups == codigo_estudio)

    # 3. Buscamos el analito específico (ej: "HGB") dentro del estudio
    for analito in estudio.analitos:
        if analito.clave_interfaz == clave_analito:
            
            # ¡AQUÍ OCURRE LA MAGIA! Llamamos a nuestro servicio externo
            diagnostico = interpretar_resultado(
                valor=valor,
                paciente_sexo=orden.paciente.sexo,
                paciente_edad=orden.paciente.edad_anos,
                rangos=analito.rangos
            )

            # Devolvemos el reporte consolidado
            return {
                "paciente": orden.paciente.nombre_completo,
                "examen": analito.nombre,
                "valor_ingresado": valor,
                "diagnostico_automatico": diagnostico
            }

    raise HTTPException(status_code=404, detail="Analito no encontrado")

# 1. EL MOLDE DE ENTRADA (Lo que le pedimos al Frontend)
class OrdenCreate(BaseModel):
    sede_id: PydanticObjectId
    paciente: PacienteInfo
    estudios_solicitados: List[str]
    medico_solicitante: str
    convenio: Optional[str] = None
    descuento_manual: float = 0.0

@router.post("/ordenes", response_model=dict)
async def crear_nueva_orden(
    datos: OrdenCreate,
    usuario_actual: dict = Depends(verificar_token)
):
    # 1. Validar que la orden tenga al menos un estudio
    if not datos.estudios_solicitados:
        raise HTTPException(status_code=400, detail="La orden debe tener al menos un estudio solicitado.")

    # 2. Generar el número de orden (Simulado temporalmente)
    # En producción esto será un correlativo real (Ej: ORD-26042026-001)
    nro_orden_generado = f"ORD-{random.randint(10000, 99999)}"

    # 3. Ensamblar la Orden con los datos del frontend
    nueva_orden = Orden(
        numero_orden=nro_orden_generado,
        sede_id=datos.sede_id,
        paciente=datos.paciente,
        estudios_solicitados=datos.estudios_solicitados,
        medico_solicitante=datos.medico_solicitante,
        convenio=datos.convenio,
        descuento_manual=datos.descuento_manual
    )

    # 4. GUARDAR EN BD (¡Aquí se detona tu @before_event automáticamente!)
    # Se calculará el total_pagado y la fecha_entrega_estimada
    await nueva_orden.insert()

    # 5. EL DISPARO LOGÍSTICO: Generar los tubos físicos
    try:
        tubos_generados = await generar_tubos_para_orden(nueva_orden, usuario_actual["username"])
    except Exception as e:
        # Si algo falla al generar los tubos, avisamos pero no borramos la orden
        raise HTTPException(status_code=500, detail=f"Orden creada, pero falló la logística: {str(e)}")

   # 6. Devolvemos un resumen completo al frontend
    return {
        "mensaje": "Orden y logística generadas con éxito",
        "orden": nueva_orden,
        "cantidad_tubos": len(tubos_generados),
        "tubos": [
            {
                "codigo": tubo.codigo_barras, 
                "tipo": tubo.tipo_muestra, 
                # Buscamos la observación dentro del primer evento del historial
                "seccion": tubo.historial_tracking[0].observaciones if tubo.historial_tracking else "Sin sección"
            } for tubo in tubos_generados
        ]
    }


@router.get("/{id}/expediente", response_model=dict)
async def obtener_expediente_completo(id: PydanticObjectId):
    # 1. Buscar la Orden
    orden = await Orden.get(id)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # 2. Buscar todos los tubos (Muestras) asociados a esta orden
    muestras = await Muestra.find(Muestra.orden_id == id).to_list()

    # 3. Buscar todos los resultados clínicos validados para esta orden
    resultados = await ResultadoMuestra.find(ResultadoMuestra.orden_id == id).to_list()

    # 4. Consolidar la respuesta final
    return {
        "paciente": orden.paciente,
        "detalles_orden": {
            "numero": orden.numero_orden,
            "fecha_creacion": orden.fecha_ingreso,
            "fecha_entrega": orden.fecha_entrega_estimada,
            "estado_pago": "Pagado" if orden.total_pagado > 0 else "Pendiente",
            "sede_id": str(orden.sede_id)
        },
        "logistica_muestras": [
            {
                "codigo": m.codigo_barras,
                "tipo": m.tipo_muestra,
                "estado_actual": m.estado_actual,
                "ultima_actualizacion": m.historial_tracking[-1].fecha_hora if m.historial_tracking else None
            } for m in muestras
        ],
        "reporte_clinico": [
            {
                "estudio": r.estudio_nombre,
                "fecha_validacion": r.fecha_procesamiento,
                "validado_por": r.bioquimico_validador,
                "analitos": r.resultados
            } for r in resultados
        ]
    }