import { useEffect, useRef, useState, useCallback } from "react";

const WS_URL = import.meta.env.VITE_WS_URL || "ws://localhost:8000";
const FPS_TARGET = 15; // capture rate from webcam

export default function VideoFeed({ sessionId, onFaceDetected, onConnectionChange }) {
  const videoRef = useRef(null);      // raw webcam <video>
  const canvasRef = useRef(null);     // hidden capture canvas
  const displayRef = useRef(null);    // annotated frame display
  const wsRef = useRef(null);
  const intervalRef = useRef(null);

  const [error, setError] = useState(null);
  const [streaming, setStreaming] = useState(false);
  const [frameCount, setFrameCount] = useState(0);

  // ── WebSocket setup ───────────────────────────────────────────────────────
  const connectWS = useCallback(() => {
    const url = `${WS_URL}/ws/feed?session_id=${sessionId}`;
    const ws = new WebSocket(url);
    ws.binaryType = "arraybuffer";

    ws.onopen = () => {
      onConnectionChange(true);
      setError(null);
    };

    ws.onmessage = (evt) => {
      try {
        const data = JSON.parse(evt.data);
        if (data.error) return;

        // Update display image with annotated frame
        if (data.frame && displayRef.current) {
          displayRef.current.src = `data:image/jpeg;base64,${data.frame}`;
        }
        if (data.face_found) onFaceDetected?.();
        setFrameCount((n) => n + 1);
      } catch (_) {}
    };

    ws.onclose = () => onConnectionChange(false);
    ws.onerror = () => setError("WebSocket connection failed.");
    wsRef.current = ws;
  }, [sessionId, onFaceDetected, onConnectionChange]);

  // ── Start webcam + capture loop ───────────────────────────────────────────
  const startStream = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: 640, height: 480, facingMode: "user" },
      });
      videoRef.current.srcObject = stream;
      await videoRef.current.play();

      connectWS();

      intervalRef.current = setInterval(() => {
        if (wsRef.current?.readyState !== WebSocket.OPEN) return;
        const canvas = canvasRef.current;
        const video = videoRef.current;
        if (!canvas || !video) return;

        canvas.width = video.videoWidth || 640;
        canvas.height = video.videoHeight || 480;
        canvas.getContext("2d").drawImage(video, 0, 0);

        canvas.toBlob(
          (blob) => {
            if (blob) blob.arrayBuffer().then((buf) => wsRef.current?.send(buf));
          },
          "image/jpeg",
          0.8
        );
      }, 1000 / FPS_TARGET);

      setStreaming(true);
    } catch (err) {
      setError(`Camera error: ${err.message}`);
    }
  };

  const stopStream = () => {
    clearInterval(intervalRef.current);
    wsRef.current?.close();
    videoRef.current?.srcObject?.getTracks().forEach((t) => t.stop());
    setStreaming(false);
    onConnectionChange(false);
  };

  useEffect(() => () => stopStream(), []); // cleanup on unmount

  return (
    <div className="video-feed">
      {/* Hidden elements for capture */}
      <video ref={videoRef} style={{ display: "none" }} muted playsInline />
      <canvas ref={canvasRef} style={{ display: "none" }} />

      {/* Annotated frame display */}
      <div className="frame-display">
        {streaming ? (
          <img
            ref={displayRef}
            alt="Annotated video feed"
            className="feed-img"
          />
        ) : (
          <div className="feed-placeholder">
            <span>📷</span>
            <p>Camera not started</p>
          </div>
        )}
      </div>

      {error && <p className="error-msg">⚠️ {error}</p>}

      <div className="feed-controls">
        {!streaming ? (
          <button className="btn btn-start" onClick={startStream}>
            ▶ Start Camera
          </button>
        ) : (
          <button className="btn btn-stop" onClick={stopStream}>
            ■ Stop
          </button>
        )}
        <span className="frame-counter">Frames: {frameCount}</span>
      </div>
    </div>
  );
}
