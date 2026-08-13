"use client";

import { useMemo, useRef, useState } from "react";
import { Activity, BarChart3, Boxes, BrainCircuit, Database, Gauge, LineChart, Radio, Search, UploadCloud, Video } from "lucide-react";
import { domains, factors, history } from "@/lib/data";

const apiUrl = process.env.NEXT_PUBLIC_VISIONALPHA_API_URL || "http://localhost:8000";

type Analysis = {
  filename?: string;
  frames_processed?: number;
  unique_tracks?: number;
  activity_index?: number;
  counts?: Record<string, number>;
};

function LinePlot() {
  const points = useMemo(() => {
    const min = Math.min(...history) - 3;
    const max = Math.max(...history) + 3;
    return history.map((v, i) => `${(i / (history.length - 1)) * 100},${92 - ((v - min) / (max - min)) * 78}`).join(" ");
  }, []);
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
  const inputRef = useRef<HTMLInputElement>(null);
  const [busy, setBusy] = useState(false);
  const [analysis, setAnalysis] = useState<Analysis | null>(null);
  const [error, setError] = useState<string | null>(null);

  async function analyze(file?: File) {
    if (!file) return;
    setBusy(true); setError(null); setAnalysis(null);
    const body = new FormData(); body.append("file", file);
    try {
      const response = await fetch(`${apiUrl}/api/v1/analyze`, { method: "POST", body });
      if (!response.ok) throw new Error(`Backend returned ${response.status}`);
      setAnalysis(await response.json());
    } catch (e) {
      setError(e instanceof Error ? e.message : "Analysis failed");
    } finally { setBusy(false); }
  }

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
          <div className="sidebar-foot"><strong>Research build 0.1</strong><span>Raw CV observations are normalized against location-specific baselines before becoming investment factors.</span></div>
        </aside>

        <main className="main">
          <div className="hero-row">
            <div><div className="eyebrow">Alternative Data Intelligence</div><h1>Economic Activity Monitor</h1><div className="subtitle">Computer vision derived activity proxies, standardized for investment research.</div></div>
            <div className="actions"><button className="btn"><Radio size={14}/> Demo Feed</button><button className="btn primary" onClick={() => inputRef.current?.click()} disabled={busy}><UploadCloud size={14}/>{busy ? "Analyzing" : "Analyze Video"}</button></div>
          </div>

          <div className="grid">
            <section className="panel index-panel">
              <div className="panel-head"><div className="panel-title">VisionAlpha Economic Activity Index</div><div className="panel-meta">Composite · 30D</div></div>
              <div className="index-body"><div className="big-index"><strong>82.41</strong><span className="delta">▲ 3.82%</span></div><div className="regime">● ECONOMIC EXPANSION</div><LinePlot/></div>
            </section>

            <section className="panel signal-panel">
              <div className="panel-head"><div className="panel-title">Model Signal</div><div className="panel-meta">NGA · INDUSTRIAL</div></div>
              <div className="signal-body"><div className="signal-hero"><div className="signal-top"><span className="signal-name">Nigeria Industrial Activity</span><span className="badge">BULLISH</span></div><div className="confidence"><span>Signal confidence</span><strong>87%</strong></div><div className="bar"><span style={{width:"87%"}}/></div></div><p className="thesis">Transport, port and heavy-equipment activity are above baseline while retail footfall remains soft. The composite currently indicates broad physical-economy expansion.</p></div>
            </section>

            <section className="panel domain-panel">
              <div className="panel-head"><div className="panel-title">Domain Activity Indices</div><div className="panel-meta">vs calibrated baseline</div></div>
              <div className="domains">{domains.map(d => <DomainCard key={d.name} {...d}/>)}</div>
              <div className="table-wrap"><table><thead><tr><th>Factor</th><th>Change</th><th>Direction</th><th>Quality</th></tr></thead><tbody>{factors.map(row => <tr key={row[0]}>{row.map((x,i) => <td key={x} className={i===2 ? (x === "Positive" ? "up" : "down") : ""}>{x}</td>)}</tr>)}</tbody></table></div>
            </section>

            <section className="panel ingest-panel">
              <div className="panel-head"><div className="panel-title">Vision Ingestion</div><div className="panel-meta">VIDEO → FACTORS</div></div>
              <div className="upload"><input ref={inputRef} hidden type="file" accept="video/*" onChange={e => analyze(e.target.files?.[0])}/><div className="drop" onClick={() => inputRef.current?.click()}><div><UploadCloud/><strong>{busy ? "Processing video..." : "Upload economic activity footage"}</strong><span>Roads, ports, stores, sites or industrial video</span></div></div>{analysis && <div className="result"><strong>Analysis complete</strong><br/>{analysis.frames_processed?.toLocaleString()} frames sampled · {analysis.unique_tracks} unique tracks · Activity index {analysis.activity_index?.toFixed(1)}</div>}{error && <div className="result"><strong>Backend unavailable</strong><br/>{error}. The research dashboard remains available in demo mode.</div>}</div>
            </section>
          </div>
        </main>
      </div>
    </div>
  );
}
