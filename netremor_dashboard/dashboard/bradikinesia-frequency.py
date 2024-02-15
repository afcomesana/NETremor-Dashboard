import pandas as pd
import numpy as np
from scipy import signal

MILLIS_PER_SAMPLE = 30
SAMPLE_FREQUENCY  = 30.0

HIGH_PASS_FILTER_FREQUENCY = 0.5 # Hz
LOW_PASS_FILTER_FREQUENCY  = 3.5 # Hz

HIGH_PASS_FILTER_FREQUENCY_NORMALIZED = HIGH_PASS_FILTER_FREQUENCY / (0.5 * SAMPLE_FREQUENCY)
LOW_PASS_FILTER_FREQUENCY_NORMALIZED  = LOW_PASS_FILTER_FREQUENCY  / (0.5 * SAMPLE_FREQUENCY)

def find_dominant_frequency(df, axis = ["x", "y", "z"]):
    
    maximum_frequencies_energies = []
    
    for ax in axis:
        data = df[ax]
        
        filtered_data = band_pass_filter(data, LOW_PASS_FILTER_FREQUENCY, HIGH_PASS_FILTER_FREQUENCY)
        
        frequencies, power = get_spectral_density(filtered_data, SAMPLE_FREQUENCY)

        max_power_index = np.argmax(power)
        
        maximum_frequencies_energies.append({
            "frequency": frequencies[max_power_index],
            "power": power[max_power_index]
        })
    
    max_frequency, max_power = max(maximum_frequencies_energies, key = lambda ax: ax["power"]).values()
    
    return max_frequency, max_power
    

def band_pass_filter(data, low_pass_frequency, high_pass_frequency):
    # N: order of the filter
    # Wn: critical frequency
    b, a = signal.butter(N=4, Wn=high_pass_frequency, btype='high', analog=False)
    d, c = signal.butter(N=4, Wn=low_pass_frequency, btype='low', analog=False)
    # returns numerator and denominator of the polynomials of the IIR filter

    # filtfilt the input acceleracion_(x|y|z) filtered
    return signal.filtfilt(d, c, signal.filtfilt(b, a, data))
    
def get_spectral_density(data, sample_frequency):
    # periodogram returns two arrays: array of sample frequencies and array of power spectral density
    frequencies, power_spectral_density = signal.periodogram(data, sample_frequency)
    
    # Parse to dB
    power_spectral_density = 10 * np.log10(power_spectral_density)
    
    return frequencies, power_spectral_density