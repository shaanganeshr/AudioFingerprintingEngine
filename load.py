import numpy as np
from scipy.io import wavfile
from scipy.signal import resample_poly
import math

TARGET_FS=11025

def load_normalise(data: np.ndarray, sample_rate: int) -> np.ndarray:
    data=data.astype(np.float32)

    #Convert all dimnesions to mono
    if data.ndim>1:
        data=np.mean(data, axis=1)

    #Normalise all amplitude by -1 to 1 by dividing by max
    max_amp=np.max(np.abs(data))
    if max_amp>0:
        data=data/max_amp

    #Downsample to target sample rate (Nyquist-Shannon Sampling Theorem - fs->fs/2)
    if sample_rate!=TARGET_FS:
        gcd=math.gcd(sample_rate, TARGET_FS)
        up=TARGET_FS//gcd
        down=sample_rate//gcd
        data=resample_poly(data, up, down)

    return data

def load_wav(filepath: str)->tuple[np.ndarray, int]:
    sample_rate, data=wavfile.read(filepath)
    processed_data=load_normalise(data, sample_rate)
    return processed_data, TARGET_FS 