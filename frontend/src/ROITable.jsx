import { useEffect, useState } from "react";

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const POLL_INTERVAL = 1500; // ms

export default function ROITable({ sessionId }) {
  const [rows, setRows] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    const fetchROI = async () => {
      setLoading(true);
      try {
        const url = `${API_URL}/roi?session_id=${sessionId}&limit=20`;
        const resp = await fetch(url);
        if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
        const data = await resp.json();
        setRows(data.items || []);
        setTotal(data.total || 0);
      } catch (_) {
        // silently retry
      } finally {
        setLoading(false);
      }
    };

    fetchROI();
    const timer = setInterval(fetchROI, POLL_INTERVAL);
    return () => clearInterval(timer);
  }, [sessionId]);

  return (
    <div className="roi-table-wrap">
      <div className="roi-header">
        <span>Total detections: <strong>{total}</strong></span>
        {loading && <span className="loading-dot">●</span>}
      </div>

      {rows.length === 0 ? (
        <p className="no-data">No detections yet. Start the camera feed.</p>
      ) : (
        <table className="roi-table">
          <thead>
            <tr>
              <th>#</th>
              <th>x1</th>
              <th>y1</th>
              <th>x2</th>
              <th>y2</th>
              <th>Confidence</th>
              <th>Detected At</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((row, i) => (
              <tr key={row.id}>
                <td>{total - i}</td>
                <td>{row.roi.x1}</td>
                <td>{row.roi.y1}</td>
                <td>{row.roi.x2}</td>
                <td>{row.roi.y2}</td>
                <td>{row.confidence != null ? `${(row.confidence * 100).toFixed(1)}%` : "—"}</td>
                <td>{new Date(row.detected_at).toLocaleTimeString()}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </div>
  );
}
