#SCRIPT PARA NORMALIZAR Y SEGMENTAR AUDIO

import os
from pydub import AudioSegment
from pydub.silence import detect_silence

def encontrar_corte_seguro(audio, target_ms, ventana_busqueda_ms=120000):
    """
    Busca un silencio en los últimos 2 minutos (ventana_busqueda_ms) antes del target_ms.
    Si encuentra silencio, devuelve el punto medio de ese silencio para cortar ahí.
    Si no, corta en el target exacto.
    """
    if target_ms >= len(audio):
        return len(audio)
        
    inicio_busqueda = max(0, target_ms - ventana_busqueda_ms)
    fragmento_busqueda = audio[inicio_busqueda:target_ms]
    
    # Consideramos silencio algo que esté 16 dB por debajo del volumen medio del audio
    umbral_silencio = audio.dBFS - 16 
    
    # Buscamos silencios de al menos 500 ms (medio segundo)
    silencios = detect_silence(fragmento_busqueda, min_silence_len=500, silence_thresh=umbral_silencio)
    
    if silencios:
        # silencios es una lista de intervalos: [[inicio, fin], [inicio, fin]...]
        ultimo_silencio = silencios[-1]
        # Cortamos exactamente a la mitad del último silencio encontrado
        punto_corte = inicio_busqueda + ((ultimo_silencio[0] + ultimo_silencio[1]) // 2)
        return punto_corte
    else:
        # Si de casualidad hablaron 2 minutos seguidos sin respirar, cortamos en el target
        return target_ms

def procesar_flujo_completo(ruta_entrada, carpeta_salida, chunk_ms, target_dbfs=-20.0):
    print(f"1. Cargando audio original: {ruta_entrada}...")
    audio = AudioSegment.from_file(ruta_entrada)
    
    # ESTANDARIZACIÓN
    print("2. Estandarizando formato (Mono, 44100Hz)...")
    audio = audio.set_frame_rate(44100).set_channels(1)

    # NORMALIZACIÓN GLOBAL
    print("3. Aplicando normalización de volumen...")
    cambio_en_dbfs = target_dbfs - audio.dBFS
    audio = audio.apply_gain(cambio_en_dbfs)

    if not os.path.exists(carpeta_salida):
        os.makedirs(carpeta_salida)

    # EXPORTAR MASTER(S) para AssemblyAI (Límite ideal de 7 horas)
    limite_master_ms = 7 * 60 * 60 * 1000
    total_ms = len(audio)
    rutas_masters = []
    limites_reales_masters = [] # Guardaremos dónde cortó exactamente

    if total_ms <= limite_master_ms:
        ruta_master = os.path.join(carpeta_salida, "MASTER_NORMALIZADO.flac")
        print(f"4. Exportando archivo MASTER para mapeo: {ruta_master}")
        audio.export(ruta_master, format="flac")
        rutas_masters.append(ruta_master)
        limites_reales_masters.append((0, total_ms))
    else:
        print(f"4. Audio muy largo detectado. Dividiendo MASTER en partes de ~7 horas buscando pausas...")
        inicio_m = 0
        contador_m = 1
        while inicio_m < total_ms:
            fin_ideal_m = min(inicio_m + limite_master_ms, total_ms)
            fin_real_m = encontrar_corte_seguro(audio, fin_ideal_m)
            
            chunk_m = audio[inicio_m:fin_real_m]
            ruta_master = os.path.join(carpeta_salida, f"MASTER_NORMALIZADO_PARTE_{contador_m:02d}.flac")
            print(f"   -> Exportando MASTER PARTE {contador_m} (Corte seguro en {(fin_real_m/1000)/60:.2f} min): {ruta_master}")
            chunk_m.export(ruta_master, format="flac")
            
            rutas_masters.append(ruta_master)
            limites_reales_masters.append((inicio_m, fin_real_m))
            
            inicio_m = fin_real_m
            contador_m += 1

    # SEGMENTACIÓN PARA GEMINI (Bloques de ~50 minutos buscando pausas)
    print("5. Iniciando segmentación en bloques de ~50 minutos (buscando pausas)...")
    inicio = 0
    contador = 1
    limites_reales_segmentos = [] # Vital para que Assembly sepa dónde empieza y termina cada segmento exacto

    while inicio < total_ms:
        fin_ideal = min(inicio + chunk_ms, total_ms)
        fin_real = encontrar_corte_seguro(audio, fin_ideal)
        
        chunk = audio[inicio:fin_real]
        
        nombre_chunk = f"segmento_{contador:02d}.flac"
        ruta_chunk = os.path.join(carpeta_salida, nombre_chunk)
        
        chunk.export(ruta_chunk, format="flac")
        duracion_min = (fin_real - inicio) / 1000 / 60
        print(f"   [OK] Fragmento guardado: {nombre_chunk} (Duración real: {duracion_min:.2f} min)")
        
        limites_reales_segmentos.append({'archivo': nombre_chunk, 'inicio_ms': inicio, 'fin_ms': fin_real})
        
        inicio = fin_real
        contador += 1

    print(f"\n¡Proceso terminado! Generados {len(rutas_masters)} MASTER(S) y {contador-1} segmentos.")
    
    # Retornamos todo lo necesario para no perder la sincronía matemática
    return rutas_masters, limites_reales_masters, limites_reales_segmentos