import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.application import MIMEApplication
from models.log_envios import LogEnvio

SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_USER = os.getenv("SMTP_USER", "a.erguetab@gmail.com") 
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD")

async def enviar_correo_resultados(email_destino: str, nombre_paciente: str, numero_orden: str, pdf_bytes: bytes = None):
    # 1. Inicializamos variables de seguridad
    msg = None
    server = None
    estado_final = "Enviado"
    error_info = None
    
    try:
        # 2. Creamos el contenedor del mensaje
        msg = MIMEMultipart()
        msg['From'] = SMTP_USER
        msg['To'] = email_destino
        msg['Subject'] = f"🔬 LabNext: Resultados de tu Orden N° {numero_orden} listos"
        
        # 3. Definimos el diseño HTML
        html_content = f"""
        <html>
            <body style="font-family: Arial, sans-serif; color: #333; line-height: 1.6;">
                <div style="max-width: 600px; margin: 0 auto; padding: 20px; border: 1px solid #ddd; border-radius: 8px;">
                    <h2 style="color: #0056b3;">¡Hola, {nombre_paciente}!</h2>
                    <p>Los resultados de su orden <strong>{numero_orden}</strong> ya han sido validados.</p>
                    <p>Adjunto a este correo encontrará su reporte oficial en formato PDF.</p>
                    <hr style="border: 0; border-top: 1px solid #eee;">
                    <p style="font-size: 11px; color: #777; text-align: center;">Este es un correo automático de LabNext.</p>
                </div>
            </body>
        </html>
        """
        msg.attach(MIMEText(html_content, 'html'))

        # 4. Adjuntamos el PDF si existe
        if pdf_bytes:
            adjunto = MIMEApplication(pdf_bytes, _subtype="pdf")
            nombre_archivo = f"Resultados_{numero_orden}.pdf"
            adjunto.add_header('Content-Disposition', 'attachment', filename=nombre_archivo)
            msg.attach(adjunto)

        # 5. Conexión y envío
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT)
        server.starttls()
        server.login(SMTP_USER, SMTP_PASSWORD)
        server.sendmail(SMTP_USER, email_destino, msg.as_string())
        
        print(f" LOG: Correo con PDF enviado exitosamente a {email_destino}")
        
    except Exception as e:
        # Si falla el envío capturamos el error
        estado_final = "Error"
        error_info = str(e)
        print(f" ERROR al enviar correo a {email_destino}: {str(e)}")
        
    finally:
        # 6. Cerramos la conexión con seguridad
        if server:
            server.quit()
    
    # 7. Registro en BD (NUEVO BLOQUE CON TRAMPA DE ERRORES)
    try:
        nuevo_log = LogEnvio(
            orden_id=numero_orden,
            destinatario=email_destino,
            estado=estado_final,
            error_msg=error_info
        )
        await nuevo_log.insert()
        print(f" LOG BD: Historial guardado correctamente en la colección logs_envios.")
    except Exception as error_bd:
        print(f" ERROR CRÍTICO AL GUARDAR EN BD: {str(error_bd)}")
        
