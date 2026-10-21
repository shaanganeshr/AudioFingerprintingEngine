import io
import os
from contextlib import asynccontextmanager
from typing import Optional

import numpy as np
import soundfile as sf
from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from supabase import Client, create_client

from engine import ShazamFingerprintEngine

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
INDEX_FILE = os.getenv("INDEX_FILE_PATH", "fingerprints.pkl")

engine = ShazamFingerprintEngine()
supabase: Client = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)

@asynccontextmanager
async def lifespan(app: FastAPI):
    #Loads the Radix Tree and Robin Hood Hash Table into RAM 
    if os.path.exists(INDEX_FILE):
        engine.load_index(INDEX_FILE)
    else:
        print(f"WARNING: '{INDEX_FILE}' not found. Run 'python build_index.py' first!")
    yield


app = FastAPI(
    title="Shazam Audio Fingerprinting API",
    description="FastAPI Bridge powered by Radix Tree & Robin Hood Hash Table",
    lifespan=lifespan
)

# Enable CORS so React can call the API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_user_id_from_auth_header(authorization: Optional[str]) -> Optional[str]:
    #Verifies the Supabase Bearer JWT token and returns the user's UUID.
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.split(" ")[1]
    try:
        user_resp = supabase.auth.get_user(token)
        return user_resp.user.id if user_resp and user_resp.user else None
    except Exception:
        return None



# GET /api/songs
@app.get("/api/songs")
def get_songs():
    response = supabase.table("songs").select("*").order("id").execute()
    return {"songs": response.data}



# POST /api/recognize
@app.post("/api/recognize")
async def recognize_audio(
    file: UploadFile = File(...),
    authorization: Optional[str] = Header(default=None)
):
    audio_bytes = await file.read()
    try:
        # Decode audio bytes directly to a NumPy array
        raw_audio, sample_rate = sf.read(io.BytesIO(audio_bytes), dtype="float32")
    except Exception as e:
        raise HTTPException(
            status_code=400,
            detail=f"Could not decode audio file. Please upload a valid .wav snippet. ({str(e)})"
        )

    match_result = engine.recognize_snippet(raw_audio, sample_rate)

    if not match_result.get("matched"):
        return match_result

    #Fetch song metadata from Supabase
    song_id = match_result["song_id"]
    song_query = supabase.table("songs").select("*").eq("id", song_id).single().execute()
    song_metadata = song_query.data if song_query.data else {"title": match_result["song_title"]}

    #If valid Supabase user JWT, log this match to match_history
    user_id = get_user_id_from_auth_header(authorization)
    if user_id:
        supabase.table("match_history").insert({
            "user_id": user_id,
            "song_id": song_id,
            "matched_timestamp_sec": match_result["timestamp_seconds"],
            "confidence_hits": match_result["confidence_hits"],
            "noise_hashes_filtered": match_result["noise_hashes_filtered"],
            "match_time_ms": match_result["match_time_ms"]
        }).execute()

    return {
        **match_result,
        "song_metadata": song_metadata,
        "logged_to_history": bool(user_id)
    }

# GET /api/history
@app.get("/api/history")
def get_user_history(authorization: Optional[str] = Header(default=None)):
    user_id = get_user_id_from_auth_header(authorization)
    if not user_id:
        raise HTTPException(status_code=401, detail="Missing or invalid Bearer token.")

    response = (
        supabase.table("match_history")
        .select("*, songs(title, artist, cover_url, duration_seconds)")
        .eq("user_id", user_id)
        .order("created_at", desc=True)
        .limit(25)
        .execute()
    )
    return {"history": response.data}