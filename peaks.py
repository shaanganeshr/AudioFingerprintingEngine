import numpy as np
from tools import DisjointSparseTable, BoundedMinHeap

TIME_RADIUS=8       #Check +/ -8 time frames in DST
FREQ_RADIUS=8       #Check +/- 8 frequency bins
MAX_K=6   
def extract_peaks(spectrogram: np.ndarray, percentile_threshold: float=75.0) -> np.ndarray:
    #Holds max of each 20*20 window
    num_freqs, num_times=spectrogram.shape
    amp_threshold=np.percentile(spectrogram, percentile_threshold)

    #Build a DST for each frequency row
    row_dsts=[DisjointSparseTable(spectrogram[f, :]) for f in range(num_freqs)]
    all_peaks=[]

    for t in range(num_times):
        frame_heap=BoundedMinHeap(max_k=MAX_K)

        for f in range(num_freqs):
            val=spectrogram[f, t]
            if val <= amp_threshold:
                continue

            #RMQ across time [t-TIME_RADIUS, t+TIME_RADIUS]
            if val < row_dsts[f].query_max(t-TIME_RADIUS, t+TIME_RADIUS):
                continue

            #Vertical frequency neighborhood [f-FREQ_RADIUS, f+FREQ_RADIUS]
            f_low=max(0, f-FREQ_RADIUS)
            f_high=min(num_freqs, f+FREQ_RADIUS +1)
            if val >= np.max(spectrogram[f_low:f_high, t]):
                frame_heap.push_peak(val, t, f)

        all_peaks.extend(frame_heap.get_peaks())

    peaks_arr=np.array(all_peaks, dtype=np.int32)
    return peaks_arr[np.argsort(peaks_arr[:, 0])] if len(peaks_arr) > 0 else np.empty((0, 2), dtype=np.int32)


