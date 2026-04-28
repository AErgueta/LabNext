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
    # Estructura del diccionario: { ("Suero", "Química"): ["Glucosa", "Colesterol"], ... }
    tubos_necesarios = {}

    for nombre_estudio in orden.estudios_solicitados:
        estudio_db = await Estudio.find_one(Estudio.nombre_estudio == nombre_estudio)
        if estudio_db:
            # Creamos la clave compuesta (Ej: "Suero" - "Química")
            clave_agrupacion = (estudio_db.muestra, estudio_db.seccion)
            
            if clave_agrupacion not in tubos_necesarios:
                tubos_necesarios[clave_agrupacion] = []
            
            tubos_necesarios[clave_agrupacion].append(estudio_db.nombre_estudio)

    # 2. Determinar el Flujo Logístico (¡Usando tu lógica de Sedes!)
    sede_origen = await Sede.get(orden.sede_id)
    
    # Buscamos los IDs de los flujos en la BD (Asumiendo que los buscamos por nombre)
    if sede_origen and sede_origen.es_procesadora:
        flujo = await FlujoMuestra.find_one(FlujoMuestra.nombre_flujo == "Flujo Local (Sede Única)")
    else:
        flujo = await FlujoMuestra.find_one(FlujoMuestra.nombre_flujo == "Flujo Estándar")
        
    if not flujo:
        raise ValueError("No se encontraron los flujos de configuración en la base de datos")

    # 3. Crear físicamente las Muestras en la BD
    muestras_creadas = []
    
    for (tipo_muestra, seccion), lista_estudios in tubos_necesarios.items():
        # Generar un código único
        codigo_generado = f"MUE-{random.randint(10000, 99999)}"
        
        # El evento inicial
        evento_inicial = EventoTracking(
            estado="Recolectada",
            fecha_hora=datetime.now(),
            usuario=usuario_creador,
            sede_id=orden.sede_id,
            observaciones=f"Tubo generado para la sección: {seccion}"
        )
        
        # Ensamblar el tubo
        nueva_muestra = Muestra(
            codigo_barras=codigo_generado,
            orden_id=orden.id, 
            flujo_id=flujo.id,
            tipo_muestra=tipo_muestra,
            estado_actual="Recolectada",
            historial_tracking=[evento_inicial]
        )
        
        await nueva_muestra.insert()
        muestras_creadas.append(nueva_muestra)
        
    return muestras_creadas