import { useEffect, useRef, useState } from "react";
import axios from "axios";
import {
  Mic,
  Upload,
  Music2,
  X,
  Clock,
  AudioLines,
  ArrowUpRight,
  Disc3,
  Headphones,
  Loader2,
} from "lucide-react";
import { supabase } from "./supabaseClient";
import { encodeWAV } from "./wavHelper";
import "./App.css";

const API_BASE = import.meta.env.VITE_API_BASE_URL || "http://127.0.0.1:8000";
const DURATION = 5000;
const LOCAL_STORAGE_KEY = "earshot_guest_history";

// High-resolution embedded SVG vinyl fallback so the record looks crisp even if vinyl.jpg isn't copied
const FALLBACK_VINYL =
  "data:image/svg+xml;utf8," +
  encodeURIComponent(`
<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 500 500">
  <defs>
    <radialGradient id="sheen" cx="50%" cy="50%" r="50%">
      <stop offset="0%" stop-color="#222"/>
      <stop offset="45%" stop-color="#111"/>
      <stop offset="70%" stop-color="#292929"/>
      <stop offset="100%" stop-color="#0a0a0a"/>
    </radialGradient>
  </defs>
  <circle cx="250" cy="250" r="246" fill="url(#sheen)" stroke="#333" stroke-width="2"/>
  <circle cx="250" cy="250" r="220" fill="none" stroke="#2c2c2c" stroke-width="1"/>
  <circle cx="250" cy="250" r="195" fill="none" stroke="#252525" stroke-width="1.5"/>
  <circle cx="250" cy="250" r="170" fill="none" stroke="#2c2c2c" stroke-width="1"/>
  <circle cx="250" cy="250" r="145" fill="none" stroke="#222" stroke-width="1.5"/>
  <circle cx="250" cy="250" r="120" fill="none" stroke="#2f2f2f" stroke-width="1"/>
  <circle cx="250" cy="250" r="82" fill="#c84b31"/>
  <circle cx="250" cy="250" r="68" fill="none" stroke="#e07a5f" stroke-width="1" opacity="0.5"/>
  <circle cx="250" cy="250" r="14" fill="#f7f4ef"/>
</svg>`);

function formatOffset(sec) {
  const s = Math.max(0, Math.round(Number(sec) || 0));
  const mins = Math.floor(s / 60);
  const rem = s % 60;
  return `${String(mins).padStart(2, "0")}:${String(rem).padStart(2, "0")}`;
}

function loadLocalHistory() {
  try {
    return JSON.parse(localStorage.getItem(LOCAL_STORAGE_KEY) || "[]");
  } catch {
    return [];
  }
}

function saveLocalHistory(items) {
  try {
    localStorage.setItem(LOCAL_STORAGE_KEY, JSON.stringify(items.slice(0, 30)));
  } catch {
    // ignore storage errors
  }
}

export default function App() {
  const canvasRef = useRef(null);
  const [status, setStatus] = useState("idle"); // "idle" | "recording" | "matching"
  const [progress, setProgress] = useState(0);
  const [result, setResult] = useState(null);
  const [notFound, setNotFound] = useState(false);
  const [error, setError] = useState(null);
  const [history, setHistory] = useState(() => loadLocalHistory());
  const [dragging, setDragging] = useState(false);

  // Supabase Auth state
  const [session, setSession] = useState(null);
  const [showAuthModal, setShowAuthModal] = useState(false);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [authNotice, setAuthNotice] = useState("");

  const fetchSupabaseHistory = async (token) => {
    try {
      const res = await axios.get(`${API_BASE}/api/history`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      const mapped = (res.data.history || []).map((item) => ({
        id: item.id,
        title: item.songs?.title || `Song #${item.song_id}`,
        artist: item.songs?.artist || "Indexed Artist",
        album: item.songs?.album || "",
        cover_url: item.songs?.cover_url || null,
        offset_seconds: item.matched_timestamp_sec ?? 0,
        confidence_hits: item.confidence_hits,
        at: item.created_at,
      }));
      setHistory(mapped);
    } catch (err) {
      console.error("Failed to fetch Supabase history:", err);
    }
  };

  useEffect(() => {
    supabase.auth.getSession().then(({ data: { session: cur } }) => {
      setSession(cur);
      if (cur?.access_token) {
        fetchSupabaseHistory(cur.access_token);
      }
    });

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, newSession) => {
      setSession(newSession);
      if (newSession?.access_token) {
        fetchSupabaseHistory(newSession.access_token);
      } else {
        setHistory(loadLocalHistory());
      }
    });

    return () => subscription.unsubscribe();
  }, []);

  const handleSignIn = async (e) => {
    e.preventDefault();
    setAuthNotice("");
    const { error: signInErr } = await supabase.auth.signInWithPassword({
      email,
      password,
    });
    if (signInErr) setAuthNotice(signInErr.message);
    else setShowAuthModal(false);
  };

  const handleSignUp = async () => {
    setAuthNotice("");
    const { error: signUpErr } = await supabase.auth.signUp({ email, password });
    if (signUpErr) setAuthNotice(signUpErr.message);
    else setAuthNotice("Account created! Click Sign In.");
  };

  const handleSignOut = async () => {
    await supabase.auth.signOut();
    setShowAuthModal(false);
  };

  async function submit(blob, name) {
    setStatus("matching");
    setError(null);
    setNotFound(false);
    try {
      const formData = new FormData();
      formData.append("file", blob, name);

      const headers = {};
      if (session?.access_token) {
        headers["Authorization"] = `Bearer ${session.access_token}`;
      }

      const res = await axios.post(`${API_BASE}/api/recognize`, formData, {
        headers,
      });
      const data = res.data;

      if (!data || !data.matched) {
        setNotFound(true);
      } else {
        const matchObj = {
          id: crypto.randomUUID(),
          title: data.song_metadata?.title || data.song_title || "Unknown Track",
          artist: data.song_metadata?.artist || "Featured Artist",
          album: data.song_metadata?.album || "",
          cover_url: data.song_metadata?.cover_url || null,
          offset_seconds: data.timestamp_seconds ?? 0,
          confidence_hits: data.confidence_hits ?? 0,
          noise_hashes_filtered: data.noise_hashes_filtered ?? 0,
          match_time_ms: data.match_time_ms ?? 0,
          at: new Date().toISOString(),
        };
        setResult(matchObj);

        if (session?.access_token) {
          fetchSupabaseHistory(session.access_token);
        } else {
          const next = [matchObj, ...history];
          setHistory(next);
          saveLocalHistory(next);
        }
      }
    } catch (e) {
      setError(
        e.response?.data?.detail ||
          (e instanceof Error ? e.message : "Recognition failed")
      );
    } finally {
      setStatus("idle");
    }
  }

  async function record() {
    if (status !== "idle") return;
    setError(null);
    setNotFound(false);

    let stream;
    try {
      stream = await navigator.mediaDevices.getUserMedia({ audio: true });
    } catch {
      setError("Microphone access was denied.");
      return;
    }

    const ctx = new (window.AudioContext || window.webkitAudioContext)({
      sampleRate: 44100,
    });
    const source = ctx.createMediaStreamSource(stream);
    const analyser = ctx.createAnalyser();
    analyser.fftSize = 1024;
    source.connect(analyser);
    const data = new Uint8Array(analyser.frequencyBinCount);

    // Capture raw PCM Float32 samples so we can encode a genuine .wav file for Python soundfile
    const processor = ctx.createScriptProcessor(4096, 1, 1);
    const pcmChunks = [];
    processor.onaudioprocess = (e) => {
      pcmChunks.push(new Float32Array(e.inputBuffer.getChannelData(0)));
    };
    source.connect(processor);
    processor.connect(ctx.destination);

    const canvas = canvasRef.current;
    const g = canvas?.getContext("2d");
    if (!canvas || !g) {
      stream.getTracks().forEach((t) => t.stop());
      await ctx.close();
      setError("Audio visualization is unavailable. Please try uploading a file.");
      return;
    }

    canvas.width = canvas.clientWidth * devicePixelRatio;
    canvas.height = canvas.clientHeight * devicePixelRatio;
    const bgStyle =
      getComputedStyle(canvas).getPropertyValue("--visualizer-background").trim() ||
      "#f2efe9";
    const primaryStyle =
      getComputedStyle(canvas).getPropertyValue("--primary").trim() || "#c84b31";

    g.fillStyle = bgStyle;
    g.fillRect(0, 0, canvas.width, canvas.height);

    const start = performance.now();
    let raf = 0;
    const col = 2 * devicePixelRatio;

    const draw = () => {
      analyser.getByteFrequencyData(data);
      g.drawImage(canvas, -col, 0);
      const bins = data.length / 2;
      const h = canvas.height / bins;
      for (let i = 0; i < bins; i++) {
        const v = (data[i] ?? 0) / 255;
        g.fillStyle = `color-mix(in oklab, ${primaryStyle} ${Math.round(
          v * 100
        )}%, ${bgStyle})`;
        g.fillRect(canvas.width - col, canvas.height - (i + 1) * h, col, h + 1);
      }
      setProgress(Math.min(1, (performance.now() - start) / DURATION));
      raf = requestAnimationFrame(draw);
    };

    setStatus("recording");
    draw();

    setTimeout(async () => {
      cancelAnimationFrame(raf);
      processor.disconnect();
      source.disconnect();
      stream.getTracks().forEach((t) => t.stop());
      await ctx.close();
      setProgress(0);

      const totalLength = pcmChunks.reduce((acc, cur) => acc + cur.length, 0);
      const flatSamples = new Float32Array(totalLength);
      let offset = 0;
      for (const chunk of pcmChunks) {
        flatSamples.set(chunk, offset);
        offset += chunk.length;
      }

      const wavBlob = encodeWAV(flatSamples, 44100);
      submit(wavBlob, "recording.wav");
    }, DURATION);
  }

  function onFile(file) {
    if (!file) return;
    if (!/\.wav$/i.test(file.name) && file.type !== "audio/wav") {
      setError("Please drop a .wav file.");
      return;
    }
    submit(file, file.name);
  }

  return (
    <main className="earshot-shell">
      <header className="site-header">
        <a href="/" className="wordmark" aria-label="Earshot home">
          <AudioLines className="text-primary" />
          earshot<span className="text-primary">.</span>
        </a>
        <div className="header-caption">FOR THE LOVE OF MUSIC</div>
        <button
          type="button"
          className="guest-label"
          onClick={() => setShowAuthModal((v) => !v)}
        >
          <span className={`status-dot ${session ? "online" : ""}`} />
          {session ? session.user.email : "Guest session"}
        </button>

        {showAuthModal && (
          <div className="auth-popover">
            {session ? (
              <>
                <h4>Signed In</h4>
                <p>Matches are automatically saved to your Supabase collection.</p>
                <button
                  type="button"
                  onClick={handleSignOut}
                  className="btn-earshot-Ghost"
                  style={{ width: "100%" }}
                >
                  Sign Out
                </button>
              </>
            ) : (
              <form onSubmit={handleSignIn}>
                <h4>Listener Account</h4>
                <p>Sign in with Supabase to sync your Past Shazams.</p>
                <input
                  type="email"
                  placeholder="Email (e.g. test@amrita.edu)"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                  className="auth-input"
                />
                <input
                  type="password"
                  placeholder="Password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  required
                  className="auth-input"
                />
                {authNotice && (
                  <p style={{ color: "var(--primary)", marginBottom: "8px" }}>
                    {authNotice}
                  </p>
                )}
                <div className="auth-actions">
                  <button type="submit" className="btn-earshot-primary">
                    Sign In
                  </button>
                  <button
                    type="button"
                    onClick={handleSignUp}
                    className="btn-earshot-Ghost"
                  >
                    Sign Up
                  </button>
                </div>
              </form>
            )}
          </div>
        )}
      </header>

      <section className="intro">
        <p className="eyebrow">
          <span className="short-rule" /> EVERY SONG HAS A NAME
        </p>
        <h1>
          Find your <em>next favorite.</em>
        </h1>
        <p className="intro-copy">
          That song you can’t get out of your head? Let’s put a name to it.
        </p>
      </section>

      <div className="workspace">
        <section className="listening-section" aria-label="Song recognition">
          <div className="section-label">
            <span>01 / THE LISTENING ROOM</span>
            <span className="live-label">
              <span className="status-dot" />{" "}
              {status === "recording"
                ? "LISTENING"
                : status === "matching"
                ? "MATCHING"
                : "READY WHEN YOU ARE"}
            </span>
          </div>

          <div className="record-stage">
            <div
              className={`vinyl-wrap ${
                status === "recording" ? "is-recording" : ""
              }`}
            >
              <img
                src={FALLBACK_VINYL}
                width={1024}
                height={1024}
                alt="Classic vinyl record with a red center label"
                className="vinyl-image"
              />
              <button
                type="button"
                onClick={record}
                disabled={status !== "idle"}
                aria-label="Record 5 seconds"
                className="record-button"
                title="Record 5 seconds"
              >
                {status === "matching" ? (
                  <Loader2 className="animate-spin" />
                ) : (
                  <Mic />
                )}
              </button>
            </div>
            <div className="record-caption">
              <h2>
                {status === "recording"
                  ? "A little closer. Keep listening."
                  : status === "matching"
                  ? "Finding your song…"
                  : "A little listening. A new discovery."}
              </h2>
              <p>
                {status === "recording"
                  ? `${Math.ceil((1 - progress) * 5)} seconds remaining`
                  : "5 seconds is all it takes."}
              </p>
            </div>
          </div>

          <div
            className={`frequency-strip ${
              status === "recording" ? "active" : ""
            }`}
          >
            <AudioLines size={18} className="text-primary" />
            <div className="frequency-display">
              <div className="idle-wave" aria-hidden="true">
                {Array.from({ length: 65 }, (_, i) => (
                  <span
                    key={i}
                    style={{
                      height: `${
                        4 + Math.abs(Math.sin(i * 1.8) * Math.cos(i * 0.35)) * 23
                      }px`,
                    }}
                  />
                ))}
              </div>
              <canvas ref={canvasRef} className="frequency-canvas" />
            </div>
            <span className="frequency-time">
              {status === "recording"
                ? `00:0${Math.min(5, Math.floor(progress * 5))}`
                : "00:05"}
            </span>
          </div>

          <label
            onDragOver={(e) => {
              e.preventDefault();
              setDragging(true);
            }}
            onDragLeave={() => setDragging(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDragging(false);
              if (status === "idle") onFile(e.dataTransfer.files[0]);
            }}
            className={`upload-zone ${dragging ? "dragging" : ""} ${
              status !== "idle" ? "upload-disabled" : ""
            }`}
          >
            <span className="upload-icon">
              <Upload size={21} />
            </span>
            <span className="upload-copy">
              <strong>Or, bring your own sound</strong>
              <span>
                Drop a .wav snippet here, or{" "}
                <span className="text-primary">browse files</span>
              </span>
            </span>
            <ArrowUpRight className="upload-arrow" size={20} />
            <input
              type="file"
              aria-label="Upload WAV snippet"
              accept=".wav,audio/wav"
              disabled={status !== "idle"}
              className="sr-only"
              onChange={(e) => {
                onFile(e.target.files?.[0]);
                e.target.value = "";
              }}
            />
          </label>

          {error && (
            <p role="alert" className="alert-error">
              {error}
            </p>
          )}
          {notFound && (
            <p role="status" className="status-not-found">
              No match found. Try again closer to the speaker.
            </p>
          )}
        </section>

        <aside className="history-section">
          <div className="section-label">
            <span>02 / YOUR COLLECTION</span>
            <Headphones size={16} />
          </div>
          <div className="history-heading">
            <h2>
              Past Shazams<span className="text-primary">.</span>
            </h2>
            <span className="history-count">
              {String(history.length).padStart(2, "0")}
            </span>
          </div>

          {history.length === 0 ? (
            <div className="empty-history">
              <span className="empty-disc">
                <Disc3 size={42} strokeWidth={1} />
              </span>
              <h3>A collection in the making.</h3>
              <p>Your next great find belongs here.</p>
              <span className="empty-line" />
            </div>
          ) : (
            <ul className="history-list">
              {history.map((h) => (
                <li key={h.id}>
                  <button
                    type="button"
                    className="history-item"
                    onClick={() => setResult(h)}
                  >
                    <Cover m={h} className="cover-thumb-sm" />
                    <span className="history-item-meta">
                      <span className="history-item-title">{h.title}</span>
                      <span className="history-item-sub">
                        {h.artist} · {new Date(h.at).toLocaleDateString()}
                      </span>
                    </span>
                    <span className="history-item-offset">
                      {formatOffset(h.offset_seconds)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}

          <div className="collection-note">
            <Music2 size={16} />
            <span>Good music is worth remembering.</span>
          </div>
        </aside>
      </div>

      <footer className="site-footer">
        <span>A WORLD OF MUSIC. ONE LITTLE LISTEN.</span>
        <span>
          Made for curious ears <AudioLines size={15} className="text-primary" />
        </span>
      </footer>

      {result && (
        <div className="modal-backdrop" onClick={() => setResult(null)}>
          <div
            role="dialog"
            aria-modal="true"
            aria-labelledby="match-title"
            className="modal-card"
            onClick={(e) => e.stopPropagation()}
          >
            <button
              type="button"
              onClick={() => setResult(null)}
              aria-label="Close"
              className="modal-close"
            >
              <X size={18} />
            </button>
            <p className="eyebrow modal-eyebrow">A NEW DISCOVERY</p>
            <Cover m={result} className="cover-thumb-lg" />
            <h3 id="match-title" className="modal-title">
              {result.title}
            </h3>
            <p className="modal-artist">{result.artist}</p>
            {result.album && (
              <p className="modal-artist" style={{ fontSize: "12px" }}>
                {result.album}
              </p>
            )}
            <p className="modal-badge">
              <Clock size={15} /> Matched at {formatOffset(result.offset_seconds)}
            </p>

            {result.confidence_hits !== undefined && (
              <div className="dsp-telemetry">
                <div>
                  <span>CONFIDENCE</span>
                  <strong>{result.confidence_hits} hits</strong>
                </div>
                <div>
                  <span>RADIX FILTER</span>
                  <strong>{result.noise_hashes_filtered ?? 0} noise</strong>
                </div>
                <div>
                  <span>LATENCY</span>
                  <strong>{result.match_time_ms ?? 0} ms</strong>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </main>
  );
}

function Cover({ m, className }) {
  return (
    <img
      src={m.cover_url || FALLBACK_VINYL}
      alt={m.title || "Vinyl record"}
      className={className}
    />
  );
}