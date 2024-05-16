import os
import sys
import imu
import math
import numpy as np
import multiprocessing
from scipy import signal
from csvsort import csvsort

imu_filepath = "/home/ging/netremor/imu-files/38ec605012c411ef99d08c1759ee1f3c-accelerometer.imu"

def bandpass_filter(data, low_pass_frequency, high_pass_frequency, sampling_frequency):
    # N: order of the filter
    # returns numerator and denominator of the polynomials of the IIR filterw
    b, a = signal.butter(N=4, Wn=[low_pass_frequency, high_pass_frequency], btype="bandpass", fs=sampling_frequency)

    return signal.filtfilt(b, a, data)


def compute_tremor(data, sampling_frequency):
    LOW_PASS_FREQ  = 2 # Herze
    HIGH_PASS_FREQ = 10 # Herz
    
    n_samples = len(data)
    
    hop_seconds = 1
    window_seconds = 3
    
    hop_size    = int(hop_seconds * sampling_frequency)
    window_size = int(window_seconds*sampling_frequency)
    
    oversampling_factor = 16
    mfft = 2**math.ceil(math.log(oversampling_factor * sampling_frequency, 2))
    
    gaussian_window = signal.windows.gaussian(window_size, std=12, sym=True)
    SFT = signal.ShortTimeFFT(gaussian_window, hop=hop_size, fs=sampling_frequency, mfft=mfft, scale_to="psd")
    
    data = bandpass_filter(data, LOW_PASS_FREQ, HIGH_PASS_FREQ, sampling_frequency)
    
    # After computing the spectrogram, each axis is a M x N where M is the number of frequencies slices
    # whose PSD was computed and N is the number of time slices.
    data = 10*np.log10(np.fmax(SFT.spectrogram(data), 1e-4))
    
    # To represent the tremor, we compute the maximum of all the frequencies at each time.
    f_index = np.argmax(data, axis=0)
    data = [data[row, col] for row, col in zip(f_index, range(data.shape[1]))]
    
    frequencies = f_index*SFT.delta_f
    
    print("lower_border_end:", SFT.lower_border_end)
    print("delta_f:", SFT.delta_f)
    print("delta_t:", SFT.delta_t)
    print("upper_border_begin(n_samples):", SFT.upper_border_begin(n_samples))
    print("t(n_samples):", SFT.t(n_samples))
    print("extent(n_samples):", SFT.extent(n_samples))
    
    
    return tuple(zip(frequencies, data))
    

def write_tremor_file(imu_filepath):

    # 1. Read imu file
    # 2. Rearrange output tuple to get all the axis values in the same tuple
    # 3. Compute parallelwise each axis tremor values
    
    # TODO: Get delta_t from original data file
    # delta_t = imufile.datafile.delta_t
    
    # if not delta_t:
    #     delta_t = settings.DEFAULT_DELTA_T
    
    delta_t = 29
    
    sampling_frequency = (1/delta_t)*1000
    
    # imu_filepath = os.path.join(settings.IMUFILES_DIR, imufile.name)
    
    data, _, initial_timestamp, delta_t = imu.rimu(imu_filepath)
    axis = data.pop(0)
    data = tuple(zip(*data))
    
    
    # Process each axis parallel-wise:
    with multiprocessing.Pool(processes=len(axis)) as pool:
        data = pool.starmap(compute_tremor, zip(data, (sampling_frequency,)*len(axis)))
        print(len(data[0]))
        print(data[0][:10])
        # data = pool.starmap(np.apply_along_axis, zip(*[[item]*n_axis for item in (max, 0)], data))
        # axis_data = 10*np.log10(np.fmax(SFT.spectrogram(axis_data), 1e-4))
    
if __name__ == "__main__":
    write_tremor_file(imu_filepath)