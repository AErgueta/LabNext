# Archivo: services/generador_muestras.py
from datetime import datetime
import random
from beanie import PydanticObjectId
from models.orden import Orden
from models.estudio import Estudio
from models.muestra import Muestra, EventoTracking
from models.sede import Sede
from models.flujo_muestra import FlujoMuestra

async def generar_tubos_para_orden(orden: Orden, usuario_creador: str):
    """
    Lee una orden recién creada, agrupa los estudios por (Muestra + Sección)
    y genera los tubos físicos necesarios en la base de datos.
    """
    
    # 1. Agrupar los estudios solicitados
    tubos_necesarios = {}

    for estudio_id in orden.estudios_solicitados:
        # Buscamos el estudio por su ID real
        estudio_db = await Estudio.get(PydanticObjectId(estudio_id))
        
        if estudio_db:
            clave_agrupacion = (estudio_db.muestra, estudio_db.seccion)
            
            if clave_agrupacion not in tubos_necesarios:
                tubos_necesarios[clave_agrupacion] = []
            
            tubos_necesarios[clave_agrupacion].append(estudio_db.nombre_estudio)

    if not tubos_necesarios:
        raise ValueError("No se encontraron los estudios solicitados en la base de datos.")

    # 2. Determinar el Flujo Logístico
    # Extraemos el ID de la sede de forma segura
    id_sede_orden = PydanticObjectId(orden.sede_id)
    sede_origen = await Sede.get(id_sede_orden)
    
    if sede_origen and sede_origen.es_procesadora:
        flujo = await FlujoMuestra.find_one(FlujoMuestra.nombre_flujo == "Flujo Local (Sede Única)")
    else:
        flujo = await FlujoMuestra.find_one(FlujoMuestra.nombre_flujo == "Flujo Estándar")
        
    if not flujo:
        raise ValueError("No se encontraron los flujos de configuración en la base de datos.")

    # 3. Crear físicamente las Muestras en la BD
    muestras_creadas = []
    
    # Extraemos los IDs limpios fuera del bucle para evitar conflictos de serialización
    id_orden_puro = PydanticObjectId(orden.id)
    id_flujo_puro = PydanticObjectId(flujo.id)
    id_sede_puro = PydanticObjectId(orden.sede_id)
    
    for (tipo_muestra, seccion), lista_estudios in tubos_necesarios.items():
        codigo_generado = f"MUE-{random.randint(10000, 99999)}"
        
        # El evento inicial con los IDs limpios
        evento_inicial = EventoTracking(
            estado="Pendiente",
            fecha_hora=datetime.now(),
            usuario=usuario_creador,
            sede_id=id_sede_puro,
            observaciones=f"Tubo generado para la sección: {seccion}"
        )
        
        # Ensamblar el tubo con IDs explícitamente convertidos
        nueva_muestra = Muestra(
            codigo_barras=codigo_generado,
            orden_id=id_orden_puro,
            flujo_id=id_flujo_puro,
            tipo_muestra=tipo_muestra,
            estado_actual="Pendiente",
            historial_tracking=[evento_inicial]
        )
        
        await nueva_muestra.insert()
        muestras_creadas.append(nueva_muestra)
        
    return muestras_creadas