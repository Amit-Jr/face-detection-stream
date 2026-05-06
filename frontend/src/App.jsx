import { useState } from "react";
import VideoFeed from "./VideoFeed";
import ROITable from "./ROITable";
import "./App.css";

export default function App() {
  const [sessionId] = useState(() => crypto.randomUUID());
  const [faceCount, setFaceCount] = useState(0);
  const [connected, setConnected] = useState(false);

  return (
    <div className="app">
      <header className="app-header">
        <div className="header-left">
          <span className="logo">⬡</span>
          <h1>Face Detection Stream</h1>
        </div>
        <div className="header-right">
          <span className={`status-dot ${connected ? "connected" : "disconnected"}`} />
          <span className="status-label">{connected ? "Live" : "Offline"}</span>
          <span className="face-badge">Faces detected: {faceCount}</span>
        </div>
      </header>

      <main className="app-main">
        <section className="video-section">
          <h2>Live Feed</h2>
          <VideoFeed
            sessionId={sessionId}
            onFaceDetected={() => setFaceCount((n) => n + 1)}
            onConnectionChange={setConnected}
          />
        </section>

        <section className="roi-section">
          <h2>ROI Data</h2>
          <ROITable sessionId={sessionId} />
        </section>
      </main>
    </div>
  );
}
