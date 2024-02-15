import pandas as pd
import numpy as np
from scipy.signal import hilbert, find_peaks
import matplotlib.pyplot as plt
import glob
import os

def compute_magnitude(df):
    return np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)

def find_absolute_top_2_peaks_with_separation_100(envelope, min_samples_separation=34):
    peak_indices, _ = find_peaks(envelope)
    peaks_above_100 = [idx for idx in peak_indices if envelope[idx] > 100] 
    top_peak_1_index = peaks_above_100[0]
    top_peak_2_index = peaks_above_100[-1]
    return [top_peak_1_index, top_peak_2_index]

def find_absolute_top_2_peaks_with_separation_25(envelope, min_samples_separation=34):
    peak_indices, _ = find_peaks(envelope)
    peaks_above_100 = [idx for idx in peak_indices if envelope[idx] > 25] # Usar 25 para Francisco P y Julian
    top_peak_1_index = peaks_above_100[0]
    top_peak_2_index = peaks_above_100[-1]
    return [top_peak_1_index, top_peak_2_index]

# Directorios
directorio_sujetos = 'SujetosSanos'
directorio_pacientes = 'Pacientes'


sujetos = ['CristinaBayon', 'lab11', 'lab12', 'lab13', 'lab14', 'lab15', 'lab16', 'LauraRomeroCrespo', 'LuciaDoradoGonzalez', 'MariaLorenzo', 'MiriamMugicaEsteve']
pacientes = ['ET_FranciscoMorenoCastillo', 'ET_MariaDelCarmenDelEspinoCruz', 'ET_SantosRodriguezSanchez', 'PD_FranciscoPorrasLopez',
             'PD_JoseAntonioOrtizBaeza', 'PD_JulianMonteroSanchez', 'PD_MariaDelPilarGaleotaPozo']

# Lista de experimentos
experimentos = ['bb', 'bt', 'cb', 'ce', 'ef', 'ot', 'sd', 'sn', 'tb', 'td']

# Lista de datos disponibles
datos_disponibles = ['gyroscope-0', 'gyroscope-1', 'gyroscope-2']

# Estructuras para almacenar los datos
datos_sujeto = {}
datos_paciente = {}

# Crear un diccionario para almacenar los resultados
resultados_sujeto_dict = {'Sujeto': [], 'Experimento': [], 'TiempoMedio': [], 'TiempoMaximo': []}
resultados_completos_sujetos_dict = {'Sujeto': [], 'Experimento': [], 'Tiempo': []}
resultados_paciente_dict = {'Paciente': [], 'Experimento': [], 'TiempoMedio': []}
resultados_completos_pacientes_dict = {'Paciente': [], 'Experimento': [], 'Tiempo': []}
tiemposMedExp_sujeto_dict = {'Experimento': [], 'TiempoMedio': [], 'TiempoMaximo': []}
tiemposMedExp_paciente_dict = {'Experimento': [], 'TiempoMedio': []}

# Creación de estructuras de datos para cada tipo de participante
for sujeto in sujetos:
    datos_sujeto[sujeto] = {}
    for experimento in experimentos:
        datos_sujeto[sujeto][experimento] = {}
        for tipo_dato in datos_disponibles:
            
            nombre_archivo = f'{tipo_dato}.csv'
            
            ruta_datos = os.path.join(directorio_sujetos, sujeto, experimento)
            archivos = [archivo for archivo in os.listdir(ruta_datos) if nombre_archivo in archivo]
            
            if archivos:
                ruta_datos_completa = os.path.join(ruta_datos, archivos[0])
                datos = pd.read_csv(ruta_datos_completa)
                datos_sujeto[sujeto][experimento][tipo_dato] = datos

for paciente in pacientes:
    datos_paciente[paciente] = {}
    for experimento in experimentos:
        datos_paciente[paciente][experimento] = {}
        for tipo_dato in datos_disponibles:

            nombre_archivo = f'{tipo_dato}.csv'

            ruta_datos = os.path.join(directorio_pacientes, paciente, experimento)
            archivos = [archivo for archivo in os.listdir(ruta_datos) if nombre_archivo in archivo]
            
            if archivos:
                ruta_datos_completa = os.path.join(ruta_datos, archivos[0])
                datos = pd.read_csv(ruta_datos_completa)
                datos_paciente[paciente][experimento][tipo_dato] = datos

cuenta_resultado_sujeto = 0
cuenta_resultado_paciente = 0
resultado_ms_sujeto = []
resultado_ms_paciente = []
resultado_s_sujeto = []
resultado_s_paciente = []
bb_max = []
bt_max = []
cb_max = []
ce_max = []
ef_max = []
ot_max = []
sd_max = []
sn_max = []
tb_max = []
td_max = []

resultados_obtenidos = []

for sujeto in sujetos:
    for experimento in experimentos:
        for tipo_dato in datos_disponibles:
            data_sujeto = datos_sujeto[sujeto][experimento][tipo_dato]
            data_sujeto['magnitude'] = compute_magnitude(data_sujeto)
            top_2_indices0 = find_absolute_top_2_peaks_with_separation_100(data_sujeto['magnitude'].values, min_samples_separation=34)
            
            distance_in_samples0 = abs(top_2_indices0[1] - top_2_indices0[0])
            resultado_ms_sujeto.append(distance_in_samples0 * 30)
            resultado_s_sujeto.append(resultado_ms_sujeto[-1] / 1000)

            # if(sujeto == 'GabrielDelgado') and (experimento == 'sd'):
            #    print(data)
            #    print(f"El participante {sujeto} tardó {resultado_s_sujeto[-1]} s en realizar la Repetición {datos_disponibles.index(tipo_dato)} de la Tarea {experimento}")

            cuenta_resultado_sujeto += 1

            resultados_completos_sujetos_dict['Sujeto'].append(sujeto)
            resultados_completos_sujetos_dict['Experimento'].append(experimento)
            resultados_completos_sujetos_dict['Tiempo'].append(resultado_s_sujeto[-1])

            if cuenta_resultado_sujeto % 3 == 0:
                resultado_ms_sujeto = resultado_ms_sujeto[-3:]
                resultado_s_sujeto = resultado_s_sujeto[-3:]
                resultados_obtenidos .append(resultado_s_sujeto)
                duracionTarea = sum(resultado_s_sujeto) / 3
                maximaDuracion = max(resultado_s_sujeto)
                # print(f"El participante {participante} tardó {duracionTarea} s de media en realizar la Tarea {experimento}")

                resultados_sujeto_dict['Sujeto'].append(sujeto)
                resultados_sujeto_dict['Experimento'].append(experimento)
                resultados_sujeto_dict['TiempoMedio'].append(duracionTarea)
                resultados_sujeto_dict['TiempoMaximo'].append(maximaDuracion)

                cuenta_resultado_sujeto = 0
            
            num_iteraciones = 10

            # GRÁFICAS
            # if((sujeto == 'GabrielDelgado') and (experimento == 'sd')):
            #     plt.figure()
            #     plt.plot(data_sujeto['magnitude'], label='Magnitud')
            #     plt.scatter(top_2_indices0, data_sujeto['magnitude'][top_2_indices0], color='red', label='Picos')

            #     plt.legend()

            #     titulo = f"Repetición {datos_disponibles.index(tipo_dato)} de la Tarea {experimento} realizada por el paciente {sujeto}"
            #     plt.title(titulo)
            #     plt.xlabel('Muestra')
            #     plt.ylabel('Magnitud') 

            #     plt.show()
    
for paciente in pacientes:
    for experimento in experimentos:
        for tipo_dato in datos_disponibles:
            data_paciente = datos_paciente[paciente][experimento][tipo_dato]
            data_paciente['magnitude'] = compute_magnitude(data_paciente)

            if((paciente == 'PD_FranciscoPorrasLopez') or (paciente == 'PD_JulianMonteroSanchez')):
                top_2_indices0 = find_absolute_top_2_peaks_with_separation_25(data_paciente['magnitude'].values, min_samples_separation=34)
            else:
                top_2_indices0 = find_absolute_top_2_peaks_with_separation_100(data_paciente['magnitude'].values, min_samples_separation=34)
   
            distance_in_samples0 = abs(top_2_indices0[1] - top_2_indices0[0])
            resultado_ms_paciente.append(distance_in_samples0 * 30)
            resultado_s_paciente.append(resultado_ms_paciente[-1] / 1000)

            # if(paciente == 'PD_JulianMonteroSanchez'):
            #     print(f"El participante {paciente} tardó {resultado_s_paciente[-1]} s en realizar la Repetición {datos_disponibles.index(tipo_dato)} de la Tarea {experimento}")

            cuenta_resultado_paciente += 1

            resultados_completos_pacientes_dict['Paciente'].append(paciente)
            resultados_completos_pacientes_dict['Experimento'].append(experimento)
            resultados_completos_pacientes_dict['Tiempo'].append(resultado_s_paciente[-1])

            if cuenta_resultado_paciente % 3 == 0:
                resultado_ms_paciente = resultado_ms_paciente[-3:]
                resultado_s_paciente = resultado_s_paciente[-3:]
                duracionTarea_paciente = sum(resultado_s_paciente) / 3
                # print(f"El participante {participante} tardó {duracionTarea} s de media en realizar la Tarea {experimento}")

                # Agregar datos al diccionario
                resultados_paciente_dict['Paciente'].append(paciente)
                resultados_paciente_dict['Experimento'].append(experimento)
                resultados_paciente_dict['TiempoMedio'].append(duracionTarea_paciente)
                cuenta_resultado_paciente = 0

            # GRÁFICAS
            if((paciente == 'ET_FranciscoMorenoCastillo') and (experimento == 'cb')):
                plt.figure()
                plt.plot(data_paciente['magnitude'], label='Magnitud')
                plt.scatter(top_2_indices0, data_paciente['magnitude'][top_2_indices0], color='red', label='Picos')

                plt.legend()

                titulo = f"Repetición {datos_disponibles.index(tipo_dato)} de la Tarea {experimento} realizada por el paciente {paciente}"
                plt.title(titulo)
                plt.xlabel('Muestra')
                plt.ylabel('Magnitud') 

                plt.show()

# Convertir el diccionario a un DataFrame
resultados_sujeto_df = pd.DataFrame(resultados_sujeto_dict)
resultados_paciente_df = pd.DataFrame(resultados_paciente_dict)
resultados_completos_sujetos_df = pd.DataFrame(resultados_completos_sujetos_dict)
resultados_completos_pacientes_df = pd.DataFrame(resultados_completos_pacientes_dict)

# Exportar el DataFrame a un archivo Excel y CSV
resultados_sujeto_df.to_csv('resultados_sujetos.csv', index=False)
resultados_paciente_df.to_csv('resultados_paciente.csv', index=False)
resultados_completos_sujetos_df.to_csv('resultados_completos_sujetos.csv', index=False)
resultados_completos_sujetos_df.to_excel('resultados_completos_sujetos.xlsx', index=True)
resultados_completos_pacientes_df.to_csv('resultados_completos_pacientes.csv', index=False)
resultados_completos_pacientes_df.to_excel('resultados_completos_pacientes.xlsx', index=True)

# Crear un objeto Styler
styler_sujeto = resultados_sujeto_df.style.apply(lambda x: ['color: red; font-weight: bold' if c == 'TiempoMedio' else '' for c in x])
styler_paciente = resultados_paciente_df.style.apply(lambda x: ['color: red; font-weight: bold' if c == 'TiempoMedio' else '' for c in x])

# Guardar el archivo HTML con formato
styler_sujeto.to_excel('resultados_sujeto_con_formato.xlsx', index=False, engine='openpyxl')
styler_paciente.to_excel('resultados_paciente_con_formato.xlsx', index=False, engine='openpyxl')

for experimento in experimentos:
    tiemposExp_sujeto = resultados_sujeto_df[resultados_sujeto_df['Experimento'] == experimento]
    tiemposMedExp_sujeto = sum(tiemposExp_sujeto['TiempoMedio'])/len(sujeto)
    tiemposMaxExp_sujeto = tiemposExp_sujeto['TiempoMedio'].max()
    tiemposMedExp_sujeto_dict['Experimento'].append(experimento)
    tiemposMedExp_sujeto_dict['TiempoMedio'].append(tiemposMedExp_sujeto)
    tiemposMedExp_sujeto_dict['TiempoMaximo'].append(tiemposMaxExp_sujeto)
    
    tiemposExp_paciente = resultados_paciente_df[resultados_paciente_df['Experimento'] == experimento]
    tiemposMedExp_paciente = sum(tiemposExp_paciente['TiempoMedio'])/len(paciente)
    tiemposMedExp_paciente_dict['Experimento'].append(experimento)
    tiemposMedExp_paciente_dict['TiempoMedio'].append(tiemposMedExp_paciente)

# Convertir el diccionario a un DataFrame
tiemposMedExp_sujeto_df = pd.DataFrame(tiemposMedExp_sujeto_dict)
tiemposMedExp_paciente_df = pd.DataFrame(tiemposMedExp_paciente_dict)

# Exportar el DataFrame a un archivo CSV
tiemposMedExp_sujeto_df.to_csv('tiemposMedExp_sujeto.csv', index=False)
tiemposMedExp_paciente_df.to_csv('tiemposMedExp_paciente.csv', index=False)

# Crear un objeto Styler
styler_sujeto2 = tiemposMedExp_sujeto_df.style.apply(lambda x: ['color: red; font-weight: bold' if c == 'TiempoMedio' else '' for c in x])
styler_paciente2 = tiemposMedExp_paciente_df.style.apply(lambda x: ['color: red; font-weight: bold' if c == 'TiempoMedio' else '' for c in x])

# Guardar el archivo HTML con formato
styler_sujeto2.to_excel('tiemposMedExp_sujeto_con_formato.xlsx', index=False, engine='openpyxl')
styler_paciente2.to_excel('tiemposMedExp_paciente_con_formato.xlsx', index=False, engine='openpyxl')

for i in range(0, num_iteraciones * 11, 10):
    bb_max.append(resultados_sujeto_dict['TiempoMaximo'][0+i])
    bt_max.append(resultados_sujeto_dict['TiempoMaximo'][1+i])
    cb_max.append(resultados_sujeto_dict['TiempoMaximo'][2+i])
    ce_max.append(resultados_sujeto_dict['TiempoMaximo'][3+i])
    ef_max.append(resultados_sujeto_dict['TiempoMaximo'][4+i])
    ot_max.append(resultados_sujeto_dict['TiempoMaximo'][5+i])
    sd_max.append(resultados_sujeto_dict['TiempoMaximo'][6+i])
    sn_max.append(resultados_sujeto_dict['TiempoMaximo'][7+i])
    tb_max.append(resultados_sujeto_dict['TiempoMaximo'][8+i])
    td_max.append(resultados_sujeto_dict['TiempoMaximo'][9+i])

bb_max_value = max(bb_max)
print(bb_max_value)
bt_max_value = max(bt_max)
cb_max_value = max(cb_max)
ce_max_value = max(ce_max)
ef_max_value = max(ef_max)
ot_max_value = max(ot_max)
sd_max_value = max(sd_max)
sn_max_value = max(sn_max)
tb_max_value = max(tb_max)
td_max_value = max(td_max)

diff_bb = abs(bb_max_value - tiemposMedExp_sujeto_dict['TiempoMedio'][0])
diff_bt = abs(bt_max_value - tiemposMedExp_sujeto_dict['TiempoMedio'][1])
diff_cb = abs(cb_max_value - tiemposMedExp_sujeto_dict['TiempoMedio'][2])
diff_ce = abs(ce_max_value - tiemposMedExp_sujeto_dict['TiempoMedio'][3])
diff_ef = abs(ef_max_value - tiemposMedExp_sujeto_dict['TiempoMedio'][4])
diff_ot = abs(ot_max_value - tiemposMedExp_sujeto_dict['TiempoMedio'][5])
diff_sd = abs(sd_max_value - tiemposMedExp_sujeto_dict['TiempoMedio'][6])
diff_sn = abs(sn_max_value - tiemposMedExp_sujeto_dict['TiempoMedio'][7])
diff_tb = abs(tb_max_value - tiemposMedExp_sujeto_dict['TiempoMedio'][8])
diff_td = abs(td_max_value - tiemposMedExp_sujeto_dict['TiempoMedio'][9])

resultados_guardados = {'Paciente': [], 'Tarea': [] ,'Resultado': [],}

for i in range(0, num_iteraciones * len(pacientes), 10):

    resultado_bb = None
    resultado_bt = None
    resultado_cb = None
    resultado_ce = None
    resultado_ef = None
    resultado_ot = None
    resultado_sd = None
    resultado_sn = None
    resultado_tb = None
    resultado_td = None
    cuenta_bradicinesia = 0

    if (resultados_paciente_dict['TiempoMedio'][0+i] > (tiemposMedExp_sujeto_dict['TiempoMedio'][0] + diff_bb/2)):
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Botón Camisa")
        resultado_bb = f"BRADICINESIA"
        cuenta_bradicinesia += 1
        print(f"Posible bradicinesia detectada en {pacientes[int(i/10)]} realizando la tarea Botón camisa")
    else: 
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Botón Camisa")
        resultado_bb = f"NO BRADICINESIA"
        print(f"{pacientes[int(i/10)]} libre de bradicinesia realizando la tarea Botón camisa")

    if (resultados_paciente_dict['TiempoMedio'][1+i] > (tiemposMedExp_sujeto_dict['TiempoMedio'][1] + diff_bt/2)):
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Lavar Dientes")
        resultado_bt = f"BRADICINESIA"
        cuenta_bradicinesia += 1
        print(f"Posible bradicinesia detectada en {pacientes[int(i/10)]} realizando la tarea Lavar Dientes")
    else: 
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Lavar Dientes")
        resultado_bt = f"NO BRADICINESIA"
        print(f"{pacientes[int(i/10)]} libre de bradicinesia realizando la tarea Lavar Dientes")
        
    if (resultados_paciente_dict['TiempoMedio'][2+i] > (tiemposMedExp_sujeto_dict['TiempoMedio'][2] + diff_cb/2)):
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Peinarse")
        resultado_cb = f"BRADICINESIA"
        cuenta_bradicinesia += 1
        print(f"Posible bradicinesia detectada en {pacientes[int(i/10)]} realizando la tarea Peinarse")
    else: 
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Peinarse")
        resultado_cb = f"NO BRADICINESIA"
        print(f"{pacientes[int(i/10)]} libre de bradicinesia realizando la tarea Peinarse")

    if (resultados_paciente_dict['TiempoMedio'][3+i] > (tiemposMedExp_sujeto_dict['TiempoMedio'][3] + diff_ce/2)):
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Cortar Comida")
        resultado_ce = f"BRADICINESIA"
        cuenta_bradicinesia += 1
        print(f"Posible bradicinesia detectada en {pacientes[int(i/10)]} realizando la tarea Cortar Comida")
    else: 
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Cortar Comida")
        resultado_ce = f"NO BRADICINESIA"
        print(f"{pacientes[int(i/10)]} libre de bradicinesia realizando la tarea Cortar Comida")

    if (resultados_paciente_dict['TiempoMedio'][4+i] > (tiemposMedExp_sujeto_dict['TiempoMedio'][4] + diff_ef/2)):
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Comer")
        resultado_ef = f"BRADICINESIA"
        cuenta_bradicinesia += 1
        print(f"Posible bradicinesia detectada en {pacientes[int(i/10)]} realizando la tarea Comer")
    else: 
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Comer")
        resultado_ef = f"NO BRADICINESIA"
        print(f"{pacientes[int(i/10)]} libre de bradicinesia realizando la tarea Comer")

    if (resultados_paciente_dict['TiempoMedio'][5+i] > (tiemposMedExp_sujeto_dict['TiempoMedio'][5] + diff_ot/2)):
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Abrir/Cerrar Caja")
        resultado_ot = f"BRADICINESIA"
        cuenta_bradicinesia += 1
        print(f"Posible bradicinesia detectada en {pacientes[int(i/10)]} realizando la tarea Abrir/Cerrar Caja")
    else: 
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Abrir/Cerrar Caja")
        resultado_ot = f"NO BRADICINESIA"
        print(f"{pacientes[int(i/10)]} libre de bradicinesia realizando la tarea Abrir/Cerrar Caja")
        
    if (resultados_paciente_dict['TiempoMedio'][6+i] > (tiemposMedExp_sujeto_dict['TiempoMedio'][6] + diff_sd/2)):
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Beber")
        resultado_sd = f"BRADICINESIA"
        cuenta_bradicinesia += 1
        print(f"Posible bradicinesia detectada en {pacientes[int(i/10)]} realizando la tarea Beber")
    else: 
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Beber")
        resultado_sd = f"NO BRADICINESIA"
        print(f"{pacientes[int(i/10)]} libre de bradicinesia realizando la tarea Beber")

    if (resultados_paciente_dict['TiempoMedio'][7+i] > (tiemposMedExp_sujeto_dict['TiempoMedio'][7] + diff_sn/2)):
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Firmar")
        resultado_sn = f"BRADICINESIA"
        cuenta_bradicinesia += 1
        print(f"Posible bradicinesia detectada en {pacientes[int(i/10)]} realizando la tarea Firmar")
    else: 
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Firmar")
        resultado_sn = f"NO BRADICINESIA"
        print(f"{pacientes[int(i/10)]} libre de bradicinesia realizando la tarea Firmar")

    if (resultados_paciente_dict['TiempoMedio'][8+i] > (tiemposMedExp_sujeto_dict['TiempoMedio'][8] + diff_tb/2)):
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Pasar Pagina")
        resultado_tb = f"BRADICINESIA"
        cuenta_bradicinesia += 1
        print(f"Posible bradicinesia detectada en {pacientes[int(i/10)]} realizando la tarea Pasar Pagina")
    else: 
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Pasar Pagina")
        resultado_tb = f"NO BRADICINESIA"
        print(f"{pacientes[int(i/10)]} libre de bradicinesia realizando la tarea Pasar Pagina")

    if (resultados_paciente_dict['TiempoMedio'][9+i] > (tiemposMedExp_sujeto_dict['TiempoMedio'][9] + diff_td/2)):
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Abrir/Cerrar Puerta")
        resultado_td = f"BRADICINESIA"
        cuenta_bradicinesia += 1
        print(f"Posible bradicinesia detectada en {pacientes[int(i/10)]} realizando la tarea Abrir/Cerrar Puerta")
    else: 
        resultados_guardados['Paciente'].append(pacientes[int(i/10)])
        resultados_guardados['Tarea'].append(f"Abrir/Cerrar Puerta")
        resultado_td = f"NO BRADICINESIA"
        print(f"{pacientes[int(i/10)]} libre de bradicinesia realizando la tarea Abrir/Cerrar Puerta")
    
    resultados_guardados['Resultado'].append(resultado_bb)
    resultados_guardados['Resultado'].append(resultado_bt)
    resultados_guardados['Resultado'].append(resultado_cb)
    resultados_guardados['Resultado'].append(resultado_ce)
    resultados_guardados['Resultado'].append(resultado_ef)
    resultados_guardados['Resultado'].append(resultado_ot)
    resultados_guardados['Resultado'].append(resultado_sd)
    resultados_guardados['Resultado'].append(resultado_sn)
    resultados_guardados['Resultado'].append(resultado_tb)
    resultados_guardados['Resultado'].append(resultado_td) 

    resultados_guardados['Paciente'].append(f"Total: ")
    resultados_guardados['Tarea'].append(f"Bradicinesia en {cuenta_bradicinesia} tareas")
    if (cuenta_bradicinesia > 5):
        resultados_guardados['Resultado'].append(f"Es posible que el paciente tenga bradicinesia") 
    else: 
        resultados_guardados['Resultado'].append(f"Paciente libre de bradicinesia")

    resultados_guardados['Paciente'].append(f"")
    resultados_guardados['Tarea'].append(f"")
    resultados_guardados['Resultado'].append(f"") 

resultados_finales_df = pd.DataFrame(resultados_guardados)
resultados_finales_df.to_excel('resultados_finales.xlsx', index=False)

# print(resultados_obtenidos)
































# ********************DEBUG********************
# DATOS PARTICIPANTE 
# participante = 'LauraRomeroCrespo'
# experimento = 'bb'
# tipo_dato0 = 'gyroscope-0'
# tipo_dato1 = 'gyroscope-1'
# tipo_dato2 = 'gyroscope-2'

# # Acceder a los datos
# data0 = datos_sujeto[participante][experimento][tipo_dato0]
# data1 = datos_sujeto[participante][experimento][tipo_dato1]
# data2 = datos_sujeto[participante][experimento][tipo_dato2]

# # data0[:170] = 0
# # data1[:170] = 0
# # data2[:170] = 0

# # data0 = datos_paciente[participante][experimento][tipo_dato0]
# # data1 = datos_paciente[participante][experimento][tipo_dato1]
# # data2 = datos_paciente[participante][experimento][tipo_dato2]

# # data0 = pd.read_csv(data_path0)
# data0['magnitude0'] = compute_magnitude(data0)
# # data0['magnitude0'] = compute_magnitude(data0[100:])

# # data1 = pd.read_csv(data_path1)
# data1['magnitude1'] = compute_magnitude(data1)

# # data2 = pd.read_csv(data_path2)
# data2['magnitude2'] = compute_magnitude(data2)

# # print(data0)
# # print(data1)
# # print(data2)

# # Find the top two peaks with at least 1 second separation
# top_2_indices0 = find_absolute_top_2_peaks_with_separation_100(data0['magnitude0'].values, min_samples_separation=34) 
# top_2_indices1 = find_absolute_top_2_peaks_with_separation_100(data1['magnitude1'].values, min_samples_separation=34) 
# top_2_indices2 = find_absolute_top_2_peaks_with_separation_100(data2['magnitude2'].values, min_samples_separation=34) 
# print(top_2_indices0)

# # Crear una sola figura para mostrar ambos picos
# plt.figure()

# # Gráfico de la magnitud
# plt.plot(data0['magnitude0'], label='Magnitud Muestra 0')
# plt.scatter(top_2_indices0, data0['magnitude0'][top_2_indices0], color='red', label='Picos Muestra 0')

# # Personalizar la leyenda
# plt.legend()

# # Título y etiquetas de los ejes
# plt.title('Repeticion 0 de la tarea')
# plt.xlabel('Muestra')
# plt.ylabel('Magnitud')

# plt.figure()
# plt.plot(data1['magnitude1'], label='Magnitud Muestra 1')
# plt.scatter(top_2_indices1, data1['magnitude1'][top_2_indices1], color='red', label='Picos Muestra 1')

# # Personalizar la leyenda
# plt.legend()

# # Título y etiquetas de los ejes
# plt.title('Repeticion 1 de la tarea')
# plt.xlabel('Muestra')
# plt.ylabel('Magnitud')

# plt.figure()
# plt.plot(data2['magnitude2'], label='Magnitud Muestra 2')
# plt.scatter(top_2_indices2, data2['magnitude2'][top_2_indices2], color='red', label='Picos Muestra 2')

# plt.legend()

# # Título y etiquetas de los ejes
# plt.title('Repeticion 2 de la tarea')
# plt.xlabel('Muestra')
# plt.ylabel('Magnitud')

# plt.show()

# # Print the distance in milliseconds between the two peaks
# distance_in_samples0 = abs(top_2_indices0[1] - top_2_indices0[0])
# distance_in_milliseconds0 = distance_in_samples0 * 30
# distance_in_seconds0 = distance_in_milliseconds0 / 1000
# print(f"Tiempo que duró la Repetición 1: {distance_in_seconds0} segundos")

# distance_in_samples1 = abs(top_2_indices1[1] - top_2_indices1[0])
# distance_in_milliseconds1 = distance_in_samples1 * 30
# distance_in_seconds1 = distance_in_milliseconds1 / 1000
# print(f"Tiempo que duró la Repetición 2: {distance_in_seconds1} segundos")

# distance_in_samples2 = abs(top_2_indices2[1] - top_2_indices2[0])
# distance_in_milliseconds2 = distance_in_samples2 * 30
# distance_in_seconds2 = distance_in_milliseconds2 / 1000
# print(f"Tiempo que duró la Repetición 3: {distance_in_seconds2} segundos")

# duracionTarea = (distance_in_seconds0 + distance_in_seconds1 + distance_in_seconds2) / 3;

# print(f"El participante tardó {duracionTarea} segundos en realizar la tarea")
