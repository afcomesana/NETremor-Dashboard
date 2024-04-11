from scipy import signal

def band_pass_filter(data, low_pass_frequency, high_pass_frequency, sampling_frequency):
    # N: order of the filter
    # Wn: critical frequency
    b, a = signal.butter(N=4, Wn=[low_pass_frequency, high_pass_frequency], btype="bandpass", fs=sampling_frequency)
    # returns numerator and denominator of the polynomials of the IIR filter

    # filtfilt the input acceleracion_(x|y|z) filtered
    return signal.filtfilt(b, a, signal.filtfilt(b, a, data))

