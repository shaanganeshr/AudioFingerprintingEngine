import os
import numpy as np
from scipy.io import wavfile
from dotenv import load_dotenv
from supabase import create_client, Client
from engine import ShazamFingerprintEngine

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
INDEX_FILE = os.getenv("INDEX_FILE_PATH", "fingerprints.pkl")
SONGS_DIR = "songs"

def ensure_sample_wavs_exist(folder: str):

    os.makedirs(folder, exist_ok=True)
    wavs = [f for f in os.listdir(folder) if f.lower().endswith(".wav")]
    if wavs:
        return

    print("No .wav files found in 'songs/'. Generating 3 synthetic test .wav tracks...")
    fs = 44100
    duration = 20
    np.random.seed(100)
    for i in range(1, 4):
        t = np.linspace(0, duration, fs * duration, endpoint=False)
        wave = np.zeros_like(t)
        for sec in range(duration):
            f1, f2 = np.random.randint(300, 1800), np.random.randint(1900, 4200)
            idx = slice(sec * fs, (sec + 1) * fs)
            wave[idx] = 0.5 * np.sin(2 * np.pi * f1 * t[idx]) + 0.4 * np.sin(2 * np.pi * f2 * t[idx])
        path = os.path.join(folder, f"Demo_Track_0{i}.wav")
        wavfile.write(path, fs, (wave * 32767).astype(np.int16))

def main():
    ensure_sample_wavs_exist(SONGS_DIR)
    supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
    engine = ShazamFingerprintEngine()

    wav_files = sorted([f for f in os.listdir(SONGS_DIR) if f.lower().endswith(".wav")])
    print(f"Indexing {len(wav_files)} tracks from '{SONGS_DIR}/'...")

    for song_id, filename in enumerate(wav_files, start=1):
        filepath = os.path.join(SONGS_DIR, filename)
        sr, raw_data = wavfile.read(filepath)
        duration_sec = round(len(raw_data) / float(sr), 2)

        #Index hashes into Radix Tree & Robin Hood Hash Table
        engine.index_song_file(song_id=song_id, filepath=filepath)

        #Add to Supabase 'songs' table
        title = os.path.splitext(filename)[0].replace("_", " ")
        supabase.table("songs").upsert({
            "id": song_id,
            "title": title,
            "artist": "Local Library",
            "duration_seconds": duration_sec,
            "file_path": filepath
        }).execute()
        print(f" -> Synced ID #{song_id} ('{title}', {duration_sec}s) to Supabase.")

    #Save Radix Tree & Robin Hood Hash Table
    engine.save_index(INDEX_FILE)
    print("\nDone! Both 'fingerprints.pkl' and Supabase 'songs' table are ready.")

if __name__ == "__main__":
    main()