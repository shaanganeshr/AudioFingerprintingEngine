import os
import time
import pickle
import numpy as np
from collections import Counter

from load import load_normalise, load_wav, TARGET_FS
from fourier import compute_fft, HOP_SIZE
from peaks import extract_peaks
from hashing import generate_hash
from tools import FingerprintRadixTree, RobinHoodHashTable


class ShazamFingerprintEngine:
    def __init__(self):
        self.radix_tree=FingerprintRadixTree()
        self.robin_hood_index=RobinHoodHashTable(initial_capacity=32768)
        #song_id -> {"title":str,"file_path":str}
        self.song_catalog: dict[int, dict]={}

    def _run_pipeline_from_array(self, raw_audio: np.ndarray, sample_rate: int) -> tuple[np.ndarray, list[tuple[int, int]]]:
        clean_audio=load_normalise(raw_audio, sample_rate)
        spectrogram=compute_fft(clean_audio, TARGET_FS)
        peaks=extract_peaks(spectrogram)
        hashes=generate_hash(peaks)
        return peaks, hashes

    def index_song_file(self, song_id: int, filepath: str):
        clean_audio, fs=load_wav(filepath)
        spectrogram=compute_fft(clean_audio, fs)
        peaks=extract_peaks(spectrogram)
        hashes=generate_hash(peaks)

        title=os.path.basename(filepath)
        self.song_catalog[song_id]={"title": title, "file_path": filepath}

        for h, t1 in hashes:
            self.radix_tree.insert(h)
            self.robin_hood_index.append_posting(h, (song_id, t1))

        print(f"[Indexed File] ID #{song_id}: '{title}' | Peaks: {len(peaks)} | Hashes: {len(hashes)}")

    def index_wav_folder(self, folder_path: str):
        #Loops through a folder of .wav files and indexes them.
        if not os.path.exists(folder_path):
            raise FileNotFoundError(f"Directory not found: {folder_path}")

        wav_files=sorted([f for f in os.listdir(folder_path) if f.lower().endswith(".wav")])
        print(f"Found {len(wav_files)} .wav files in '{folder_path}'...")

        for idx, filename in enumerate(wav_files, start=1):
            full_path=os.path.join(folder_path, filename)
            self.index_song_file(song_id=idx, filepath=full_path)

    def index_song_array(self, song_id: int, title: str, raw_audio: np.ndarray, sample_rate: int):
        #Indexes a song directly from an array.
        peaks, hashes=self._run_pipeline_from_array(raw_audio, sample_rate)
        self.song_catalog[song_id]={"title": title, "file_path": "in_memory"}

        for h, t1 in hashes:
            self.radix_tree.insert(h)
            self.robin_hood_index.append_posting(h, (song_id, t1))

        print(f"[Indexed Array] ID #{song_id}: '{title}' | Peaks: {len(peaks)} | Hashes: {len(hashes)}")

    def recognize_snippet(self, raw_snippet: np.ndarray, sample_rate: int) -> dict:
        """
        Matches an audio snippet using:
        1.RadixTree to filter out unindexed background noise hashes
        2.RobinHoodHashTable to fetch (song_id, t_db)
        3.Counter Offset Histogram to find the tallest time-offset spike
        """
        start_time=time.perf_counter()
        _, sample_hashes=self._run_pipeline_from_array(raw_snippet, sample_rate)

        offset_histogram=Counter()
        radix_filtered_noise=0

        for h, t_sample in sample_hashes:
            #Radix tree removes unncessary noise hashes
            if not self.radix_tree.contains(h):
                radix_filtered_noise += 1
                continue

            #RobinHoodHashTable returns a list of (song_id, t_db) for the hash
            postings=self.robin_hood_index.get(h)
            for song_id, t_db in postings:
                delta_T=t_db - t_sample
                if delta_T >= 0:
                    offset_histogram[(song_id, delta_T)] += 1

        elapsed_ms=(time.perf_counter() - start_time) * 1000

        if not offset_histogram:
            return {
                "matched": False,
                "noise_hashes_filtered": radix_filtered_noise,
                "match_time_ms": round(elapsed_ms, 2)
            }

        #Extract the tallest spike in histogram
        (best_song_id, best_offset_frames), confidence_hits=offset_histogram.most_common(1)[0]
        timestamp_seconds=(best_offset_frames * HOP_SIZE) / TARGET_FS

        #Top 5 spikes
        top_spikes=[
            {
                "song_id": s_id,
                "song_title": self.song_catalog[s_id]["title"],
                "offset_sec": round((offset_f * HOP_SIZE) / TARGET_FS, 2),
                "hits": hits
            }
            for (s_id, offset_f), hits in offset_histogram.most_common(5)
        ]

        return {
            "matched": True,
            "song_id": best_song_id,
            "song_title": self.song_catalog[best_song_id]["title"],
            "confidence_hits": confidence_hits,
            "timestamp_seconds": round(timestamp_seconds, 2),
            "total_sample_hashes": len(sample_hashes),
            "noise_hashes_filtered": radix_filtered_noise,
            "match_time_ms": round(elapsed_ms, 2),
            "top_histogram_spikes": top_spikes
        }

    #Save and load the index to/from disk
    def save_index(self, filepath: str="fingerprints.pkl"):
        with open(filepath, "wb") as f:
            pickle.dump({
                "radix_tree": self.radix_tree,
                "robin_hood_index": self.robin_hood_index,
                "song_catalog": self.song_catalog
            }, f)
        print(f"Saved index ({self.robin_hood_index.size} unique hashes) to '{filepath}'.")

    def load_index(self, filepath: str="fingerprints.pkl"):
        with open(filepath, "rb") as f:
            data=pickle.load(f)
            self.radix_tree=data["radix_tree"]
            self.robin_hood_index=data["robin_hood_index"]
            self.song_catalog=data["song_catalog"]
        print(f"Loaded {len(self.song_catalog)} songs ({self.robin_hood_index.size} unique hashes) from '{filepath}'.")


# --- CLI VERIFICATION TEST (Run `python engine.py`) ---
if __name__ == "__main__":
    np.random.seed(42)
    engine=ShazamFingerprintEngine()
    fs=44100
    duration=30  # 30-second test tracks

    print("--- Indexing 5 Synthetic Tracks ---")
    tracks={}
    for s_id in range(1, 6):
        t=np.linspace(0, duration, fs * duration, endpoint=False)
        wave=np.zeros_like(t)
        for sec in range(duration):
            fa, fb=np.random.randint(300, 2000), np.random.randint(2000, 4500)
            idx=slice(sec * fs, (sec + 1) * fs)
            wave[idx]=np.sin(2 * np.pi * fa * t[idx]) + 0.8 * np.sin(2 * np.pi * fb * t[idx])
        tracks[s_id]=wave
        engine.index_song_array(s_id, f"Song_0{s_id}.wav", wave, fs)

    print("\n--- Testing 4-Second Noisy Snippet from Song_04 at 17.5s ---")
    start_idx, end_idx=int(17.5 * fs), int(21.5 * fs)
    noisy_clip=tracks[4][start_idx:end_idx] + np.random.normal(0, 0.8, size=(end_idx - start_idx))

    result=engine.recognize_snippet(noisy_clip, fs)
    print("Match Result:", result)