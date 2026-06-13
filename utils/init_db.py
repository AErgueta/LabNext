# Archivo recomendado: utils/init_db.py o dentro de tu flujo de arranque en main.py
from models.flujo_muestra import FlujoMuestra

async def verificar_y_actualizar_flujos():
    """
    Garantiza que los flujos logísticos existan en la base de datos 
    y tengan las reglas de transición de estados actualizadas.
    """
    print("LOG: Verificando configuración de flujos logísticos...")

    # 1. Configuración para el Flujo Estándar
    flujo_estandar_data = {
        "nombre_flujo": "Flujo Estándar",
        "descripcion": "Flujo regular para sedes no procesadoras (Requiere envío logístico)",
        "estados_permitidos": [
            "Pendiente",      # <--- ¡CORRECCIÓN AQUÍ!
            "Recolectada", 
            "En Tránsito", 
            "En Laboratorio", 
            "Procesada", 
            "Validada"
        ],
        "transiciones_validas": {
            "Pendiente": ["Recolectada"],
            "Recolectada": ["En Tránsito", "En Laboratorio"],
            "En Tránsito": ["En Laboratorio"],
            "En Laboratorio": ["Procesada"],
            "Procesada": ["Validada"]
        }
    }

    # 2. Configuración para el Flujo Local
    flujo_local_data = {
        "nombre_flujo": "Flujo Local (Sede Única)",
        "descripcion": "Flujo simplificado para sedes que procesan sus propias muestras",
        "estados_permitidos": [
            "Pendiente",      # <--- ¡CORRECCIÓN AQUÍ!
            "Recolectada", 
            "En Laboratorio", 
            "Procesada", 
            "Validada"
        ],
        "transiciones_validas": {
            "Pendiente": ["Recolectada"],
            "Recolectada": ["En Laboratorio"],
            "En Laboratorio": ["Procesada"],
            "Procesada": ["Validada"]
        }
    }

    for datos_flujo in [flujo_estandar_data, flujo_local_data]:
        # Buscamos si ya existe el flujo por su nombre
        flujo_existente = await FlujoMuestra.find_one(
            FlujoMuestra.nombre_flujo == datos_flujo["nombre_flujo"]
        )

        if flujo_existente:
            # --- CORRECCIONES CRÍTICAS AQUÍ ---
            flujo_existente.estados_permitidos = datos_flujo["estados_permitidos"]  # <-- ¡Faltaba esta línea crucial!
            flujo_existente.transiciones_validas = datos_flujo["transiciones_validas"]
            flujo_existente.descripcion = datos_flujo["descripcion"]
            
            # Usamos replace() en lugar de save() para obligar a MongoDB a reescribir todo
            await flujo_existente.replace() 
            print(f"LOG: Flujo '{datos_flujo['nombre_flujo']}' actualizado por completo con 'Pendiente'.")
        else:
            # Si no existe, lo creamos desde cero
            nuevo_flujo = FlujoMuestra(**datos_flujo)
            await nuevo_flujo.insert()
            print(f"LOG: Flujo '{datos_flujo['nombre_flujo']}' creado por primera vez.")