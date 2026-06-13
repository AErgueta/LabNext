# Archivo: routes/ordenes.py
from fastapi import APIRouter, HTTPException, Depends, status, BackgroundTasks
from fastapi.responses import Response
from weasyprint import HTML
from jinja2 import Environment, FileSystemLoader
from pydantic import BaseModel
from typing import List, Optional
from beanie import PydanticObjectId
import random
from models.orden import Orden, PacienteInfo
from services.generador_muestras import generar_tubos_para_orden
from services.notificaciones import enviar_correo_resultados
from models.estudio import Estudio
from services.evaluador import interpretar_resultado # Importamos nuestra Función Global
from utils.seguridad import verificar_token
from models.muestra import Muestra
from models.resultado import ResultadoMuestra
from bson import ObjectId
from datetime import datetime
from models.usuario import Usuario

from schemas.ordenes import ConfiguracionTubo

# router = APIRouter()
router = APIRouter(prefix="/ordenes", tags=["Órdenes"])

# @router.post("/ordenes")
# async def crear_orden(orden: Orden, usuario: dict = Depends(verificar_token)):
#     # Al hacer .insert(), Beanie dispara el @before_event automáticamente
#     await orden.insert()
#     return {
#         "status": "success",
#         "numero_orden": orden.numero_orden,
#         "total_calculado": orden.total_pagado # Veremos si el trigger funcionó
#     }

@router.get("/")
async def listar_ordenes():
    return await Orden.find_all().to_list()

# --- NUEVA RUTA PARA PROCESAR RESULTADOS ---

@router.post("/{numero_orden}/resultados/{clave_analito}")
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

@router.post("/", response_model=dict)
async def crear_nueva_orden(
    datos: OrdenCreate,
    usuario_actual: dict = Depends(verificar_token)
):
    # 1. Validar que la orden tenga al menos un estudio
    if not datos.estudios_solicitados:
        raise HTTPException(status_code=400, detail="La orden debe tener al menos un estudio solicitado.")

    # --- NUEVO ESCUDO DE SEGURIDAD ---
    # 1.5. Validar que el paciente tenga un correo válido
    if not datos.paciente.email:
        raise HTTPException(
            status_code=400, 
            detail=f"El paciente {datos.paciente.nombre_completo} no tiene un correo registrado. Actualice sus datos en recepción antes de crear la orden."
        )
    # ---------------------------------

    # 2. Generar el número de orden (Simulado temporalmente)
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

    # 4. GUARDAR EN BD 
    await nueva_orden.insert()

    # 5. EL DISPARO LOGÍSTICO: Generar los tubos físicos
    try:
        tubos_generados = await generar_tubos_para_orden(nueva_orden, usuario_actual["username"])
    except Exception as e:
        print(f"DEBUG ERROR: {str(e)}")
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
                "seccion": tubo.historial_tracking[0].observaciones if tubo.historial_tracking else "Sin sección"
            } for tubo in tubos_generados
        ]
    }

@router.get("/{orden_id}/expediente", response_model=dict)
async def obtener_expediente_completo(orden_id: PydanticObjectId):
    # 1. Buscar la Orden
    orden = await Orden.get(orden_id)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # 2. Buscar todos los tubos (Muestras) asociados a esta orden
    muestras = await Muestra.find(Muestra.orden_id == orden_id).to_list()

    # 3. Buscar todos los resultados clínicos validados para esta orden
    resultados = await ResultadoMuestra.find(ResultadoMuestra.orden_id == orden_id).to_list()

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

@router.post("/{orden_id}/generar_tubos")
async def endpoint_generar_tubos_manual(
    orden_id: str, 
    configuraciones: List[ConfiguracionTubo], # <--- Recibimos la elección del usuario
    usuario_actual: dict = Depends(verificar_token)
):
    # 1. Buscamos la orden
    orden = await Orden.get(orden_id)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # 2. Extraemos el usuario del token (nuestro arreglo de ayer)
    identificador_usuario = usuario_actual.get("sub") or "Sistema"
    fecha_corta = datetime.now().strftime("%y%m%d")
    
    tubos_generados = []
    correlativo = 1

    # 3. Iteramos sobre lo que el usuario configuró manualmente
    for config in configuraciones:
        # Generamos el código de barras (ej. 240520-396-1)
        codigo_barras = f"{fecha_corta}-{orden.numero_orden[-3:]}-{correlativo}"
        
        # Creamos la instancia de Muestra (UNA POR CADA VUELTA)
        nuevo_tubo = Muestra(
            codigo_barras=codigo_barras,
            orden_id=orden.id,
            flujo_id=ObjectId(config.flujo_id), # <--- ¡DINÁMICO! Usamos lo que envió el usuario
            tipo_muestra=config.tipo_muestra,
            estado_actual="Recolectada",
            historial_tracking=[
                {
                    "estado": "Recolectada",
                    "fecha_hora": datetime.now(),
                    "usuario": identificador_usuario,
                    "sede_id": orden.sede_id,
                    "observaciones": "Tubo generado con flujo elegido por el usuario."
                }
            ]
        )
        
        await nuevo_tubo.insert()
        tubos_generados.append(nuevo_tubo)
        correlativo += 1

    return {
            "status": "success",
            "message": f"Se generaron {len(tubos_generados)} tubos para impresión",
            "paciente": orden.paciente.nombre_completo,
            "tubos": tubos_generados
        }

# Configuración de Jinja2 para cargar tu HTML
env = Environment(loader=FileSystemLoader("templates"))

@router.get("/{orden_id}/reporte", tags=["Reportes"])
async def generar_reporte_pdf(orden_id: str):
    # 1. Convertir el string a ObjectId para Beanie
    try:
        orden_oid = PydanticObjectId(orden_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de orden inválido.")

    # 2. Buscar la Orden
    orden_db = await Orden.get(orden_oid)
    if not orden_db:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    # 3. Buscar todos los resultados validados para esta orden
    # Asumiendo que tu modelo ResultadoMuestra tiene un campo orden_id
    resultados_db = await ResultadoMuestra.find(ResultadoMuestra.orden_id == orden_oid).to_list()

    if not resultados_db:
        raise HTTPException(status_code=400, detail="Esta orden aún no tiene resultados procesados para imprimir.")

    # 4. Cargar la plantilla HTML y pasarle los datos
    template = env.get_template("reporte_paciente.html")
    html_renderizado = template.render(
        orden=orden_db,
        resultados=resultados_db
    )

    # 5. Magia: Convertir HTML a PDF con WeasyPrint
    pdf_bytes = HTML(string=html_renderizado).write_pdf()

    # 6. Enviar el archivo binario al navegador
    return Response(
        content=pdf_bytes, 
        media_type="application/pdf",
        headers={"Content-Disposition": f"inline; filename=Reporte_LabNext_{orden_db.numero_orden}.pdf"}
    )


@router.put("/{orden_id}/revertir-validacion", tags=["Validación Clínica"])
async def revertir_validacion_orden(
    orden_id: str, 
    usuario_actual: dict = Depends(verificar_token)
):
    # 1. Extraemos el rol de forma segura desde el Token
    rol_token = usuario_actual.get("rol")

    # 2. Control de Accesos: Solo Validadores (o Administradores) pueden deshacer esto
    if rol_token not in ["BioquimicoValidador", "Admin"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN, 
            detail="No tienes permisos para revertir validaciones clínicas."
        )

    # 3. Validamos el ID de la orden
    try:
        orden_oid = PydanticObjectId(orden_id)
    except Exception:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="ID de orden inválido.")

    # 4. Buscar la Orden
    orden_db = await Orden.get(orden_oid)
    if not orden_db:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Orden no encontrada.")

    # 5. Reglas de Negocio: Solo se puede revertir si está actualmente Validada
    if getattr(orden_db, "estado", "") != "Validada":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, 
            detail=f"No se puede revertir. La orden está en estado: '{orden_db.estado}'."
        )

    # 6. RETROCEDER EL ESTADO Y LIMPIAR LA FIRMA
    orden_db.estado = "Procesada"  # La devolvemos a la fase previa
    orden_db.bioquimico_validador = None
    orden_db.fecha_validacion = None

    # 7. Persistir cambios
    await orden_db.save()

    return {
        "status": "success",
        "mensaje": "Validación revertida. La orden vuelve a estar disponible para modificaciones.",
        "orden": orden_db.numero_orden,
        "nuevo_estado": orden_db.estado
    }

@router.post("/{orden_id}/validar", tags=["Validación Clínica"])
async def validar_resultados_orden(
    orden_id: str,
    background_tasks: BackgroundTasks,
    usuario_actual: dict = Depends(verificar_token)
):
    username_token = usuario_actual.get("username")
    rol_token = usuario_actual.get("rol")

    # 1. Validar el ID
    try:
        orden_oid = PydanticObjectId(orden_id)
    except Exception:
        raise HTTPException(status_code=400, detail="ID de orden inválido.")

    # 2. Buscar la Orden
    orden_db = await Orden.get(orden_oid)
    if not orden_db:
        raise HTTPException(status_code=404, detail="Orden no encontrada.")

    if getattr(orden_db, "estado", "") == "Validada":
        raise HTTPException(status_code=400, detail="Esta orden ya fue validada anteriormente.")

    if rol_token != "BioquimicoValidador":
        raise HTTPException(status_code=403, detail="No tienes permisos de validación clínica.")

    # 3. Buscar al usuario validador
    validador = await Usuario.find_one(Usuario.username == username_token)
    if not validador:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    # 4. --- NUEVO: BUSCAR RESULTADOS Y GENERAR PDF ---
    resultados_db = await ResultadoMuestra.find(ResultadoMuestra.orden_id == orden_oid).to_list()
    if not resultados_db:
        raise HTTPException(status_code=400, detail="No se puede validar ni enviar correo: La orden no tiene resultados cargados.")

    # Renderizar plantilla y crear PDF en memoria (Bytes)
    template = env.get_template("reporte_paciente.html")
    html_renderizado = template.render(
        orden=orden_db,
        resultados=resultados_db
    )
    pdf_generado_bytes = HTML(string=html_renderizado).write_pdf()

    # 5. Estampar la firma en BD
    orden_db.estado = "Validada"
    orden_db.bioquimico_validador = validador.nombre_completo
    orden_db.fecha_validacion = datetime.utcnow()
    await orden_db.save()

    # 6. --- DISPARAR EL CORREO CON EL PDF ADJUNTO ---
    # email_paciente = "aerguetab@live.com"  
    # nombre_paciente = "Paciente de Prueba"
    nombre_paciente = orden_db.paciente.nombre_completo 
    email_paciente = orden_db.paciente.email

    if not email_paciente:
            print(f" LOG: El paciente {nombre_paciente} no tiene correo registrado. Se omitirá el envío.")
            # Aquí le ponemos tu correo temporalmente para que no truene, 
            # o puedes decidir no encolar la tarea (background_tasks.add_task) si está vacío.
            email_paciente = "aerguetab@live.com"

    background_tasks.add_task(
        enviar_correo_resultados,
        email_destino=email_paciente,
        nombre_paciente=nombre_paciente,
        numero_orden=orden_db.numero_orden,
        pdf_bytes=pdf_generado_bytes # <--- ¡Aquí le pasamos el archivo físico!
    )

    return {
        "status": "success",
        "mensaje": "Resultados validados. El reporte en PDF está siendo enviado al paciente.",
        "orden": orden_db.numero_orden
    }