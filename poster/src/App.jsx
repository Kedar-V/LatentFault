import React, { useEffect, useLayoutEffect, useRef, useState } from 'react';
import QRCode from 'qrcode';
import { toPng } from 'html-to-image';
import Poster from './Poster.jsx';
import { EditProvider, useEditState, storeEdits } from './editable.jsx';
import { REPO_URL, DEFAULT_COLS, POSTER } from './config.js';

const W = POSTER.widthIn * POSTER.dpi;
const H = POSTER.heightIn * POSTER.dpi;
const PRINT = new URLSearchParams(location.search).has('print');
const COLS_KEY = 'poster-cols-v1';

function loadCols() {
  try { const c = JSON.parse(localStorage.getItem(COLS_KEY)); if (Array.isArray(c) && c.length === 3) return c; } catch { /* ignore */ }
  return DEFAULT_COLS;
}

export default function App() {
  const [edits, setEdits] = useEditState();
  const [edit, setEdit] = useState(false);
  const [cols, setCols] = useState(loadCols);
  const [qr, setQr] = useState(null);
  const [zoom, setZoom] = useState(null); // null = fit
  const [fit, setFit] = useState(0.3);
  const [busy, setBusy] = useState('');
  const stage = useRef(null);

  useEffect(() => { if (REPO_URL) QRCode.toDataURL(REPO_URL, { margin: 0, width: 600, color: { dark: '#0B1F3A' } }).then(setQr); }, []);
  useEffect(() => { try { localStorage.setItem(COLS_KEY, JSON.stringify(cols)); } catch { /* ignore */ } }, [cols]);
  useLayoutEffect(() => {
    if (PRINT) return undefined;
    const f = () => {
      const el = stage.current; if (!el) return;
      setFit(Math.min((el.clientWidth - 48) / W, (el.clientHeight - 48) / H));
    };
    f(); window.addEventListener('resize', f);
    return () => window.removeEventListener('resize', f);
  }, []);

  const body = <EditProvider edit={edit} edits={edits} setEdits={setEdits}><Poster cols={cols.map((c) => `${c}fr`)} qr={qr} /></EditProvider>;
  if (PRINT) return <div className="print-root">{body}</div>;

  const scale = zoom ?? fit;
  const setCol = (i, v) => setCols((c) => { const n = [...c]; n[i] = Number(v); return n; });
  const exportPng = async () => {
    setBusy('Rendering PNG…'); setEdit(false);
    await new Promise((r) => setTimeout(r, 50));
    try {
      const url = await toPng(document.getElementById('poster'), { width: W, height: H, pixelRatio: 2, style: { transform: 'none' } });
      const a = document.createElement('a'); a.href = url; a.download = 'poster.png'; a.click();
    } finally { setBusy(''); }
  };
  const exportJson = () => {
    const a = document.createElement('a');
    a.href = URL.createObjectURL(new Blob([JSON.stringify({ edits, cols }, null, 1)], { type: 'application/json' }));
    a.download = 'poster-edits.json'; a.click();
  };
  const importJson = (file) => file.text().then((t) => {
    const j = JSON.parse(t); if (j.edits) { setEdits(j.edits); storeEdits(j.edits); } if (j.cols) setCols(j.cols);
  });

  return (
    <div className="app">
      <div className="toolbar">
        <strong>Poster · 36 × 24 in</strong>
        <span className="tb-group">
          <button onClick={() => setZoom(Math.max(0.05, scale / 1.25))}>−</button>
          <span className="tb-zoom">{Math.round(scale * 100)}%</span>
          <button onClick={() => setZoom(Math.min(2, scale * 1.25))}>+</button>
          <button className={zoom == null ? 'on' : ''} onClick={() => setZoom(null)}>Fit</button>
          <button onClick={() => setZoom(1)} title="1 CSS px = 1/96 in: true print size on a 96-dpi screen">Print size</button>
        </span>
        <span className="tb-group">
          <button className={edit ? 'on' : ''} onClick={() => setEdit((e) => !e)}>{edit ? 'Editing text' : 'Edit text'}</button>
          <button onClick={() => { if (confirm('Discard all text edits?')) { setEdits({}); storeEdits({}); } }}>Reset text</button>
          <button onClick={exportJson}>Save edits</button>
          <label className="tb-file">Load edits<input type="file" accept="application/json" onChange={(e) => e.target.files[0] && importJson(e.target.files[0])} /></label>
        </span>
        <span className="tb-group tb-cols">
          Columns
          {['L', 'C', 'R'].map((n, i) => (
            <label key={n}>{n}<input type="range" min="18" max="50" value={cols[i]} onChange={(e) => setCol(i, e.target.value)} /></label>
          ))}
          <button onClick={() => setCols(DEFAULT_COLS)}>Reset</button>
        </span>
        <span className="tb-group">
          <button onClick={() => { setEdit(false); setTimeout(() => window.print(), 50); }}>Export PDF</button>
          <button onClick={exportPng}>Export PNG</button>
        </span>
        {busy && <span className="tb-busy">{busy}</span>}
      </div>
      <div className="stage" ref={stage}>
        <div className="sizer" style={{ width: W * scale, height: H * scale }}>
          <div className="scaler" style={{ transform: `scale(${scale})` }}>{body}</div>
        </div>
      </div>
    </div>
  );
}
