# Archivo: routes/caja.py
from fastapi import APIRouter, HTTPException, Depends  # <-- 1. Agregamos Depends aquí
from models.orden import Orden
from models.estudio import Estudio
from models.convenio import Convenio
from services.facturacion import calcular_totales

from utils.seguridad import verificar_token  # <-- 2. Importamos a nuestro guardia

router = APIRouter()

# --- 3. PONEMOS EL CANDADO EN LOS PARÉNTESIS ---
@router.get("/caja/liquidar/{numero_orden}")
async def liquidar_orden(numero_orden: str, usuario_actual: str = Depends(verificar_token)):
    
    # 1. Buscamos la orden
    orden = await Orden.find_one(Orden.numero_orden == numero_orden)
    if not orden:
        raise HTTPException(status_code=404, detail="Orden no encontrada")

    # 2. Sumamos los precios base de los estudios solicitados
    subtotal = 0.0
    for codigo in orden.estudios_solicitados:
        estudio = await Estudio.find_one(Estudio.codigo_cups == codigo)
        if estudio:
            subtotal += estudio.precio_base

    # 3. Buscamos el convenio si la orden tiene uno
    convenio = None
    if orden.convenio:
        convenio = await Convenio.find_one(Convenio.nombre == orden.convenio)

    # 4. Usamos nuestro "Cerebro Financiero" para hacer el cálculo
    resultado = calcular_totales(subtotal, convenio, orden.descuento_manual)

    # 5. Devolvemos el "Ticket" a la pantalla
    return {
        "paciente": orden.paciente.nombre_completo,
        "convenio_aplicado": orden.convenio or "Ninguno",
        "detalle_cobro": resultado
    }