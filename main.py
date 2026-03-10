import os
import shutil
import preprocesar_audio
import assembly_test
import fusion_assembly_gemini
from google_services import obtener_servicios_google, obtener_filas_pendientes, actualizar_status_y_link
from drive_manager import procesar_link_entrada, crear_carpeta_drive, subir_archivo_drive

# --- CONFIGURACIÓN GLOBAL ---
# Esta es la "super solución" para el desfase
DURACION_SEGMENTO_MS = 50 * 60 * 1000 
SPREADSHEET_ID = '1DPf_Z_YKfIGEO1vlzLGCk6IRTFYzuLkUAf2ylRRdqXY'
CARPETA_TRANSCRIPCIONES_ID = '17Ady_eCQFjebnHwLAyBKetWjl-9rHz66'

def limpiar_directorio_local(ruta):
    """Elimina la carpeta temporal local después de procesar."""
    if os.path.exists(ruta):
        try:
            shutil.rmtree(ruta)
        except Exception as e:
            print(f"No se pudo borrar la carpeta temporal {ruta}: {e}")

def main():
    print("Iniciando Orquestador del Sistema AI RFE...")
    
    # 1. Autenticación con Google
    sheets_service, drive_service = obtener_servicios_google()
    
    # 2. Leer filas pendientes (CORREGIDO: Ahora pasa ambos argumentos)
    filas = obtener_filas_pendientes(SPREADSHEET_ID, sheets_service)
    if not filas:
        print("No hay filas con status 'PENDING'. Saliendo...")
        return

    print(f"Se encontraron {len(filas)} filas para procesar.")

    for fila in filas:
        print(f"\n{'='*50}")
        print(f"Procesando Fila {fila['fila_excel']} - Cliente: {fila['cliente']}")
        print(f"{'='*50}")
        
        # Cambiar estado a PROCESSING
        actualizar_status_y_link(sheets_service, SPREADSHEET_ID, fila['fila_excel'], "PROCESSING")
        
        carpeta_trabajo = f"temp_procesamiento_{fila['fila_excel']}"
        carpeta_descargas = os.path.join(carpeta_trabajo, "descargas")
        
        try:
            # 4. Descargar archivos de Drive
            rutas_descargadas, tipo_link = procesar_link_entrada(drive_service, fila['link'], carpeta_descargas)
            
            if not rutas_descargadas:
                actualizar_status_y_link(sheets_service, SPREADSHEET_ID, fila['fila_excel'], "ERROR: No hay archivos")
                continue

            archivos_txt_generados = []

            for ruta_audio in rutas_descargadas:
                nombre_base = os.path.splitext(os.path.basename(ruta_audio))[0]
                carpeta_segmentos = os.path.join(carpeta_trabajo, f"segmentos_{nombre_base}")
                archivo_txt_final = os.path.join(carpeta_trabajo, f"Transcripcion_{nombre_base}.txt")

                print(f"\n--- Iniciando pipeline para: {nombre_base} ---")
                
                # Paso A: Preprocesar (Usa la constante global)
                ruta_master = preprocesar_audio.procesar_flujo_completo(ruta_audio, carpeta_segmentos, DURACION_SEGMENTO_MS)
                
                # Paso B: AssemblyAI (Usa la constante global para evitar desfase)
                exito_assembly = assembly_test.generar_mapas_segmentados(ruta_master, carpeta_segmentos, DURACION_SEGMENTO_MS)
                if not exito_assembly:
                    raise Exception(f"Falló el proceso de AssemblyAI para {nombre_base}")
                
                # Paso C: Gemini (Usa la constante global para el ensamblado final)
                fusion_assembly_gemini.ensamblar_transcripcion_final(carpeta_segmentos, archivo_txt_final, DURACION_SEGMENTO_MS)
                
                if os.path.exists(archivo_txt_final):
                    archivos_txt_generados.append(archivo_txt_final)

            # 6. Subir resultados a Drive
            link_resultado_drive = ""
            if tipo_link == 'folder' or len(archivos_txt_generados) > 1:
                nombre_carpeta_nueva = f"Transcripciones - {fila['cliente']}"
                folder_id, link_resultado_drive = crear_carpeta_drive(drive_service, nombre_carpeta_nueva, CARPETA_TRANSCRIPCIONES_ID)
                for txt in archivos_txt_generados:
                    subir_archivo_drive(drive_service, txt, folder_id)
            else:
                link_resultado_drive = subir_archivo_drive(drive_service, archivos_txt_generados[0], CARPETA_TRANSCRIPCIONES_ID)

            # 7. Actualizar Spreadsheet con ÉXITO
            actualizar_status_y_link(sheets_service, SPREADSHEET_ID, fila['fila_excel'], "COMPLETED", link_resultado_drive)
            print(f"Fila {fila['fila_excel']} completada con éxito.")

        except Exception as e:
            print(f"Error en fila {fila['fila_excel']}: {e}")
            actualizar_status_y_link(sheets_service, SPREADSHEET_ID, fila['fila_excel'], "ERROR", str(e)[:50])
        
        finally:
            limpiar_directorio_local(carpeta_trabajo)

if __name__ == "__main__":
    main()