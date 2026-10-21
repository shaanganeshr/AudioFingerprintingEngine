import numpy as np
from tools import Custom2DKDTree

FAN_OUT = 15
MIN_TIME_DELTA = 1
MAX_TIME_DELTA = 63
MAX_FREQ_DELTA = 150

def generate_hash(peaks: np.ndarray) -> list[tuple[int, int]]:
    if len(peaks)==0:
        return []

    hashes=[]
    tree = Custom2DKDTree(peaks)

    for i, (t1, f1) in enumerate(peaks):
        #Find all peaks within search radius
        indices=tree.query_target_box(
            t_min=int(t1 + MIN_TIME_DELTA),
            t_max=int(t1 + MAX_TIME_DELTA),
            f_min=int(f1 - MAX_FREQ_DELTA),
            f_max=int(f1 + MAX_FREQ_DELTA)
        )       

        paired=0
        for j in indices:
            #Only points after anchor point
            if j<=i:
                continue

            t2, f2=peaks[j]
            time_delta=int(t2-t1)

            #Bit packing into single hash
            hash_value=(int(f1) << 20) | (int(f2) << 10) | time_delta
            hashes.append((hash_value, int(t1)))
            paired+=1
            
            if paired>=FAN_OUT:
                break

    return hashes