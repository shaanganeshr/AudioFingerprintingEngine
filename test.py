import os
import numpy as np
from scipy.io import wavfile

# Grab the first .wav song in your songs/ folder
songs = sorted([f for f in os.listdir("songs") if f.lower().endswith(".wav")])
target_song = os.path.join("songs", songs[0])

sr, data = wavfile.read(target_song)
# Convert to float (-1.0 to 1.0)
data = data.astype(np.float32)
if data.ndim > 1:
    data = np.mean(data, axis=1)
data /= np.max(np.abs(data))

# Slice a 5-second clip starting at 10.0 seconds into the song
start_sec = 10.0
clip = data[int(start_sec * sr) : int((start_sec + 5.0) * sr)]

# Add light background noise (simulating a room recording)
noisy_clip = clip + np.random.normal(0, 0.05, size=len(clip))
noisy_clip = np.clip(noisy_clip, -1.0, 1.0)

wavfile.write("test_snippet_10s.wav", sr, (noisy_clip * 32767).astype(np.int16))
print(f"Created 'test_snippet_10s.wav' sliced from '{songs[0]}' at {start_sec}s!")