# Archivo: services/evaluador.py

def interpretar_resultado(valor: float, paciente_sexo: str, paciente_edad: int, rangos: list) -> str:
    """
    Recibe el valor del laboratorio y lo compara con los rangos 
    adecuados según la edad y sexo del paciente.
    """
    for rango in rangos:
        # 1. Filtramos: ¿Este rango es para el sexo y edad de nuestro paciente?
        if rango.sexo == paciente_sexo and (rango.edad_min <= paciente_edad <= rango.edad_max):
            
            # 2. Evaluamos el valor numérico
            if valor < rango.valor_min:
                return "Bajo ⬇️"
            elif valor > rango.valor_max:
                return "Alto ⬆️"
            else:
                return "Normal ✅"
                
    return "Sin Referencia (Fuera de rango de edad/sexo)"