# Archivo: routes/ordenes.py
from fastapi import APIRouter, HTTPException, Depends
from models.orden import Orden
from models.estudio import Estudio
from services.evaluador import interpretar_resultado # Importamos nuestra Función Global
from utils.seguridad import verificar_token

router = APIRouter()

@router.post("/ordenes")
async def crear_orden(orden: Orden, usuario: dict = Depends(verificar_token)):
    # Al hacer .insert(), Beanie dispara el @before_event automáticamente
    await orden.insert()
    return {
        "status": "success",
        "numero_orden": orden.numero_orden,
        "total_calculado": orden.total_pagado # Veremos si el trigger funcionó
    }

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