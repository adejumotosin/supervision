"use client";

import { useEffect, useMemo, useRef, useState } from "react";
import { Activity, BarChart3, Boxes, BrainCircuit, Database, Gauge, LineChart, Radio, Search, UploadCloud, Video } from "lucide-react";
import * as tus from "tus-js-client";
import { domains, factors, history } from "@/lib/data";

const apiUrl = process.env.NEXT_PUBLIC_VISIONALPHA_API_URL || "http://localhost:8000";

type Analysis = {
  filename?: string;
  frames_processed?: number;
  unique_tracks?: number;
  activity_index?: number;
  counts?: Record<string, number>;
  persisted?: boolean;
};

type HistoryItem = {
  created_at?: string;
  activity_index?: number | string | null;
};

type SemanticUploadTicket = {
  token: string;
  tus_endpoint: string;
  bucket: string;
  object_path: string;
  asset_id: string;
  chunk_size: number;
};

type SemanticJob = {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "canceled";
  progress?: number | string;
  error?: string | null;
  analysis_run_id?: string | null;
};

type HealthPayload = {
  semantic_queue?: "enabled" | "disabled" | "unconfigured";
};

function LinePlot({ values }: { values: number[] }) {
  const points = useMemo(() => {
    const safeValues = values.length ? values : [50];
    const min = Math.min(...safeValues) - 3;
    const max = Math.max(...safeValues) + 3;
    const range = Math.max(max - min, 1);
    const denominator = Math.max(safeValues.length - 1, 1);
    return safeValues.map((v, i) => `${(i / denominator) * 100},${92 - ((v - min) / range) * 78}`).join(" ");
  }, [values]);
  const area = `0,100 ${points} 100,100`;
  return (
    <svg className="chart" viewBox="0 0 100 100" preserveAspectRatio="none" aria-label="Economic activity index history">
      <defs><linearGradient id="area" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#5f9de8" stopOpacity=".22"/><stop offset="100%" stopColor="#5f9de8" stopOpacity="0"/></linearGradient></defs>
      {[20,40,60,80].map(y => <line key={y} className="chart-grid" x1="0" y1={y} x2="100" y2={y}/>) }
      <polygon className="chart-area" points={area}/>
      <polyline className="chart-line" points={points}/>
    </svg>
  );
}

function DomainCard({ name, score, change, spark }: (typeof domains)[number]) {
  const max = Math.max(...spark);
  return (
    <div className="domain">
      <div className="domain-name">{name}</div>
      <div className="domain-score"><strong>{score.toFixed(1)}</strong><span className={`change ${change < 0 ? "negative" : ""}`}>{change >= 0 ? "+" : ""}{change.toFixed(1)}%</span></div>
      <div className="spark">{spark.map((h, i) => <span key={i} style={{ height: `${Math.max(10, (h / max) * 100)}%` }} />)}</div>
    </div>
  );
}

export default function Dashboard() {
  const quickInputRef = useRef<HTMLInputElement>(null);
  const semanticInputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [semanticBusy, setSemanticBusy] = useState(false);
  const [semanticEnabled, setSemanticEnabled] = useState(false);
  const [semanticProgress, setSemanticProgress] = useState(0);
  const [semanticJob, setSemanticJob] = useState<SemanticJob | null>(null);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [semanticError, setSemanticError] = useState<string | null>(null);
  const [historyData, setHistoryData] = useState<number[]>(history);
  const [usingPersistedHistory, setUsingPersistedHistory] = useState(false);

  async function loadHistory() {
    try {
      const response = await fetch(`${apiUrl}/api/v1/history?limit=30`, { cache: "no-store" });
      if (!response.ok) return;
      const payload = await response.json() as { items?: HistoryItem[] };
      const values = (payload.items || [])
        .map(item => Number(item.activity_index))
        .filter(value => Number.isFinite(value));
      if (values.length) {
        setHistoryData(values);
        setUsingPersistedHistory(true);
      }
    } catch {
      // Keep the seeded research series visible if persistence is unavailable.
    }
  }

  async function loadCapabilities() {
    try {
      const response = await fetch(`${apiUrl}/health`, { cache: "no-store" });
      if (!response.ok) return;
      const payload = await response.json() as HealthPayload;
      setSemanticEnabled(payload.semantic_queue === "enabled");
    } catch {
      setSemanticEnabled(false);
    }
  }

  useEffect(() => {
    void Promise.all([loadHistory(), loadCapabilities()]);
  }, []);

  async function analyzeQuick(file?: File) {
    if (!file) return;
    setBusy(true); setError(null); setAnalysis(null);
    const body = new FormData(); body.append("file", file);
    try {
      const response = await fetch(`${apiUrl}/api/v1/analyze`, { method: "POST", body });
      if (!response.ok) throw new Error(`Backend returned ${response.status}`);
      const result = await response.json() as Analysis;
      setAnalysis(result);
      if (result.persisted) await loadHistory();
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally { setBusy(false); }
  }

  function uploadWithTus(file: File, ticket: SemanticUploadTicket) {
    return new Promise<void>((resolve, reject) => {
      const upload = new tus.Upload(file, {
        endpoint: ticket.tus_endpoint,
        retryDelays: [0, 3000, 5000, 10000, 20000],
        headers: { "x-signature": ticket.token },
        uploadDataDuringCreation: true,
        removeFingerprintOnSuccess: true,
        chunkSize: ticket.chunk_size,
        metadata: {
          bucketName: ticket.bucket,
          objectName: ticket.object_path,
          contentType: file.type || "video/mp4",
          cacheControl: "3600",
        },
        onError: error => reject(error),
        onProgress: (uploaded, total) => {
          setSemanticProgress(total > 0 ? (uploaded / total) * 100 : 0);
        },
        onSuccess: () => resolve(),
      });

      upload.findPreviousUploads()
        .then(previous => {
          if (previous.length) upload.resumeFromPreviousUpload(previous[0]);
          upload.start();
        })
        .catch(reject);
    });
  }

  async function pollSemanticJob(jobId: string) {
    for (let attempt = 0; attempt < 120; attempt += 1) {
      const response = await fetch(`${apiUrl}/api/v1/jobs/${jobId}`, { cache: "no-store" });
      if (!response.ok) throw new Error(`Job status returned ${response.status}`);
      const job = await response.json() as SemanticJob;
      setSemanticJob(job);

      if (job.status === "succeeded") {
        await loadHistory();
        return;
      }
      if (job.status === "failed" || job.status === "canceled") {
        throw new Error(job.error || `Semantic job ${job.status}`);
      }
      await new Promise(resolve => setTimeout(resolve, 3000));
    }
    throw new Error("Semantic processing is taking longer than expected. The job remains in the queue.");
  }

  async function analyzeSemantic(file?: File) {
    if (!file || !semanticEnabled) return;
    setSemanticBusy(true);
    setSemanticProgress(0);
    setSemanticJob(null);
    setSemanticError(null);

    try {
      const signResponse = await fetch(`${apiUrl}/api/v1/uploads/sign`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          filename: file.name,
          content_type: file.type || null,
          size_bytes: file.size,
        }),
      });
      if (!signResponse.ok) throw new Error(`Upload authorization returned ${signResponse.status}`);
      const ticket = await signResponse.json() as SemanticUploadTicket;

      await uploadWithTus(file, ticket);
      setSemanticProgress(100);

      const jobResponse = await fetch(`${apiUrl}/api/v1/jobs`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ asset_id: ticket.asset_id }),
      });
      if (!jobResponse.ok) throw new Error(`Job submission returned ${jobResponse.status}`);
      const job = await jobResponse.json() as SemanticJob;
      setSemanticJob(job);
      await pollSemanticJob(job.id);
    } catch (e) {
      setSemanticError(e instanceof Error ? e.message : "Semantic analysis failed");
    } finally {
      setSemanticBusy(false);
    }
  }

  const latestIndex = historyData.at(-1) ?? 82.41;
  const firstIndex = historyData[0] ?? latestIndex;
  const changePct = historyData.length > 1 ? ((latestIndex - firstIndex) / Math.max(Math.abs(firstIndex), 0.001)) * 100 : 0;
  const regime = latestIndex >= 55 ? "ECONOMIC EXPANSION" : latestIndex <= 45 ? "ECONOMIC CONTRACTION" : "NEUTRAL ACTIVITY";
  const semanticProgressLabel = `${semanticProgress.toFixed(1)}%`;
  const semanticJobProgress = semanticJob?.progress == null ? null : Number(semanticJob.progress);

  return (
    <div className="shell">
      <header className="topbar">
        <div className="brand"><div className="brand-mark">Vα</div><div className="brand-name">VISION<span>ALPHA</span></div></div>
        <div className="market-status"><span className="dot"/> DATA ENGINE ONLINE <Search size={14}/></div>
      </header>
      <div className="layout">
        <aside className="sidebar">
          <div className="nav-label">INTELLIGENCE</div>
          <button className="nav-item active"><BarChart3/> Overview</button>
          <button className="nav-item"><LineChart/> Activity Indices</button>
          <button className="nav-item"><BrainCircuit/> Signals</button>
          <div className="nav-label" style={{marginTop: 24}}>VISION</div>
          <button className="nav-item"><Video/> Ingestion</button>
          <button className="nav-item"><Boxes/> Object Flows</button>
          <button className="nav-item"><Gauge/> Zone Metrics</button>
          <div className="nav-label" style={{marginTop: 24}}>DATA</div>
          <button className="nav-item"><Database/> Sources</button>
          <button className="nav-item"><Activity/> Backtests</button>
          <div className="sidebar-foot"><strong>Research build 0.3</strong><span>Full Engine observations are normalized to per-minute rates before location-specific baseline calibration.</span></div>
        </aside>

        <main className="main">
          <div className="hero-row">
            <div><div className="eyebrow">Alternative Data Intelligence</div><h1>Economic Activity Monitor</h1><div className="subtitle">Computer vision derived activity proxies, standardized for investment research.</div></div>
            <div className="actions">
              <button className="btn"><Radio size={14}/> {usingPersistedHistory ? "Live History" : "Demo Feed"}</button>
              <button className="btn" onClick={() => quickInputRef.current?.click()} disabled={busy || semanticBusy}><Video size={14}/>{busy ? "Analyzing" : "Quick Test"}</button>
              <button className="btn primary" onClick={() => semanticInputRef.current?.click()} disabled={!semanticEnabled || semanticBusy || busy}><UploadCloud size={14}/>{semanticEnabled ? (semanticBusy ? "Processing" : "Full Engine") : "Full Engine Soon"}</button>
            </div>
          </div>

          <div className="grid">
            <section className="panel index-panel">
              <div className="panel-head"><div className="panel-title">VisionAlpha Economic Activity Index</div><div className="panel-meta">Composite · {usingPersistedHistory ? `${historyData.length} observations` : "30D demo"}</div></div>
              <div className="index-body"><div className="big-index"><strong>{latestIndex.toFixed(2)}</strong><span className={`delta ${changePct < 0 ? "negative" : ""}`}>{changePct >= 0 ? "▲" : "▼"} {Math.abs(changePct).toFixed(2)}%</span></div><div className="regime">● {regime}</div><LinePlot values={historyData}/></div>
            </section>

            <section className="panel signal-panel">
              <div className="panel-head"><div className="panel-title">Model Signal</div><div className="panel-meta">NGA · PORT & LOGISTICS</div></div>
              <div className="signal-body"><div className="signal-hero"><div className="signal-top"><span className="signal-name">Port & Logistics Activity</span><span className="badge">RESEARCH</span></div><div className="confidence"><span>Baseline status</span><strong>PROVISIONAL</strong></div><div className="bar"><span style={{width:"50%"}}/></div></div><p className="thesis">Phase 3 separates truck, boat, bus and car flow into a dedicated logistics index. Production signals require location, camera, hour, weekday and seasonal calibration before investment use.</p></div>
            </section>

            <section className="panel domain-panel">
              <div className="panel-head"><div className="panel-title">Domain Activity Indices</div><div className="panel-meta">vs calibrated baseline</div></div>
              <div className="domains">{domains.map(d => <DomainCard key={d.name} {...d}/>)}</div>
              <div className="table-wrap"><table><thead><tr><th>Factor</th><th>Change</th><th>Direction</th><th>Quality</th></tr></thead><tbody>{factors.map(row => <tr key={row[0]}>{row.map((x,i) => <td key={x} className={i===2 ? (x === "Positive" ? "up" : "down") : ""}>{x}</td>)}</tr>)}</tbody></table></div>
            </section>

            <section className="panel ingest-panel">
              <div className="panel-head"><div className="panel-title">Vision Ingestion</div><div className="panel-meta">VIDEO → STORAGE → GPU → FACTORS</div></div>
              <div className="upload">
                <input ref={quickInputRef} hidden type="file" accept="video/*" onChange={e => analyzeQuick(e.target.files?.[0])}/>
                <input ref={semanticInputRef} hidden type="file" accept="video/*" disabled={!semanticEnabled} onChange={e => analyzeSemantic(e.target.files?.[0])}/>
                <div className="drop" onClick={() => semanticEnabled && semanticInputRef.current?.click()}><div><UploadCloud/><strong>{semanticEnabled ? (semanticBusy ? `Full Engine ${semanticProgressLabel}` : "Upload for semantic analysis") : "Full Engine worker deployment pending"}</strong><span>{semanticEnabled ? "Resumable upload for roads, ports, stores, sites and industrial video" : "Quick Test remains available while semantic compute is being provisioned"}</span></div></div>
                {semanticJob && <div className="result"><strong>Full Engine job: {semanticJob.status}</strong><br/>Upload {semanticProgressLabel}{semanticJobProgress != null ? ` · Processing ${semanticJobProgress.toFixed(0)}%` : ""}{semanticJob.analysis_run_id ? " · saved to history" : ""}</div>}
                {semanticError && <div className="result"><strong>Full Engine unavailable</strong><br/>{semanticError}</div>}
                {analysis && <div className="result"><strong>Quick analysis complete</strong><br/>{analysis.frames_processed?.toLocaleString()} frames sampled · {analysis.unique_tracks} unique tracks · Activity index {analysis.activity_index?.toFixed(1)}{analysis.persisted ? " · saved to history" : ""}</div>}
                {error && <div className="result"><strong>Quick analysis unavailable</strong><br/>{error}. The research dashboard remains available in demo mode.</div>}
              </div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
