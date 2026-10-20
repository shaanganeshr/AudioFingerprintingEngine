import numpy as np
from load import TARGET_FS
from tools import CircularAudioQueue

FFT_SIZE=1024
HOP_SIZE=512

def compute_fft(audio: np.ndarray, fs: int=TARGET_FS)->np.ndarray:
    #Hann window is used to compute FFT
    ring_buffer=CircularAudioQueue(capacity=FFT_SIZE)
    hann_window=np.hanning(FFT_SIZE).astype(np.float32)
    frames_fft=[]
    ring_buffer.push_chunk(audio[:FFT_SIZE - HOP_SIZE])
    
    for offset in range(FFT_SIZE-HOP_SIZE, len(audio)-HOP_SIZE+1, HOP_SIZE):
        chunk=audio[offset : offset + HOP_SIZE]
        ring_buffer.push_chunk(chunk)
    
        #Current 1024 sample
        frame=ring_buffer.get_ordered_frame() * hann_window
        fft_mag=np.abs(np.fft.rfft(frame))
        frames_fft.append(20 * np.log10(fft_mag + 1e-10))
    
        #Advance circular queue 
        ring_buffer.pop_hop(HOP_SIZE)
    

    return np.column_stack(frames_fft)

