import pandas as pd
import numpy as np
from scipy import signal
from scipy.signal import hilbert, find_peaks
import matplotlib.pyplot as plt
import glob
import os

# Directorios
directorio_sujetos = 'SujetosSanos'
directorio_pacientes = 'Pacientes'
directorio_participantes = 'Participantes'

# Listas de participantes
sujetos = ['AlvaroBasterraGarcia', 'CO_DoloresDominguezJimenez', 'CO_MariaLuisaMayorAndujar', 'CristinaBayon', 'DianaJimenez',
                  'JavierGavilanes', 'lab11', 'lab12', 'lab13', 'lab14', 'lab15', 'lab16', 'LauraGarciaSanchez',
                  'LauraRomeroCrespo', 'LorenaAricetaGarcia', 'LuciaDoradoGonzalez', 'MariaLorenzo', 'MiriamMugicaEsteve', 'SabelaAraSolla']

# sujetos = ['CristinaBayon', 'lab11', 'lab12', 'lab13', 'lab14', 'lab15', 'lab16', 'LauraRomeroCrespo', 'LuciaDoradoGonzalez', 'MariaLorenzo', 'MiriamMugicaEsteve']

pacientes = ['ET_FranciscoMorenoCastillo', 'ET_MariaDelCarmenDelEspinoCruz', 'ET_SantosRodriguezSanchez', 'PD_FranciscoPorrasLopez',
             'PD_JoseAntonioOrtizBaeza', 'PD_JulianMonteroSanchez', 'PD_MariaDelPilarGaleotaPozo']

participantes = ['AlvaroBasterraGarcia', 'CO_DoloresDominguezJimenez', 'CO_MariaLuisaMayorAndujar', 'CristinaBayon', 'DianaJimenez',
                    'JavierGavilanes', 'lab11', 'lab12', 'lab13', 'lab14', 'lab15', 'lab16', 'LauraGarciaSanchez',
                    'LauraRomeroCrespo', 'LorenaAricetaGarcia', 'LuciaDoradoGonzalez', 'MariaLorenzo', 'MiriamMugicaEsteve', 'SabelaAraSolla', 
                    'ET_FranciscoMorenoCastillo', 'ET_MariaDelCarmenDelEspinoCruz', 'ET_SantosRodriguezSanchez', 'PD_FranciscoPorrasLopez',
                    'PD_JoseAntonioOrtizBaeza', 'PD_JulianMonteroSanchez', 'PD_MariaDelPilarGaleotaPozo']

# Lista de experimentos
experimentos = ['bb', 'bt', 'cb', 'ce', 'ef', 'ot', 'sd', 'sn', 'tb', 'td']

# Lista de tipos de datos disponibles
datos_disponibles = ['accelerometer-0', 'accelerometer-1', 'accelerometer-2']

# Estructuras para almacenar los datos
datos_sujeto = {}
datos_participante = {}
datos_paciente = {}

# Variables para almacenar los resultados
resultados_participante = []
resultados_experimento = []
resultados_potencia_maxima = []
resultados_frecuencia_dominante = []
resultados_espec_part_dict = {'Participante': [], 'Experimento': [], 'Potencia Espectral Máxima': [], 'Frecuencia Dominante (Hz)': []}
resultados_espec_suj_dict = {'Sujeto': [], 'Experimento': [], 'Potencia Espectral Máxima': [], 'Frecuencia Dominante (Hz)': []}
cuenta_resultado = 0
cuenta_tarea = 1

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


for participante in participantes:
    datos_participante[participante] = {}
    for experimento in experimentos:
        datos_participante[participante][experimento] = {}
        for tipo_dato in datos_disponibles:

            nombre_archivo = f'{tipo_dato}.csv'

            ruta_datos = os.path.join(directorio_participantes, participante, experimento)
            archivos = [archivo for archivo in os.listdir(ruta_datos) if nombre_archivo in archivo]
            
            if archivos:
                ruta_datos_completa = os.path.join(ruta_datos, archivos[0])
                datos = pd.read_csv(ruta_datos_completa)
                datos_participante[participante][experimento][tipo_dato] = datos


for sujeto in sujetos:
    for experimento in experimentos:
        for tipo_dato in datos_disponibles:

            grosor_linea = 0.6
            datos = datos_sujeto[sujeto][experimento][tipo_dato]

            timestamp = datos['timestamp']
            aceleracion_x = datos['x']
            aceleracion_y = datos['y']
            aceleracion_z = datos['z']

            # Plotear en el dominio del tiempo antes del filtro
            plt.figure(figsize=(12, 6))
            plt.subplot(2, 3, 1)
            # plt.plot(timestamp, aceleracion_x, linewidth=grosor_linea)
            # plt.plot(timestamp, aceleracion_y, linewidth=grosor_linea)
            plt.plot(timestamp, aceleracion_z, linewidth=grosor_linea)
            plt.title('Dominio del tiempo (antes del filtro)')
            plt.xlabel('Tiempo')
            plt.ylabel('Aceleración')

            # Aplicación de filtros
            fs = 30.0  

            frecuencia_corte_HP = 0.05  # Frecuencia de corte en Hz
            frecuencia_corte_LP = 3.5 
            frecuencia_corte_HP_norm = frecuencia_corte_HP / (0.5 * fs)
            frecuencia_corte_LP_norm = frecuencia_corte_LP / (0.5 * fs)

            b, a = signal.butter(N=4, Wn=frecuencia_corte_HP_norm, btype='high', analog=False)
            d, c = signal.butter(N=4, Wn=frecuencia_corte_LP_norm, btype='low', analog=False)

            aceleracion_x_filtrada_HP = signal.filtfilt(b, a, aceleracion_x)
            aceleracion_y_filtrada_HP = signal.filtfilt(b, a, aceleracion_y)
            aceleracion_z_filtrada_HP = signal.filtfilt(b, a, aceleracion_z)

            aceleracion_x_filtrada_LP = signal.filtfilt(d, c, aceleracion_x_filtrada_HP)
            aceleracion_y_filtrada_LP = signal.filtfilt(d, c, aceleracion_y_filtrada_HP)
            aceleracion_z_filtrada_LP = signal.filtfilt(d, c, aceleracion_z_filtrada_HP)

            # Plotear en el dominio del tiempo después del filtro
            plt.subplot(2, 3, 2)
            # plt.plot(timestamp, aceleracion_x_filtrada_HP, linewidth=grosor_linea)
            # plt.plot(timestamp, aceleracion_y_filtrada_HP, linewidth=grosor_linea)
            plt.plot(timestamp, aceleracion_z_filtrada_HP, linewidth=grosor_linea)
            plt.title('Dominio del tiempo (después del primer filtro)')
            plt.xlabel('Tiempo')
            plt.ylabel('Aceleración')

            # Plotear en el dominio de la frecuencia antes del filtro
            plt.subplot(2, 3, 3)
            # plt.plot(timestamp, aceleracion_x_filtrada_LP, linewidth=grosor_linea)
            # plt.plot(timestamp, aceleracion_y_filtrada_LP, linewidth=grosor_linea)
            plt.plot(timestamp, aceleracion_z_filtrada_LP, linewidth=grosor_linea)
            plt.title('Dominio del tiempo (después del segundo filtro)')
            plt.xlabel('Tiempo')
            plt.ylabel('Aceleración')

            # Plotear en el dominio de la frecuencia después del filtro
            plt.subplot(2, 3, 4)
            fx, Pxxx = signal.periodogram(aceleracion_x, fs)
            fy, Pxxy = signal.periodogram(aceleracion_y, fs)
            fz, Pxxz = signal.periodogram(aceleracion_z, fs)

            Pxxx_dB = 10 * np.log10(Pxxx)
            Pxxy_dB = 10 * np.log10(Pxxy)
            Pxxz_dB = 10 * np.log10(Pxxz)

            # Trazar en escala logarítmica
            plt.semilogy(fx, Pxxx_dB, linewidth=grosor_linea, label='Aceleración X')
            plt.semilogy(fy, Pxxy_dB, linewidth=grosor_linea, label='Aceleración Y')
            plt.semilogy(fz, Pxxz_dB, linewidth=grosor_linea, label='Aceleración Z')

            plt.title('Dominio de la frecuencia (antes del filtro)')
            plt.xlabel('Frecuencia (Hz)')
            plt.ylabel('Potencia espectral')

            # Plotear en el dominio de la frecuencia antes del filtro
            plt.subplot(2, 3, 5)
            fx, Pxxx_filtrado_HP = signal.periodogram(aceleracion_x_filtrada_HP, fs)
            fy, Pxxy_filtrado_HP = signal.periodogram(aceleracion_y_filtrada_HP, fs)
            fz, Pxxz_filtrado_HP = signal.periodogram(aceleracion_z_filtrada_HP, fs)

            Pxxx_dB = 10 * np.log10(Pxxx_filtrado_HP)
            Pxxy_dB = 10 * np.log10(Pxxy_filtrado_HP)
            Pxxz_dB = 10 * np.log10(Pxxz_filtrado_HP)

            # Trazar en escala logarítmica
            plt.semilogy(fx, Pxxx_dB, linewidth=grosor_linea, label='Aceleración X')
            plt.semilogy(fy, Pxxy_dB, linewidth=grosor_linea, label='Aceleración Y')
            plt.semilogy(fz, Pxxz_dB, linewidth=grosor_linea, label='Aceleración Z')

            plt.title('Dominio de la frecuencia (después del primer filtro)')
            plt.xlabel('Frecuencia (Hz)')
            plt.ylabel('Potencia espectral')

            # Plotear en el dominio de la frecuencia después del filtro
            plt.subplot(2, 3, 6)

            fx, Pxxx_filtrado_LP = signal.periodogram(aceleracion_x_filtrada_LP, fs)
            fy, Pxxy_filtrado_LP = signal.periodogram(aceleracion_y_filtrada_LP, fs)
            fz, Pxxz_filtrado_LP = signal.periodogram(aceleracion_z_filtrada_LP, fs)

            Pxxx_dB = 10 * np.log10(Pxxx_filtrado_LP)
            Pxxy_dB = 10 * np.log10(Pxxy_filtrado_LP)
            Pxxz_dB = 10 * np.log10(Pxxz_filtrado_LP)

            f_min = 0.05
            f_max = 3.5
            dB_min_zoom = 10
            dB_max_zoom = 70

            # Convertir frecuencias a índices
            idx_min = np.argmax(fx >= f_min)
            idx_max = np.argmax(fx >= f_max)

            # Trazar en escala logarítmica
            plt.semilogy(fx, Pxxx_dB, linewidth=grosor_linea, label='Aceleración X')
            plt.semilogy(fy, Pxxy_dB, linewidth=grosor_linea, label='Aceleración Y')
            plt.semilogy(fz, Pxxz_dB, linewidth=grosor_linea, label='Aceleración Z')

            # Seleccionar una región de interés
            plt.xlim(f_min, f_max)
            plt.ylim(dB_min_zoom, dB_max_zoom)

            plt.xlabel('Frecuencia (Hz)')
            plt.ylabel('PSD (dB/Hz)')
            plt.legend()
            plt.grid(True)

            plt.title('Dominio de la frecuencia después del segundo filtro')
            plt.xlabel('Frecuencia (Hz)')
            plt.ylabel('Potencia espectral')

            plt.tight_layout()

            # Índice del máximo para cada señal
            idx_max_x = np.argmax(Pxxx_dB)
            idx_max_y = np.argmax(Pxxy_dB)
            idx_max_z = np.argmax(Pxxz_dB)

            # Frecuencias correspondientes a esos índices
            f_max_x = fx[idx_max_x]
            f_max_y = fy[idx_max_y]
            f_max_z = fz[idx_max_z]

            # Sacar los resultados por terminal
            print(f'RESULTADOS del Participante {sujeto} realizando el experimento {experimento}')

            print(f'Máximo en aceleración X: {Pxxx_dB[idx_max_x]} dB/Hz en {f_max_x} Hz')
            print(f'Máximo en aceleración Y: {Pxxy_dB[idx_max_y]} dB/Hz en {f_max_y} Hz')
            print(f'Máximo en aceleración Z: {Pxxz_dB[idx_max_z]} dB/Hz en {f_max_z} Hz')

            max_power = np.maximum.reduce([Pxxx_dB[idx_max_x], Pxxy_dB[idx_max_y], Pxxz_dB[idx_max_z]])

            print()
            
            if(max_power == Pxxx_dB[idx_max_x]):
                print(f'El dato que se tendrá en cuenta para medir la Bradicinesia es: Aceleración en el Eje X')
            elif(max_power == Pxxy_dB[idx_max_y]):
                print(f'El dato que se tendrá en cuenta para medir la Bradicinesia es: Aceleración en el Eje Y')
            elif(max_power == Pxxz_dB[idx_max_z]):
                print(f'El dato que se tendrá en cuenta para medir la Bradicinesia es: Aceleración en el Eje Z') 

            # Agregar resultados a las listas
            # resultados_participante.append(participante)
            # resultados_experimento.append(experimento)
            resultados_potencia_maxima.append(max_power)
            resultados_frecuencia_dominante.append(f_max_x if max_power == Pxxx_dB[idx_max_x] else (f_max_y if max_power == Pxxy_dB[idx_max_y] else f_max_z))

            cuenta_resultado += 1

            if cuenta_resultado % 3 == 0:
                resultados_potencia_maxima = resultados_potencia_maxima[-3:]
                resultados_frecuencia_dominante = resultados_frecuencia_dominante[-3:]
                potencia_maxima = sum(resultados_potencia_maxima) / 3
                frecuencia_dominante = sum(resultados_frecuencia_dominante) / 3

                # Agregar datos al diccionario
                resultados_espec_suj_dict['Sujeto'].append(sujeto)
                resultados_espec_suj_dict['Experimento'].append(experimento)
                resultados_espec_suj_dict['Potencia Espectral Máxima'].append(potencia_maxima)
                resultados_espec_suj_dict['Frecuencia Dominante (Hz)'].append(frecuencia_dominante)

                cuenta_resultado = 0
                cuenta_tarea += 1
                 
            plt.show()



for participante in participantes:
    for experimento in experimentos:
        for tipo_dato in datos_disponibles:

            grosor_linea = 0.6
            datos = datos_participante[participante][experimento][tipo_dato]

            timestamp = datos['timestamp']
            aceleracion_x = datos['x']
            aceleracion_y = datos['y']
            aceleracion_z = datos['z']

            # Plotear en el dominio del tiempo antes del filtro
            plt.figure(figsize=(12, 6))
            plt.subplot(2, 3, 1)
            # plt.plot(timestamp, aceleracion_x, linewidth=grosor_linea)
            # plt.plot(timestamp, aceleracion_y, linewidth=grosor_linea)
            plt.plot(timestamp, aceleracion_z, linewidth=grosor_linea)
            plt.title('Dominio del tiempo (antes del filtro)')
            plt.xlabel('Tiempo')
            plt.ylabel('Aceleración')

            # Aplicación de filtros
            fs = 30.0  

            frecuencia_corte_HP = 0.05  
            frecuencia_corte_LP = 3.5 
            frecuencia_corte_HP_norm = frecuencia_corte_HP / (0.5 * fs)
            frecuencia_corte_LP_norm = frecuencia_corte_LP / (0.5 * fs)

            b, a = signal.butter(N=4, Wn=frecuencia_corte_HP_norm, btype='high', analog=False)
            d, c = signal.butter(N=4, Wn=frecuencia_corte_LP_norm, btype='low', analog=False)

            aceleracion_x_filtrada_HP = signal.filtfilt(b, a, aceleracion_x)
            aceleracion_y_filtrada_HP = signal.filtfilt(b, a, aceleracion_y)
            aceleracion_z_filtrada_HP = signal.filtfilt(b, a, aceleracion_z)

            aceleracion_x_filtrada_LP = signal.filtfilt(d, c, aceleracion_x_filtrada_HP)
            aceleracion_y_filtrada_LP = signal.filtfilt(d, c, aceleracion_y_filtrada_HP)
            aceleracion_z_filtrada_LP = signal.filtfilt(d, c, aceleracion_z_filtrada_HP)

            # Plotear en el dominio del tiempo después del filtro
            plt.subplot(2, 3, 2)
            # plt.plot(timestamp, aceleracion_x_filtrada_HP, linewidth=grosor_linea)
            # plt.plot(timestamp, aceleracion_y_filtrada_HP, linewidth=grosor_linea)
            plt.plot(timestamp, aceleracion_z_filtrada_HP, linewidth=grosor_linea)
            plt.title('Dominio del tiempo (después del primer filtro)')
            plt.xlabel('Tiempo')
            plt.ylabel('Aceleración')

            # Plotear en el dominio de la frecuencia antes del filtro
            plt.subplot(2, 3, 3)
            # plt.plot(timestamp, aceleracion_x_filtrada_LP, linewidth=grosor_linea)
            # plt.plot(timestamp, aceleracion_y_filtrada_LP, linewidth=grosor_linea)
            plt.plot(timestamp, aceleracion_z_filtrada_LP, linewidth=grosor_linea)
            plt.title('Dominio del tiempo (después del segundo filtro)')
            plt.xlabel('Tiempo')
            plt.ylabel('Aceleración')

            # Plotear en el dominio de la frecuencia después del filtro
            plt.subplot(2, 3, 4)
            fx, Pxxx = signal.periodogram(aceleracion_x, fs)
            fy, Pxxy = signal.periodogram(aceleracion_y, fs)
            fz, Pxxz = signal.periodogram(aceleracion_z, fs)

            Pxxx_dB = 10 * np.log10(Pxxx)
            Pxxy_dB = 10 * np.log10(Pxxy)
            Pxxz_dB = 10 * np.log10(Pxxz)

            # Trazar en escala logarítmica
            plt.semilogy(fx, Pxxx_dB, linewidth=grosor_linea, label='Aceleración X')
            plt.semilogy(fy, Pxxy_dB, linewidth=grosor_linea, label='Aceleración Y')
            plt.semilogy(fz, Pxxz_dB, linewidth=grosor_linea, label='Aceleración Z')

            plt.title('Dominio de la frecuencia (antes del filtro)')
            plt.xlabel('Frecuencia (Hz)')
            plt.ylabel('Potencia espectral')

            # Plotear en el dominio de la frecuencia antes del filtro
            plt.subplot(2, 3, 5)
            fx, Pxxx_filtrado_HP = signal.periodogram(aceleracion_x_filtrada_HP, fs)
            fy, Pxxy_filtrado_HP = signal.periodogram(aceleracion_y_filtrada_HP, fs)
            fz, Pxxz_filtrado_HP = signal.periodogram(aceleracion_z_filtrada_HP, fs)

            Pxxx_dB = 10 * np.log10(Pxxx_filtrado_HP)
            Pxxy_dB = 10 * np.log10(Pxxy_filtrado_HP)
            Pxxz_dB = 10 * np.log10(Pxxz_filtrado_HP)

            # Trazar en escala logarítmica
            plt.semilogy(fx, Pxxx_dB, linewidth=grosor_linea, label='Aceleración X')
            plt.semilogy(fy, Pxxy_dB, linewidth=grosor_linea, label='Aceleración Y')
            plt.semilogy(fz, Pxxz_dB, linewidth=grosor_linea, label='Aceleración Z')

            plt.title('Dominio de la frecuencia (después del primer filtro)')
            plt.xlabel('Frecuencia (Hz)')
            plt.ylabel('Potencia espectral')

            # Plotear en el dominio de la frecuencia después del filtro
            plt.subplot(2, 3, 6)

            fx, Pxxx_filtrado_LP = signal.periodogram(aceleracion_x_filtrada_LP, fs)
            fy, Pxxy_filtrado_LP = signal.periodogram(aceleracion_y_filtrada_LP, fs)
            fz, Pxxz_filtrado_LP = signal.periodogram(aceleracion_z_filtrada_LP, fs)

            Pxxx_dB = 10 * np.log10(Pxxx_filtrado_LP)
            Pxxy_dB = 10 * np.log10(Pxxy_filtrado_LP)
            Pxxz_dB = 10 * np.log10(Pxxz_filtrado_LP)

            f_min = 0.05
            f_max = 3.5
            dB_min_zoom = 10
            dB_max_zoom = 70

            # Convertir frecuencias a índices
            idx_min = np.argmax(fx >= f_min)
            idx_max = np.argmax(fx >= f_max)

            # Trazar en escala logarítmica
            plt.semilogy(fx, Pxxx_dB, linewidth=grosor_linea, label='Aceleración X')
            plt.semilogy(fy, Pxxy_dB, linewidth=grosor_linea, label='Aceleración Y')
            plt.semilogy(fz, Pxxz_dB, linewidth=grosor_linea, label='Aceleración Z')

            # Seleccionar una región de interés
            plt.xlim(f_min, f_max)
            plt.ylim(dB_min_zoom, dB_max_zoom)

            plt.xlabel('Frecuencia (Hz)')
            plt.ylabel('PSD (dB/Hz)')
            plt.legend()
            plt.grid(True)

            plt.title('Dominio de la frecuencia (después del segundo filtro)')
            plt.xlabel('Frecuencia (Hz)')
            plt.ylabel('Potencia espectral')

            plt.tight_layout()

            # Índice del máximo para cada señal
            idx_max_x = np.argmax(Pxxx_dB)
            idx_max_y = np.argmax(Pxxy_dB)
            idx_max_z = np.argmax(Pxxz_dB)

            # Frecuencias correspondientes a esos índices
            f_max_x = fx[idx_max_x]
            f_max_y = fy[idx_max_y]
            f_max_z = fz[idx_max_z]

            # Sacar los resultados por terminal
            print(f'RESULTADOS del Participante {participante} realizando el experimento {experimento}')

            print(f'Máximo en aceleración X: {Pxxx_dB[idx_max_x]} dB/Hz en {f_max_x} Hz')
            print(f'Máximo en aceleración Y: {Pxxy_dB[idx_max_y]} dB/Hz en {f_max_y} Hz')
            print(f'Máximo en aceleración Z: {Pxxz_dB[idx_max_z]} dB/Hz en {f_max_z} Hz')

            max_power = np.maximum.reduce([Pxxx_dB[idx_max_x], Pxxy_dB[idx_max_y], Pxxz_dB[idx_max_z]])

            print()
            
            if(max_power == Pxxx_dB[idx_max_x]):
                print(f'El dato que se tendrá en cuenta para medir la Bradicinesia es: Aceleración en el Eje X')
            elif(max_power == Pxxy_dB[idx_max_y]):
                print(f'El dato que se tendrá en cuenta para medir la Bradicinesia es: Aceleración en el Eje Y')
            elif(max_power == Pxxz_dB[idx_max_z]):
                print(f'El dato que se tendrá en cuenta para medir la Bradicinesia es: Aceleración en el Eje Z') 

            # Agregar resultados a las listas
            # resultados_participante.append(participante)
            # resultados_experimento.append(experimento)
            resultados_potencia_maxima.append(max_power)
            resultados_frecuencia_dominante.append(f_max_x if max_power == Pxxx_dB[idx_max_x] else (f_max_y if max_power == Pxxy_dB[idx_max_y] else f_max_z))

            cuenta_resultado += 1

            if cuenta_resultado % 3 == 0:
                resultados_potencia_maxima = resultados_potencia_maxima[-3:]
                resultados_frecuencia_dominante = resultados_frecuencia_dominante[-3:]
                potencia_maxima = sum(resultados_potencia_maxima) / 3
                frecuencia_dominante = sum(resultados_frecuencia_dominante) / 3

                # Agregar datos al diccionario
                resultados_espec_part_dict['Participante'].append(participante)
                resultados_espec_part_dict['Experimento'].append(experimento)
                resultados_espec_part_dict['Potencia Espectral Máxima'].append(potencia_maxima)
                resultados_espec_part_dict['Frecuencia Dominante (Hz)'].append(frecuencia_dominante)

                cuenta_resultado = 0
                cuenta_tarea += 1
                 
            # plt.show()


# Crear un DataFrame con los resultados
df_resultados_part = pd.DataFrame({
    'Participante': resultados_espec_part_dict['Participante'],
    'Experimento': resultados_espec_part_dict['Experimento'],
    'PotenciaEspectralMaxima': resultados_espec_part_dict['Potencia Espectral Máxima'],
    'FrecuenciaDominante': resultados_espec_part_dict['Frecuencia Dominante (Hz)']
})

df_resultados_suj = pd.DataFrame({
    'Experimento': resultados_espec_suj_dict['Experimento'],
    'PotenciaEspectralMaxima': resultados_espec_suj_dict['Potencia Espectral Máxima'],
    'FrecuenciaDominante': resultados_espec_suj_dict['Frecuencia Dominante (Hz)']
})

# Guardar el DataFrame en un archivo Excel y otro csv
df_resultados_part.to_excel('resultadosParticipantesPotenciaEspectral.xlsx', index=False)
df_resultados_part.to_csv('resultadosParticipantesPotenciaEspectral.csv', index=False)
df_resultados_suj.to_excel('resultadosSujetosPotenciaEspectral.xlsx', index=False)

# Convertir las columnas relevantes a tipo numérico si no lo son
df_resultados_part['PotenciaEspectralMaxima'] = pd.to_numeric(df_resultados_part['PotenciaEspectralMaxima'], errors='coerce')
df_resultados_part['FrecuenciaDominante'] = pd.to_numeric(df_resultados_part['FrecuenciaDominante'], errors='coerce')

media_por_experimento = df_resultados_suj.groupby('Experimento').mean()
media_por_experimento.to_excel('mediasSujetosPotenciaEspectral.xlsx', index=False)
media_por_experimento.to_csv('mediasSujetosPotenciaEspectral.csv', index=False)























## ESPECTRO DE POTENCIA FUNCIONANDO PARA 1 PACIENTE

# import pandas as pd
# import numpy as np
# from scipy import signal
# from scipy.signal import hilbert, find_peaks
# import matplotlib.pyplot as plt
# import glob
# import os

# # Directorios
# directorio_sujetos = 'SujetosSanos'
# directorio_pacientes = 'Pacientes'

# # Definir la lista de participantes
# # sujetos = ['AlvaroBasterraGarcia', 'CO_DoloresDominguezJimenez', 'CO_MariaLuisaMayorAndujar', 'CristinaBayon', 'DianaJimenez',
# #                  'JavierGavilanes', 'lab11', 'lab12', 'lab13', 'lab14', 'lab15', 'lab16', 'LauraGarciaSanchez',
# #                  'LauraRomeroCrespo', 'LorenaAricetaGarcia', 'LuciaDoradoGonzalez', 'MariaLorenzo', 'MiriamMugicaEsteve', 'SabelaAraSolla']

# sujetos = ['CristinaBayon', 'lab11', 'lab12', 'lab13', 'lab14', 'lab15', 'lab16', 'LauraRomeroCrespo', 'LuciaDoradoGonzalez', 'MariaLorenzo', 'MiriamMugicaEsteve']

# pacientes = ['ET_FranciscoMorenoCastillo', 'ET_MariaDelCarmenDelEspinoCruz', 'ET_SantosRodriguezSanchez', 'PD_FranciscoPorrasLopez',
#              'PD_JoseAntonioOrtizBaeza', 'PD_JulianMonteroSanchez', 'PD_MariaDelPilarGaleotaPozo']

# # Definir la lista de experimentos
# experimentos = ['bb', 'bt', 'cb', 'ce', 'ef', 'ot', 'sd', 'sn', 'tb', 'td']

# # Definir la lista de tipos de datos disponibles
# datos_disponibles = ['accelerometer-0', 'accelerometer-1', 'accelerometer-2']

# # Crear una estructura de datos para almacenar los datos
# datos_sujeto = {}
# datos_paciente = {}

# # Crear un diccionario para almacenar los resultados
# resultados_sujeto_dict = {'Sujeto': [], 'Experimento': [], 'TiempoMedio (s)': [], 'TiempoMaximo (s)': []}
# resultados_paciente_dict = {'Paciente': [], 'Experimento': [], 'TiempoMedio (s)': []}
# tiemposMedExp_sujeto_dict = {'Experimento': [], 'TiempoMedio (s)': []}
# tiemposMedExp_paciente_dict = {'Experimento': [], 'TiempoMedio (s)': []}

# for sujeto in sujetos:
#     datos_sujeto[sujeto] = {}
#     for experimento in experimentos:
#         datos_sujeto[sujeto][experimento] = {}
#         for tipo_dato in datos_disponibles:
#             # Crear el patrón de búsqueda del nombre del archivo
#             nombre_archivo = f'{tipo_dato}.csv'
#             # Buscar archivos que coincidan con el patrón
#             ruta_datos = os.path.join(directorio_sujetos, sujeto, experimento)
#             archivos = [archivo for archivo in os.listdir(ruta_datos) if nombre_archivo in archivo]
            
#             if archivos:
#                 # Si se encuentran archivos, cargar el primero (puedes adaptar esto según tus necesidades)
#                 ruta_datos_completa = os.path.join(ruta_datos, archivos[0])
#                 datos = pd.read_csv(ruta_datos_completa)
#                 datos_sujeto[sujeto][experimento][tipo_dato] = datos

# for paciente in pacientes:
#     datos_paciente[paciente] = {}
#     for experimento in experimentos:
#         datos_paciente[paciente][experimento] = {}
#         for tipo_dato in datos_disponibles:
#             # Crear el patrón de búsqueda del nombre del archivo
#             nombre_archivo = f'{tipo_dato}.csv'
#             # Buscar archivos que coincidan con el patrón
#             ruta_datos = os.path.join(directorio_pacientes, paciente, experimento)
#             archivos = [archivo for archivo in os.listdir(ruta_datos) if nombre_archivo in archivo]
            
#             if archivos:
#                 # Si se encuentran archivos, cargar el primero (puedes adaptar esto según tus necesidades)
#                 ruta_datos_completa = os.path.join(ruta_datos, archivos[0])
#                 datos = pd.read_csv(ruta_datos_completa)
#                 datos_paciente[paciente][experimento][tipo_dato] = datos

# sujeto = 'lab11'
# experimento = 'bb'
# tipo_dato = 'accelerometer-0'
# grosor_linea = 0.6
# datos = datos_sujeto[sujeto][experimento][tipo_dato]

# timestamp = datos['timestamp']
# aceleracion_x = datos['x']
# aceleracion_y = datos['y']
# aceleracion_z = datos['z']

# # Plotear en el dominio del tiempo antes del filtro
# plt.figure(figsize=(12, 6))
# plt.subplot(2, 3, 1)
# # plt.plot(timestamp, aceleracion_x, linewidth=grosor_linea)
# # plt.plot(timestamp, aceleracion_y, linewidth=grosor_linea)
# plt.plot(timestamp, aceleracion_z, linewidth=grosor_linea)
# plt.title('Dominio del tiempo (antes del filtro)')
# plt.xlabel('Tiempo')
# plt.ylabel('Aceleración')

# fs = 30.0  

# frecuencia_corte_HP = 0.05  
# frecuencia_corte_LP = 3.5 
# frecuencia_corte_HP_norm = frecuencia_corte_HP / (0.5 * fs)
# frecuencia_corte_LP_norm = frecuencia_corte_LP / (0.5 * fs)

# b, a = signal.butter(N=4, Wn=frecuencia_corte_HP_norm, btype='high', analog=False)
# d, c = signal.butter(N=4, Wn=frecuencia_corte_LP_norm, btype='low', analog=False)

# aceleracion_x_filtrada_HP = signal.filtfilt(b, a, aceleracion_x)
# aceleracion_y_filtrada_HP = signal.filtfilt(b, a, aceleracion_y)
# aceleracion_z_filtrada_HP = signal.filtfilt(b, a, aceleracion_z)

# aceleracion_x_filtrada_LP = signal.filtfilt(d, c, aceleracion_x_filtrada_HP)
# aceleracion_y_filtrada_LP = signal.filtfilt(d, c, aceleracion_y_filtrada_HP)
# aceleracion_z_filtrada_LP = signal.filtfilt(d, c, aceleracion_z_filtrada_HP)

# # Plotear en el dominio del tiempo después del filtro
# plt.subplot(2, 3, 2)
# # plt.plot(timestamp, aceleracion_x_filtrada_HP, linewidth=grosor_linea)
# # plt.plot(timestamp, aceleracion_y_filtrada_HP, linewidth=grosor_linea)
# plt.plot(timestamp, aceleracion_z_filtrada_HP, linewidth=grosor_linea)
# plt.title('Dominio del tiempo (después del primer filtro)')
# plt.xlabel('Tiempo')
# plt.ylabel('Aceleración')

# # Plotear en el dominio de la frecuencia antes del filtro
# plt.subplot(2, 3, 3)
# # plt.plot(timestamp, aceleracion_x_filtrada_LP, linewidth=grosor_linea)
# # plt.plot(timestamp, aceleracion_y_filtrada_LP, linewidth=grosor_linea)
# plt.plot(timestamp, aceleracion_z_filtrada_LP, linewidth=grosor_linea)
# plt.title('Dominio del tiempo (después del segundo filtro)')
# plt.xlabel('Tiempo')
# plt.ylabel('Aceleración')

# # Plotear en el dominio de la frecuencia después del filtro
# plt.subplot(2, 3, 4)
# fx, Pxxx = signal.periodogram(aceleracion_x, fs)
# fy, Pxxy = signal.periodogram(aceleracion_y, fs)
# fz, Pxxz = signal.periodogram(aceleracion_z, fs)

# Pxxx_dB = 10 * np.log10(Pxxx)
# Pxxy_dB = 10 * np.log10(Pxxy)
# Pxxz_dB = 10 * np.log10(Pxxz)

# # Trazar en escala logarítmica
# plt.semilogy(fx, Pxxx_dB, linewidth=grosor_linea, label='Aceleración X')
# plt.semilogy(fy, Pxxy_dB, linewidth=grosor_linea, label='Aceleración Y')
# plt.semilogy(fz, Pxxz_dB, linewidth=grosor_linea, label='Aceleración Z')

# plt.title('Dominio de la frecuencia (antes del filtro)')
# plt.xlabel('Frecuencia (Hz)')
# plt.ylabel('Potencia espectral')

# # Plotear en el dominio de la frecuencia antes del filtro
# plt.subplot(2, 3, 5)
# fx, Pxxx_filtrado_HP = signal.periodogram(aceleracion_x_filtrada_HP, fs)
# fy, Pxxy_filtrado_HP = signal.periodogram(aceleracion_y_filtrada_HP, fs)
# fz, Pxxz_filtrado_HP = signal.periodogram(aceleracion_z_filtrada_HP, fs)

# Pxxx_dB = 10 * np.log10(Pxxx_filtrado_HP)
# Pxxy_dB = 10 * np.log10(Pxxy_filtrado_HP)
# Pxxz_dB = 10 * np.log10(Pxxz_filtrado_HP)

# # Trazar en escala logarítmica
# plt.semilogy(fx, Pxxx_dB, linewidth=grosor_linea, label='Aceleración X')
# plt.semilogy(fy, Pxxy_dB, linewidth=grosor_linea, label='Aceleración Y')
# plt.semilogy(fz, Pxxz_dB, linewidth=grosor_linea, label='Aceleración Z')

# plt.title('Dominio de la frecuencia (después del primer filtro)')
# plt.xlabel('Frecuencia (Hz)')
# plt.ylabel('Potencia espectral')

# # Plotear en el dominio de la frecuencia después del filtro
# plt.subplot(2, 3, 6)

# fx, Pxxx_filtrado_LP = signal.periodogram(aceleracion_x_filtrada_LP, fs)
# fy, Pxxy_filtrado_LP = signal.periodogram(aceleracion_y_filtrada_LP, fs)
# fz, Pxxz_filtrado_LP = signal.periodogram(aceleracion_z_filtrada_LP, fs)

# Pxxx_dB = 10 * np.log10(Pxxx_filtrado_LP)
# Pxxy_dB = 10 * np.log10(Pxxy_filtrado_LP)
# Pxxz_dB = 10 * np.log10(Pxxz_filtrado_LP)

# f_min = 0.05
# f_max = 3.5
# dB_min_zoom = 10
# dB_max_zoom = 70

# # Convertir frecuencias a índices
# idx_min = np.argmax(fx >= f_min)
# idx_max = np.argmax(fx >= f_max)

# # Trazar en escala logarítmica
# plt.semilogy(fx, Pxxx_dB, linewidth=grosor_linea, label='Aceleración X')
# plt.semilogy(fy, Pxxy_dB, linewidth=grosor_linea, label='Aceleración Y')
# plt.semilogy(fz, Pxxz_dB, linewidth=grosor_linea, label='Aceleración Z')

# # Seleccionar una región de interés
# plt.xlim(f_min, f_max)
# plt.ylim(dB_min_zoom, dB_max_zoom)

# plt.xlabel('Frecuencia (Hz)')
# plt.ylabel('PSD (dB/Hz)')
# plt.legend()
# plt.grid(True)

# plt.title('Dominio de la frecuencia (después del segundo filtro)')
# plt.xlabel('Frecuencia (Hz)')
# plt.ylabel('Potencia espectral')

# plt.tight_layout()

# idx_max_x = np.argmax(Pxxx_dB)
# idx_max_y = np.argmax(Pxxy_dB)
# idx_max_z = np.argmax(Pxxz_dB)

# f_max_x = fx[idx_max_x]
# f_max_y = fy[idx_max_y]
# f_max_z = fz[idx_max_z]

# print(f'Máximo en aceleración X: {Pxxx_dB[idx_max_x]} dB/Hz en {f_max_x} Hz')
# print(f'Máximo en aceleración Y: {Pxxy_dB[idx_max_y]} dB/Hz en {f_max_y} Hz')
# print(f'Máximo en aceleración Z: {Pxxz_dB[idx_max_z]} dB/Hz en {f_max_z} Hz')

# max_power = np.maximum.reduce([Pxxx_dB[idx_max_x], Pxxy_dB[idx_max_y], Pxxz_dB[idx_max_z]])

# power_alias = {'Aceleración en el Eje X': Pxxx_dB[idx_max_x], 'Aceleración en el Eje Y': Pxxy_dB[idx_max_y], 'Aceleración en el Eje Z': Pxxz_dB[idx_max_z]}

# # Variable con el valor máximo
# max_power_alias = max(power_alias, key=lambda k: max_power)

# print()
# print(f'El dato que se tendrá en cuenta para medir la Braidicinesia es: {max_power_alias}')

# plt.show()


