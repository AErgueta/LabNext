from fastapi import FastAPI
import uvicorn
from database.config import conectar_bd

from routes.estudios import router as rutas_estudios
from routes.ordenes import router as rutas_ordenes 
from routes.medicos import router as rutas_medicos
from routes.convenios import router as rutas_convenios
from routes.caja import router as rutas_caja
from routes.auth import router as rutas_auth
from routes.pacientes import router as rutas_pacientes
from routes.sedes import router as rutas_sedes
from routes.flujos import router as rutas_flujos
from routes.muestras import router as rutas_muestras
from routes.resultados import router as resultados

# Importamos la función de sembrado arriba con los demás imports
from utils.init_db import verificar_y_actualizar_flujos

app = FastAPI(title="LabNext API")

# Centralizamos todo lo que debe ocurrir al arrancar el servidor aquí
@app.on_event("startup")
async def iniciar_servidor():
    # 1. Conectar a MongoDB a través de Beanie
    await conectar_bd()
    
    # 2. Ejecutar inmediatamente el blindaje y actualización de flujos logísticos
    await verificar_y_actualizar_flujos()

# Inclusión de routers de tu API
app.include_router(rutas_estudios, tags=["Catálogo de Estudios"])
app.include_router(rutas_ordenes, tags=["Órdenes de Trabajo"]) 
app.include_router(rutas_medicos, tags=["Catálogo de Médicos"])
app.include_router(rutas_convenios, tags=["Catálogo de Convenios"])
app.include_router(rutas_caja, tags=["Caja y Facturación"])
app.include_router(rutas_auth, tags=["Seguridad"])
app.include_router(rutas_pacientes, tags=["Pacientes"])
app.include_router(rutas_sedes, prefix="/sedes", tags=["Sedes"])
app.include_router(rutas_flujos, prefix="/flujos", tags=["Configuración - Flujos de Muestras"])
app.include_router(rutas_muestras, prefix="/muestras", tags=["Logística y Tracking"])
app.include_router(resultados, prefix="/resultados", tags=["Resultados"])

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)