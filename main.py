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

app = FastAPI(title="LabNext API")

@app.on_event("startup")
async def iniciar_servidor():
    await conectar_bd()

app.include_router(rutas_estudios, tags=["Catálogo de Estudios"])
app.include_router(rutas_ordenes, tags=["Órdenes de Trabajo"]) 
app.include_router(rutas_medicos, tags=["Catálogo de Médicos"])
app.include_router(rutas_convenios, tags=["Catálogo de Convenios"])
app.include_router(rutas_caja, tags=["Caja y Facturación"])
app.include_router(rutas_auth, tags=["Seguridad"])
app.include_router(rutas_pacientes, tags=["Pacientes"])
app.include_router(rutas_sedes, prefix="/sedes", tags=["Sedes"])
# (Aquí eliminamos la línea duplicada de órdenes que tenías)

if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)