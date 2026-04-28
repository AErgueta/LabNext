# Archivo: services/validador_clinico.py
from models.resultado import ResultadoDetalle
from models.estudio import Estudio

def procesar_resultados_estudio(estudio_db: Estudio, valores_enviados: dict, edad_paciente: int, sexo_paciente: str) -> list[ResultadoDetalle]:
    """
    Recibe el Estudio completo del catálogo y un diccionario con los valores que digitó el bioquímico.
    Ejemplo de valores_enviados: {"Glucosa Basal": 115.0, "Colesterol Total": 180.5}
    """
    detalles_procesados = []

    # 1. Recorremos todos los analitos que componen este estudio en el catálogo
    for analito_catalogo in estudio_db.analitos:
        
        # 2. Verificamos si el bioquímico mandó un resultado para ESTE analito específico
        if analito_catalogo.nombre in valores_enviados:
            valor_maquina = valores_enviados[analito_catalogo.nombre]
            
            # Variables por defecto por si el paciente no encaja en ningún rango
            estado = "Normal"
            fuera_rango = False
            texto_rango_aplicado = "Revisión manual requerida"

            # 3. Buscamos el rango correcto para este paciente dentro de los rangos de ESTE analito
            for rango in analito_catalogo.rangos:
                
                # Filtro de Sexo
                if rango.sexo != "Ambos" and rango.sexo != sexo_paciente:
                    continue
                
                # Filtro de Edad
                if not (rango.edad_min <= edad_paciente <= rango.edad_max):
                    continue

                # ¡Hicimos Match! Evaluamos el valor contra los límites numéricos
                if rango.valor_min is not None and valor_maquina < rango.valor_min:
                    estado = "Bajo"
                    fuera_rango = True
                elif rango.valor_max is not None and valor_maquina > rango.valor_max:
                    estado = "Alto"
                    fuera_rango = True
                else:
                    estado = "Normal"
                    fuera_rango = False

                # Guardamos la "fotografía" del rango usado
                texto_rango_aplicado = f"{rango.valor_min} a {rango.valor_max} ({rango.texto_referencia})"
                
                # Como ya encontramos el rango correcto para el paciente, dejamos de buscar
                break 

            # 4. Ensamblamos la pieza final del resultado para la base de datos
            detalle_final = ResultadoDetalle(
                analito=analito_catalogo.nombre,
                valor_leido=valor_maquina,
                unidad_medida=analito_catalogo.unidad_medida,
                estado_clinico=estado,
                rango_aplicado=texto_rango_aplicado,
                fuera_de_rango=fuera_rango
            )
            
            detalles_procesados.append(detalle_final)

    return detalles_procesados