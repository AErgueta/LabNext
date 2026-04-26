# Archivo: services/facturacion.py

def calcular_totales(subtotal: float, convenio, descuento_manual: float = 0.0) -> dict:
    
    # 1. Caso: Paciente Particular (Sin convenio)
    if not convenio:
        if descuento_manual > 0:
            descuento = subtotal * descuento_manual
            return {
                "subtotal": subtotal,
                "descuento": descuento,
                "total_paciente": subtotal - descuento,
                "total_seguro": 0.0,
                "mensaje_caja": f"Particular con descuento manual autorizado del {descuento_manual * 100}%"
            }
        else:
            return {
                "subtotal": subtotal,
                "descuento": 0.0,
                "total_paciente": subtotal,
                "total_seguro": 0.0,
                "mensaje_caja": "Particular (100% a cargo del paciente)"
            }

    # 2. Caso: Es un Seguro (Copago)
    if convenio.tipo == "Seguro":
        pago_paciente = subtotal * convenio.porcentaje_copago_paciente
        pago_seguro = subtotal * convenio.porcentaje_cobertura_seguro
        return {
            "subtotal": subtotal,
            "descuento": 0.0, 
            "total_paciente": pago_paciente,
            "total_seguro": pago_seguro,
            "mensaje_caja": f"Cobrar al paciente el {convenio.porcentaje_copago_paciente * 100}%"
        }

    # 3. Caso: Es una Empresa/Clínica (Descuento directo)
    elif convenio.tipo == "Empresa":
        descuento = subtotal * convenio.porcentaje_descuento
        return {
            "subtotal": subtotal,
            "descuento": descuento,
            "total_paciente": subtotal - descuento,
            "total_seguro": 0.0,
            "mensaje_caja": f"Descuento empresarial aplicado: {convenio.porcentaje_descuento * 100}%"
        }