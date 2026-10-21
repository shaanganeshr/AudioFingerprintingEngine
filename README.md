<div align="center">

# 🎧 Earshot & AudioFingerprint Engine
### *For the love of music. A world of sound, one little listen.*

<p align="center">
  <img src="https://img.shields.io/badge/FastAPI-005571?style=for-the-badge&logo=fastapi" alt="FastAPI" />
  <img src="https://img.shields.io/badge/React-20232A?style=for-the-badge&logo=react&logoColor=61DAFB" alt="React" />
  <img src="https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white" alt="Supabase" />
  <img src="https://img.shields.io/badge/Python-FFD43B?style=for-the-badge&logo=python&logoColor=blue" alt="Python" />
  <img src="https://img.shields.io/badge/Tailwind_CSS-38BDF8?style=for-the-badge&logo=tailwind-css&logoColor=white" alt="Tailwind CSS" />
</p>

</div>

---

## 📖 Overview

**Earshot** is an acoustic fingerprinting and music recognition platform. Powered by a high-performance **FastAPI DSP engine** and an editorial **React frontend**, it listens to live microphone snippets or uploaded `.wav` files, extracts constellation peaks using Fourier transforms, and instantly identifies songs down to the exact timestamp offset.

Whether you're testing your favorite tracks or building a custom database of indexed audio, Earshot bridges raw digital signal processing with a fluid analog-inspired user experience.

---

## ✨ Key Features

* **⚡ High-Performance DSP Backend**: Fast Fourier Transform (FFT) analysis, local maxima peak detection, and combinatorial hashing with RMS silence filtering to filter out ambient noise.
* **🎨 Editorial "Earshot" UI/UX**: Designed with warm cream and terracotta tones, Instrument Serif typography, a spinning vinyl recording stage, and a live frequency visualizer canvas.
* **🎙️ Cross-Platform Audio Encoder**: Converts browser microphone audio streams into clean 16-bit PCM `.wav` blobs on the fly for reliable parsing by Python's audio libraries.
* **☁️ Secure Cloud Persistence**: Integrated with Supabase Auth and database tables to track user search histories and personal Shazam collections.

---

## 🏗️ Project Architecture

```text
AudioFingerprint/
├── app.py              # FastAPI application server & routing
├── engine.py           # Core DSP recognition & catalog indexing
├── fourier.py          # FFT & spectrogram calculations
├── hashing.py          # Constellation hash generation & indexing
├── load.py             # Audio file loading utilities
├── peaks.py            # Local maxima peak detection algorithms
├── song_index.py       # Song database & metadata management
├── tools.py            # Helper utilities & RMS noise thresholds
├── test.py             # Backend testing scripts
├── test_snippet_10s.wav# Sample audio test snippet
├── requirements.txt    # Python backend dependencies
└── frontend/           # React + Vite frontend application
    ├── public/         # Static assets & icons
    ├── src/
    │   ├── App.jsx     # Main dashboard interface
    │   ├── App.css     # Editorial styling & custom animations
    │   ├── index.css   # Global resets
    │   ├── main.jsx    # React mounting point
    │   ├── supabaseClient.js # Supabase connection client
    │   └── wavHelper.js# 16-bit PCM WAV client encoder
    ├── package.json    # Frontend packages & scripts
    └── vite.config.js  # Vite bundler configuration
```
<div align="center">

# 🔬 Deep Dive: How the DSP Engine Works
### *The mathematics and logic running under the hood*

</div>

If you're curious about the internal signal processing algorithms driving the system:

1. **Time-Frequency Representation**: The audio snippet is converted into a spectrogram using Short-Time Fourier Transform (STFT), breaking the sound wave down into frequency bins across time frames.
2. **Constellation Mapping**: The engine identifies high-energy points (peaks) in the spectrogram using combinatorial neighbor zones, making the fingerprint resilient to background noise and minor distortions.
3. **Hash Indexing & Lookup**: Hashes generated from peak pairs are matched against the pre-computed database (`fingerprints.pkl`). A matching score is calculated based on time-delta consistency, returning the exact song title and offset timestamp with millisecond precision.

---

<div align="center">

# 🚀 Getting Started Guide
### *Set up and run the complete stack locally*

</div>

### Prerequisites
- **Python 3.10+** installed on your system.
- **Node.js & npm** (or Bun) installed for the React frontend.
- A **Supabase** project for authentication and match history storage.

### 1. Backend Setup (FastAPI)
Clone the repository and set up your Python environment:

```bash
# Navigate to the root directory
cd AudioFingerprint

# Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On macOS/Linux:
source .venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Start the FastAPI backend server
uvicorn app:app --reload --port 8000
The DSP engine uses STFT-based spectrogram analysis, spectral peak detection, and hash-based fingerprint matching.

You're all set! Start both servers and open http://localhost:5173 to access the application locally.
```

### 2. Frontend Setup (React / Earshot)
Open a new terminal window for the frontend:

```bash
# Move into the frontend folder
cd frontend

# Install dependencies
npm install

# Create a local .env file
touch .env
```
Add your credentials to frontend/.env:

```bash
VITE_SUPABASE_URL=your_supabase_project_url
VITE_SUPABASE_ANON_KEY=your_supabase_anon_key
VITE_API_BASE_URL=[http://127.0.0.1:8000](http://127.0.0.1:8000)
```

Run the development server:

```bash
npm run dev
# Open http://localhost:5173 in your browser.
```
