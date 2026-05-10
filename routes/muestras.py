# Archivo: routes/muestras.py
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from beanie import PydanticObjectId
from datetime import datetime
import random # Lo usaremos temporalmente para generar un código al azar

from models.muestra import Muestra, EventoTracking
from models.orden import Orden
from models.resultado import ResultadoMuestra, ResultadoDetalle
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

class DatoEntradaAnalito(BaseModel):
    analito: str
    valor_leido: float
    unidad_medida: str
    estado_clinico: str
    rango_aplicado: str
    fuera_de_rango: bool

class RegistroResultados(BaseModel):
    codigo_barras: str
    estudio_nombre: str
    resultados: List[DatoEntradaAnalito]

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


@router.get("/monitor-trabajo", response_model=dict)
async def obtener_monitor_trabajo(usuario_actual: dict = Depends(verificar_token)):
    # 1. Filtro de Seguridad: Solo personal autorizado
    if usuario_actual["rol"] not in ["Admin", "Bioquimico"]:
        raise HTTPException(
            status_code=403, 
            detail="Acceso denegado. Solo el personal clínico puede ver el monitor de trabajo."
        )

    # 2. Buscar todos los tubos que aún NO están terminados
    tubos_pendientes = await Muestra.find(
        Muestra.estado_actual != "Procesada"
    ).to_list()

    # 3. Formatear la lista para la vista del monitor
    vista_monitor = []
    # ... código anterior (filtro de seguridad y búsqueda de tubos) ...

    # Formatear la lista cruzando datos con la Orden
    vista_monitor = []
    for tubo in tubos_pendientes:
        
        # PASO NUEVO: Usamos el orden_id del tubo para traer la Orden completa de la BD
        orden_madre = await Orden.get(tubo.orden_id)
        
        # PASO NUEVO: Extraemos los estudios de la orden (si la orden existe)
        # OJO: Aquí asumo que en tu models/orden.py el campo se llama "estudios"
        lista_estudios = orden_madre.estudios_solicitados if orden_madre else []

        vista_monitor.append({
            "muestra_id": str(tubo.id),
            "codigo_barras": tubo.codigo_barras,
            "tipo_tubo": tubo.tipo_muestra,
            "estudios_solicitados": lista_estudios, # ¡Le devolvemos los ojos al técnico!
            "estado_actual": tubo.estado_actual,
            "fecha_ingreso": tubo.historial_tracking[0].fecha_hora if tubo.historial_tracking else None
        })

    return {
        "usuario_operador": usuario_actual["username"],
        "total_tubos_pendientes": len(vista_monitor),
        "lista_trabajo": vista_monitor
    }

@router.post("/resultados", response_model=dict)
async def guardar_resultados(datos: RegistroResultados, usuario_actual: dict = Depends(verificar_token)):
    # 1. Filtro de Seguridad
    if usuario_actual["rol"] not in ["Admin", "Bioquimico"]:
        raise HTTPException(status_code=403, detail="Acceso denegado. Solo personal clínico.")

    # 2. Buscar la Muestra en Logística
    tubo = await Muestra.find_one(Muestra.codigo_barras == datos.codigo_barras)
    if not tubo:
        raise HTTPException(status_code=404, detail="Muestra no encontrada")
        
    if tubo.estado_actual == "Procesada":
        raise HTTPException(status_code=400, detail="Esta muestra ya fue procesada anteriormente")

    # 3. Preparar la lista de analitos usando tu modelo ResultadoDetalle
    detalles = []
    for res in datos.resultados:
        detalles.append(ResultadoDetalle(
            analito=res.analito,
            valor_leido=res.valor_leido,
            unidad_medida=res.unidad_medida,
            estado_clinico=res.estado_clinico,
            rango_aplicado=res.rango_aplicado,
            fuera_de_rango=res.fuera_de_rango
        ))

    # 4. Crear el documento en la colección resultados_clinicos
    nuevo_resultado = ResultadoMuestra(
        muestra_id=tubo.id,
        orden_id=tubo.orden_id, # Usamos el vínculo directo desde el tubo
        estudio_nombre=datos.estudio_nombre,
        resultados=detalles,
        bioquimico_validador=usuario_actual["username"] # Sello automático del bioquímico logueado
    )
    await nuevo_resultado.insert() # Aquí la magia: se guarda en su propia colección

    # 5. Actualizar la logística de la Muestra
    tubo.estado_actual = "Procesada"
    sede_origen = tubo.historial_tracking[0].sede_id if tubo.historial_tracking else tubo.orden_id
    
    nuevo_evento = EventoTracking(
        estado="Procesada",
        usuario=usuario_actual["username"],
        sede_id=sede_origen, 
        observaciones=f"Resultados de {datos.estudio_nombre} validados"
    )
    tubo.historial_tracking.append(nuevo_evento)
    await tubo.save()

    return {
        "status": "success",
        "message": f"Resultados guardados correctamente. Muestra {tubo.codigo_barras} marcada como Procesada."
    }

@router.get("/resultados/orden/{orden_id}")
async def obtener_resultados_orden(orden_id: PydanticObjectId, usuario_actual: dict = Depends(verificar_token)):
    
    # 1. Filtro de Seguridad: Usamos la variable para restringir quién puede ver resultados médicos
    roles_permitidos = ["Admin", "Bioquimico", "Secretaria", "Medico"] # Ajusta estos roles según tu sistema
    if usuario_actual["rol"] not in roles_permitidos:
        raise HTTPException(status_code=403, detail="No tienes permisos para ver resultados médicos.")

    # 2. Validar la existencia de la orden madre
    orden = await Orden.get(orden_id)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden médica no encontrada")
        
    # 3. Buscar todos los resultados vinculados a ese ID
    lista_resultados = await ResultadoMuestra.find(ResultadoMuestra.orden_id == orden_id).to_list()
    
    # 4. Retornar el paquete consolidado
    return {
        "numero_orden": orden.numero_orden,
        "paciente": orden.paciente,
        "medico": orden.medico_solicitante,
        "total_estudios_procesados": len(lista_resultados),
        "detalle_resultados": lista_resultados
    }