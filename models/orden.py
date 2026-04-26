from pydantic import BaseModel, Field
from typing import List, Optional, Annotated
from beanie import Document, before_event, Insert, Replace, Save, PydanticObjectId
# Importamos time para la hora de corte y timedelta para los cálculos
from datetime import datetime, timedelta, time 
# Importamos el modelo Estudio para buscar los precios y días de demora
from models.estudio import Estudio 
from models.sede import Sede

# --- CONSTANTES DE NEGOCIO ---
# Mapeo de Python (0-6) a tus strings de la DB
DIAS_MAP = {
    0: "Lunes", 1: "Martes", 2: "Miercoles", 
    3: "Jueves", 4: "Viernes", 5: "Sábado", 6: "Domingo"
}

class PacienteInfo(BaseModel):
    nombre_completo: str
    sexo: str 
    edad_anos: int

class Orden(Document):
    numero_orden: str
    fecha_ingreso: datetime = Field(default_factory=datetime.now)
    sede_id: PydanticObjectId
    fecha_entrega_estimada: Optional[datetime] = None
    
    paciente: PacienteInfo 
    estudios_solicitados: List[str] 
    
    medico_solicitante: str
    convenio: Optional[str] = None 
    descuento_manual: float = 0.0 
    
    total_pagado: float = 0.0
    estado: str = "Ingresada" 

    @before_event([Insert, Replace, Save])
    async def procesar_logica_laboratorio(self):
        """
        Lógica procedural para calcular total, logística de sedes y fecha de entrega.
        """
        sede_actual = await Sede.get(self.sede_id)

        # 1. Ajuste por hora de corte (11:00 AM)
        fecha_base = self.fecha_ingreso
        if self.fecha_ingreso.time() >= time(11, 0):
            fecha_base = (self.fecha_ingreso + timedelta(days=1)).replace(hour=0, minute=0, second=0, microsecond=0)

        # --- ADICIÓN: Logística entre Sedes ---
        # Si la sede (ej: Equipetrol) no procesa, sumamos 1 día de transporte
        if sede_actual and not sede_actual.es_procesadora:
            fecha_base += timedelta(days=1)

        max_fecha_entrega = fecha_base
        subtotal = 0.0

        # 2. Iteración sobre estudios para consolidar la orden
        for nombre in self.estudios_solicitados:
            estudio_db = await Estudio.find_one(Estudio.nombre_estudio == nombre)
            if estudio_db:
                # Suma de precios
                subtotal += estudio_db.precio_base
                
                # Búsqueda del siguiente día de procesamiento
                fecha_inicio_proceso = fecha_base
                intentos = 0
                # Usamos DIAS_MAP para comparar el weekday de Python con tu lista de strings
                while DIAS_MAP[fecha_inicio_proceso.weekday()] not in estudio_db.dias_procesamiento and intentos < 7:
                    fecha_inicio_proceso += timedelta(days=1)
                    intentos += 1
                
                # Cálculo de entrega de este estudio individual
                fecha_resultado = fecha_inicio_proceso + timedelta(days=estudio_db.dias_demora)
                
                # Nos quedamos con la fecha más lejana (cuello de botella)
                if fecha_resultado > max_fecha_entrega:
                    max_fecha_entrega = fecha_resultado

        # 3. Asignación de resultados finales al objeto
        descuento = subtotal * self.descuento_manual
        self.total_pagado = subtotal - descuento
        self.fecha_entrega_estimada = max_fecha_entrega

    class Settings:
        name = "ordenes_trabajo"