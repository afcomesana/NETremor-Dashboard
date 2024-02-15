import pandas as pd
import numpy as np
from scipy.signal import hilbert, find_peaks
import matplotlib.pyplot as plt
import glob
import os

# TIME INFORMATION (gyroscope data):

def get_task_time(df, millis_per_sample):
    
    df['magnitude'] = compute_magnitude(df)
    
    start_peak, end_peak = find_surrounding_peaks(df['magnitude'].values, threshold=100)

    return abs(end_peak - start_peak) * millis_per_sample / 1000

def compute_magnitude(df):
    return np.sqrt(df['x']**2 + df['y']**2 + df['z']**2)

def find_surrounding_peaks(data, threshold):
    peak_indices, _ = find_peaks(envelope)
    peaks_above_threshold = [idx for idx in peak_indices if data[idx] > threshold]
    return peaks_above_threshold[0], peaks_above_threshold[-1]

# Lista de datos disponibles
datos_disponibles = ['gyroscope-0', 'gyroscope-1', 'gyroscope-2']

# Estructuras para almacenar los datos
datos_sujeto = {}
datos_paciente = {}

# Crear un diccionario para almacenar los resultados
resultados_sujeto_dict = {'Sujeto': [], 'Experimento': [], 'TiempoMedio': [], 'TiempoMaximo': []}
resultados_completos_sujetos_dict = {'Sujeto': [], 'Experimento': [], 'Tiempo': []}
resultados_paciente_dict = {'Paciente': [], 'Experimento': [], 'TiempoMedio': []}
tiemposMedExp_sujeto_dict = {'Experimento': [], 'TiempoMedio': [], 'TiempoMaximo': []}



resultados_paciente_df = pd.DataFrame(resultados_paciente_dict)
styler_paciente = resultados_paciente_df.style.apply(lambda x: ['color: red; font-weight: bold' if c == 'TiempoMedio' else '' for c in x])
styler_paciente.to_excel('resultados_paciente_con_formato.xlsx', index=False, engine='openpyxl')


# Convertir el diccionario a un DataFrame
resultados_sujeto_df = pd.DataFrame(resultados_sujeto_dict)

for experimento in experimentos:
    tiemposExp_sujeto = resultados_sujeto_df[resultados_sujeto_df['Experimento'] == experimento]
    tiemposMedExp_sujeto = sum(tiemposExp_sujeto['TiempoMedio'])/len(sujeto)
    tiemposMaxExp_sujeto = tiemposExp_sujeto['TiempoMedio'].max()
    tiemposMedExp_sujeto_dict['Experimento'].append(experimento)
    tiemposMedExp_sujeto_dict['TiempoMedio'].append(tiemposMedExp_sujeto)
    tiemposMedExp_sujeto_dict['TiempoMaximo'].append(tiemposMaxExp_sujeto)



pd.DataFrame(tiemposMedExp_sujeto_dict).to_csv('tiemposMedExp_sujeto.csv', index=False)

