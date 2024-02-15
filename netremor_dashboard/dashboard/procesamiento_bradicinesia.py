import pandas as pd
import numpy as np

# Cargar datos desde el archivo CSV
ruta_medias = 'mediasSujetosPotenciaEspectral.csv' 
ruta_medias_tiempo = 'tiemposMedExp_sujeto.csv'
ruta_resultados = 'resultadosParticipantesPotenciaEspectral.csv' 
ruta_resultados_tiempo = 'resultados_paciente_con_formato.csv'

medias = pd.read_csv(ruta_medias)
medias_tiempos = pd.read_csv(ruta_medias_tiempo)
resultados = pd.read_csv(ruta_resultados)
tiempos = pd.read_csv(ruta_resultados_tiempo)

primer_paciente_inex = 190

# Cargar datos en variables
pem = medias['PotenciaEspectralMaxima'].tolist()
frec_dom = medias['FrecuenciaDominante'].tolist()
tiempos_medios = medias_tiempos['TiempoMedio'].tolist()
tiempos_maximos = medias_tiempos['TiempoMaximo'].tolist()
resultados_pem = resultados['PotenciaEspectralMaxima'].tolist()
resultados_pem = resultados_pem[primer_paciente_inex:]
resultados_frec_dom = resultados['FrecuenciaDominante'].tolist()
resultados_frec_dom = resultados_frec_dom[primer_paciente_inex:]
resultados_tiempos = tiempos['TiempoMedio'].tolist()

# Número de elementos en cada segmento
elementos_por_segmento = 10

# Listas para almacenar resultados
resultados_por_segmento_pem = []
resultados_numericos_pem = []
resultados_por_segmento_frec_dom = []
resultados_numericos_frec_dom = []
resultados_por_segmento_tiempos = []
resultados_numericos_tiempos = []

# Número total de segmentos
num_segmentos_pem = len(resultados_pem) // elementos_por_segmento
num_segmentos_frec_dom = len(resultados_frec_dom) // elementos_por_segmento
num_segmentos_tiempos = len(resultados_tiempos) // elementos_por_segmento

# Lista de nombres para las filas
nombres_filas = [f"Paciente_{i+1}" for i in range(num_segmentos_pem)]

# Bucle para comparar segmentos de 10 elementos
for i in range(0, len(resultados_pem), elementos_por_segmento):
    segmento_actual_pem = resultados_pem[i:i + elementos_por_segmento]

    comparacion_pem = [elemento < variable for elemento, variable in zip(segmento_actual_pem, pem)]
    resultados_por_segmento_pem.append(comparacion_pem)

    # Convertir True/False a 1/0
    resultados_numericos_pem.append([int(resultado) for resultado in comparacion_pem])

# Bucle para comparar segmentos de 10 elementos
for i in range(0, len(resultados_frec_dom), elementos_por_segmento):
    segmento_actual_frec_dom = resultados_frec_dom[i:i + elementos_por_segmento]

    comparacion_frec_dom = [elemento < variable for elemento, variable in zip(segmento_actual_frec_dom, frec_dom)]
    resultados_por_segmento_frec_dom.append(comparacion_frec_dom)

    # Convertir True/False a 1/0
    resultados_numericos_frec_dom.append([int(resultado) for resultado in comparacion_frec_dom])


# Bucle para comparar segmentos de 10 elementos
for i in range(0, len(resultados_tiempos), elementos_por_segmento):
    segmento_actual_tiempos = resultados_tiempos[i:i + elementos_por_segmento]

    comparacion_tiempos = [elemento > (variable + abs(variable_max-variable)/2) for elemento, variable, variable_max in zip(segmento_actual_tiempos, tiempos_medios, tiempos_maximos)]
    resultados_por_segmento_tiempos.append(comparacion_tiempos)

    # Convertir True/False a 1/0
    resultados_numericos_tiempos.append([int(resultado) for resultado in comparacion_tiempos])

df_resultados_pem = pd.DataFrame(resultados_numericos_pem, index=nombres_filas, columns=[f"Tarea_{i+1}" for i in range(len(pem))])
df_resultados_pem.to_excel('resultados_segmentos_pem.xlsx', index=True)
print(df_resultados_pem)

df_resultados_frec_dom = pd.DataFrame(resultados_numericos_frec_dom, index=nombres_filas, columns=[f"Tarea_{i+1}" for i in range(len(frec_dom))])
df_resultados_frec_dom.to_excel('resultados_segmentos_frec_dom.xlsx', index=True)
print(df_resultados_frec_dom)

df_resultados_tiempos = pd.DataFrame(resultados_numericos_tiempos, index=nombres_filas, columns=[f"Tarea_{i+1}" for i in range(len(frec_dom))])
df_resultados_tiempos.to_excel('resultados_segmentos_tiempos.xlsx', index=True)
print(df_resultados_tiempos)

df_resultados_pem['Suma'] = df_resultados_pem.sum(axis=1)
df_resultados_frec_dom['Suma'] = df_resultados_frec_dom.sum(axis=1)
df_resultados_tiempos['Suma'] = df_resultados_tiempos.sum(axis=1)

posibilidades_bradicinesia = (df_resultados_pem['Suma'] + df_resultados_frec_dom['Suma'] + df_resultados_tiempos['Suma']) *100 / 30

# Imprimir resultados
print("\nResultados Potencia Espectral Máxima:")
print(df_resultados_pem[['Suma']])

print("\nResultados Frecuencia Dominante:")
print(df_resultados_frec_dom[['Suma']])

print("\nResultados Tiempos:")
print(df_resultados_tiempos['Suma'])

print("\nPosibilidades de tener bradicinesia:")
print(posibilidades_bradicinesia)