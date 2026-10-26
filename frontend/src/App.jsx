import { useEffect, useState, useRef } from 'react';
import { Activity, ArrowDownToLine, Circle, Cpu, Radio, RotateCcw, Wifi, Waves, Volume2, VolumeX } from 'lucide-react';
import { useRadarWebSocket } from './hooks/useRadarWebSocket';
import { LinksPanel, SpectralPanel, EventsJournal, AlertsToggle, WaterfallPanel } from './components/EnvironmentPanels';
import './App.css';

const labels = {
  waiting: 'Awaiting Sensor',
  calibrating: 'Calibrating Room Baseline...',
  quiet: 'Signal Stable (Calm)',
  signal_change: '⚠️ MOTION DETECTED!',
  motion_candidate: '⚠️ MOTION DETECTED!',
  disconnected: 'Sensor Disconnected',
  stale: 'Sensor Data Stale',
  offline: 'Server Offline'
};
const base = import.meta.env.VITE_API_URL || '';

function playBeep() {
  try {
    const AudioCtx = window.AudioContext || window.webkitAudioContext;
    if (!AudioCtx) return;
    const ctx = new AudioCtx();
    const osc = ctx.createOscillator();
    const gain = ctx.createGain();
    osc.type = 'sine';
    osc.frequency.setValueAtTime(880, ctx.currentTime);
    osc.frequency.exponentialRampToValueAtTime(1320, ctx.currentTime + 0.12);
    gain.gain.setValueAtTime(0.3, ctx.currentTime);
    gain.gain.exponentialRampToValueAtTime(0.01, ctx.currentTime + 0.28);
    osc.connect(gain);
    gain.connect(ctx.destination);
    osc.start();
    osc.stop(ctx.currentTime + 0.3);
  } catch { /* AudioContext might need user gesture first */ }
}

function Trace({ history, field, min, max, label, unit }) {
  const first = history[0]?.at ?? 0;
  const span = Math.max(10000, (history.at(-1)?.at ?? first) - first);
  const points = history.map(p => `${((p.at - first) / span) * 800},${110 - Math.max(0, Math.min(1, (p[field] - min) / (max - min))) * 90}`).join(' ');
  return <div className="trace">
    <div className="trace-heading"><h3>{label}</h3><span>{min} to {max} {unit}</span></div>
    <svg viewBox="0 0 800 130" role="img" aria-label={`${label} over the last ${Math.round(span / 1000)} seconds`} preserveAspectRatio="none">
      {[20, 50, 80, 110].map(y => <line key={y} x1="0" x2="800" y1={y} y2={y} className="chart-grid" />)}
      {points && <polyline points={points} fill="none" className={`trace-line ${field}`} strokeWidth="2" vectorEffect="non-scaling-stroke" />}
    </svg>
    <div className="trace-foot"><span>{history.length ? new Date(first).toLocaleTimeString() : 'Waiting for measurements'}</span><span>NOW</span></div>
  </div>;
}

export default function App() {
  const { data, history, events, connection } = useRadarWebSocket();
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState('');
  const [sessions, setSessions] = useState([]);
  const [audioMuted, setAudioMuted] = useState(false);
  const lastBeepRef = useRef(0);

  const available = data.system_status === 'ok';
  const isCsi = data.source === 'esp32_csi' || data.source === 'csi_simulation';
  const sourceName = data.is_simulation ? (data.source === 'csi_simulation' ? 'Synthetic CSI demo' : 'Synthetic demo')
    : isCsi ? 'ESP32 · CSI' : 'Laptop · RSSI';
  const title = labels[data.state] || 'Awaiting Sensor';

  useEffect(() => {
    if (data.motion_detected && !audioMuted) {
      const now = Date.now();
      if (now - lastBeepRef.current > 1400) {
        playBeep();
        lastBeepRef.current = now;
      }
    }
  }, [data.motion_detected, audioMuted]);

  const loadSessions = async () => {
    try {
      const response = await fetch(`${base}/sessions`);
      if (response.ok) setSessions(await response.json());
    } catch { /* Current sensor status carries connection failures. */ }
  };
  useEffect(() => {
    let active = true;
    fetch(`${base}/sessions`).then(response => response.ok ? response.json() : [])
      .then(rows => { if (active) setSessions(rows); }).catch(() => {});
    return () => { active = false; };
  }, [data.recording]);
  const action = async (path, options) => {
    setBusy(true);
    setNotice('');
    try {
      const response = await fetch(`${base}${path}`, { method: 'POST', ...(options || {}) });
      const result = await response.json();
      if (!response.ok) throw new Error(result.detail || 'Request failed');
      setNotice(result.message);
      await loadSessions();
    } catch (error) { setNotice(error.message); }
    finally { setBusy(false); }
  };
  const toggleAlerts = () => action('/api/alerts', {
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ enabled: !data.alerts_enabled }),
  });

  return <div className="workspace">
    <aside className="sidebar">
      <div className="workspace-label">SENSING WORKSPACE <span>06</span></div>
      <div className="nav-active"><Radio size={18} /> Live monitor <span className="live-dot" /></div>
      <div className="sidebar-section"><p className="eyebrow">CONNECTED SOURCE</p><div className="source-icon"><Wifi size={22} /></div>
        <h3>{sourceName}</h3><p className="muted">{data.adapter || 'Connecting to your receiver…'}</p>
        <dl className="source-details"><div><dt>Network</dt><dd>{data.ssid || (isCsi ? 'CSI receiver' : '—')}</dd></div>
          <div><dt>Channel</dt><dd>{data.channel ?? '—'}</dd></div><div><dt>Transport</dt><dd>{connection}</dd></div></dl>
      </div>
      <div className="sidebar-section capability-list"><p className="eyebrow">MEASUREMENT CAPABILITIES</p>
        <div><span className="cap-dot enabled" /> Live signal strength</div>
        <div><span className={`cap-dot ${isCsi ? 'enabled' : ''}`} /> CSI amplitude {isCsi ? 'connected' : 'requires receiver'}</div>
        <div><span className="cap-dot enabled" /> RF Path-Loss Distance ({data.estimated_distance_m != null ? `~${data.estimated_distance_m}m` : 'active'})</div>
        <div><span className="cap-dot enabled" /> Fresnel Proximity ({data.proximity_level || 'Calm'})</div>
        <p className="muted small">Calibrated multi-link RF perturbation.</p>
      </div>
      <div className="sidebar-bottom"><span className="tiny-square" /> LOCAL-FIRST SENSING<span>v6.0</span></div>
    </aside>

    <main className="main-content">
      <header className="topbar"><div><p className="eyebrow">WORKSPACE / LIVE MONITOR</p><h1>Read the room.</h1><p className="subtitle">Live Wi-Fi measurements. A clearer view of signal changes.</p></div>
        <div className={`source-badge ${data.is_simulation ? 'demo' : available ? 'online' : ''}`}><span className="live-dot" />{data.is_simulation ? 'SIMULATED DATA' : available ? 'LIVE HARDWARE' : 'AWAITING SENSOR'}</div>
      </header>

      {data.motion_detected && (
        <div className="motion-alert-banner" role="alert">
          <span className="alert-badge">🚨 DETECTED</span>
          <strong>Wi-Fi Fresnel Line Anomaly / Motion Detected!</strong>
          <span>{data.proximity_level || 'Line Perturbation'} · Deviation: {Math.round(data.change_score)}% · Estimated Tx-Rx Distance: {data.estimated_distance_m != null ? `${data.estimated_distance_m} m` : '—'}</span>
        </div>
      )}

      <section className="metric-grid" aria-label="Live measurements">
        <article className="metric"><div><span>RECEIVED SIGNAL</span><Wifi size={16} /></div><strong>{data.rssi_dbm == null ? '—' : data.rssi_dbm.toFixed(1)}<small>dBm</small></strong><p>Receiver RSSI level</p></article>
        <article className="metric"><div><span>CHANGE SCORE</span><Activity size={16} /></div><strong>{available ? Math.round(data.change_score) : '—'}<small>/ 100</small></strong><p>{data.motion_detected ? '🚨 MOTION DETECTED' : 'Baseline deviation'}</p></article>
        <article className="metric"><div><span>TX-RX DISTANCE</span><Radio size={16} /></div><strong>{available && data.estimated_distance_m != null ? data.estimated_distance_m : '—'}<small>m</small></strong><p>Path-Loss RF estimated distance</p></article>
        <article className="metric"><div><span>FRESNEL PERTURBATION</span><Activity size={16} /></div><strong>{available && data.fresnel_perturbation_pct != null ? `${Math.round(data.fresnel_perturbation_pct)}%` : '—'}</strong><p>{data.proximity_level || 'Calm line'}</p></article>
        <article className="metric"><div><span>READ RATE</span><Cpu size={16} /></div><strong>{available ? data.read_rate_hz.toFixed(1) : '—'}<small>Hz</small></strong><p>{isCsi ? 'Received CSI frames' : 'Driver reads · update rate'}</p></article>
        <article className="metric"><div><span>DATA AGE</span><Radio size={16} /></div><strong>{data.sample_age_ms == null || connection === 'offline' ? '—' : data.sample_age_ms}<small>ms</small></strong><p>{available ? 'Sensor stream is current' : 'Waiting for measurements'}</p></article>
      </section>

      <div className="monitor-grid">
        <section className="panel field-panel"><div className="panel-heading"><div><p className="eyebrow">SIGNAL FIELD</p><h2>Environmental activity</h2></div><span className="tag">{isCsi ? 'CSI AMPLITUDE' : 'RSSI MONITOR'}</span></div>
          <div className={`field ${available ? 'running' : ''} ${data.motion_detected ? 'changed' : ''}`} aria-label="Signal activity illustration; no measured positions">
            <div className="field-grid" /><div className="ring ring-one" /><div className="ring ring-two" /><div className="ring ring-three" />
            <div className="field-cross horizontal" /><div className="field-cross vertical" /><div className="sweep" />
            <span className="field-label top">SIGNAL ENVIRONMENT</span><span className="field-label bottom">ACTIVITY VIEW · NO POSITION DATA</span>
            <div className="receiver"><Waves size={35} /><span>RECEIVER</span></div>
          </div>
          <div className="field-caption"><span className={`live-dot ${available ? '' : 'inactive'}`} />{data.is_simulation ? 'Demo visualization using synthetic measurements' : 'Activity illustration driven by live measurements'}<span>NO TARGETS INFERRED</span></div>
        </section>

        <section className="panel detection-panel"><p className="eyebrow">DETECTION STATE</p><div className={`state-symbol ${data.motion_detected ? 'changed' : ''}`}><Activity size={27} /></div>
          <h2 aria-live="polite">{title}</h2><p className="state-description">{data.error || (data.state === 'calibrating' ? 'Keep the room quiet and your laptop and router stationary while the baseline is learned.' : data.motion_detected ? (isCsi ? 'Channel changes may indicate movement. Human presence has not been verified.' : 'The Wi-Fi link changed. Movement, interference, or receiver changes can cause this.') : available ? 'Monitoring changes relative to your quiet-room baseline. A stable signal does not prove the room is empty.' : 'Connect your Wi-Fi adapter or configured CSI receiver to resume live monitoring.')}</p>
          <div className="meter-label"><span>{data.state === 'calibrating' ? 'Calibration' : 'Signal change score'}</span><strong>{data.state === 'calibrating' ? `${Math.round(data.learning_progress * 100)}%` : `${Math.round(data.change_score)} / 100`}</strong></div>
          <div className="meter"><div style={{ width: `${data.state === 'calibrating' ? data.learning_progress * 100 : data.change_score}%` }} /></div>
          <div className="detection-buttons">
            <button className="button calibrate" disabled={busy || !available} onClick={() => action('/api/calibrate')}><RotateCcw size={15} /> Calibrate quiet room</button>
            <button className={`button sound-toggle ${audioMuted ? 'muted' : 'active'}`} onClick={() => { setAudioMuted(!audioMuted); if (audioMuted) playBeep(); }} title="Toggle audio alert">
              {audioMuted ? <VolumeX size={15} /> : <Volume2 size={15} />} {audioMuted ? 'Audio Muted' : 'Audio Alert On'}
            </button>
            <AlertsToggle enabled={data.alerts_enabled} busy={busy} onToggle={() => toggleAlerts()} />
          </div>
          <div className="unavailable-metrics">
            <div><span>DISTANCE</span><strong>{data.estimated_distance_m != null ? `${data.estimated_distance_m}m` : '—'}</strong></div>
            <div><span>FRESNEL</span><strong>{data.fresnel_perturbation_pct != null ? `${Math.round(data.fresnel_perturbation_pct)}%` : '—'}</strong></div>
            <div><span>EVENTS</span><strong>{data.event_count}</strong></div>
          </div>
          <p className="small muted">{isCsi ? 'CSI motion detection is experimental and needs testing in this room.' : 'Add an ESP32 CSI receiver for richer motion measurements.'}</p>
        </section>
      </div>

      <section className="panel telemetry-panel"><div className="panel-heading"><div><p className="eyebrow">LIVE TELEMETRY</p><h2>The signal, over time</h2></div><span className="legend"><span className="live-dot" /> RSSI <i /> Change score</span></div>
        <div className="charts"><Trace history={history} field="rssi" min={-100} max={-20} label="Signal strength" unit="dBm" /><Trace history={history} field="score" min={0} max={100} label="Baseline deviation" unit="" /></div>
      </section>

      {data.csi_preview && <WaterfallPanel data={data} />}

      <div className="environment-grid">
        <LinksPanel links={data.links} />
        <SpectralPanel spectral={data.spectral} />
        <EventsJournal base={base} />
      </div>

      <div className="bottom-grid"><section className="panel events-panel"><div className="panel-heading"><h2>Activity log</h2><span className="tag">THIS CONNECTION</span></div>
        {events.length ? <ul className="event-list">{events.map((event, i) => <li key={`${event.at}-${i}`}><span className="event-marker" /><span>{labels[event.state] || event.state}</span><time>{event.at}</time></li>)}</ul> : <p className="muted">Sensor transitions will appear here.</p>}
      </section><section className="panel sessions-panel"><div className="panel-heading"><h2>Recorded sessions</h2><button className={`button ${data.recording ? 'recording' : ''}`} disabled={busy || (!data.recording && !available)} onClick={() => action(data.recording ? '/session/stop' : '/session/start')}><Circle size={12} fill={data.recording ? 'currentColor' : 'none'} />{data.recording ? 'Stop recording' : 'Record session'}</button></div>
        {sessions.length ? <ul className="session-list">{sessions.slice(0, 4).map(session => <li key={session.id}><div><strong>{session.name}</strong><span>{new Date(session.start_time).toLocaleString()}{data.session_id === session.id ? ' · Recording' : ''}</span></div><a href={`${base}/session/${session.id}/export`} aria-label={`Export ${session.name}`} title="Export CSV"><ArrowDownToLine size={17} /></a></li>)}</ul> : <p className="muted">Record live measurements to compare a quiet room with a walk-through. Export sessions as CSV.</p>}
        {data.recording_error && <p className="error-text">Recording failed: {data.recording_error}</p>}
      </section></div>
      {notice && <div className="notice" role="status">{notice}<button aria-label="Dismiss message" onClick={() => setNotice('')}>×</button></div>}
      <footer className="page-footer">WiFi Sensing / Experimental environmental sensing<span>RSSI and untrained CSI do not identify humans or objects.</span></footer>
    </main>
  </div>;
}
