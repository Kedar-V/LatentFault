import React from 'react';
import D from './data/poster_data.json';

// Every chart reads poster_data.json (built by scripts/build_data.py from the result files).
// Style: one saturated accent per figure, comparisons in grey, direct labels instead of legends.
export const C = {
  navy: '#0B1F3A',
  ink: '#25324A',
  muted: '#5B677A',
  faint: '#8E9AAB',
  grid: '#E7EBF0',
  teal: '#0A8A96',
  tealSoft: '#EEF6F7',
  coral: '#E2493A',
  coralSoft: '#F7D3CE',
  grey: '#A9B4C2',
  greyDark: '#6F7C8F',
};

const lin = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0)) * (r1 - r0);
export const pct = (v) => `${Math.round(v * 100)}%`;
const path = (pts) => pts.map(([x, y], i) => `${i ? 'L' : 'M'}${x.toFixed(1)},${y.toFixed(1)}`).join('');
const st = (fill) => ({ fill });

// Figure 1: held-out AUROC by layer. Focus: text -> image transfer (teal); the rest in grey.
export function AurocChart({ w = 940, h = 362 }) {
  const m = { l: 74, r: 18, t: 50, b: 70 };
  const x = lin(0, 36, m.l, w - m.r);
  const y = lin(0.4, 1.0, h - m.b, m.t);
  const L = D.layers;
  const sel = D.summary.layer;
  const line = (key) => path(L.map((r) => [x(r.layer), y(r[key])]));
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="Held-out AUROC by layer: text to image transfer rises sharply at layer 19">
      <rect x={x(19)} y={m.t} width={x(36) - x(19)} height={h - m.b - m.t} fill={C.teal} fillOpacity={0.09} />
      <text x={m.l - 10} y={24} className="ax-title">Held-out AUROC</text>
      {[0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0].map((t) => (
        <g key={t}>
          <line x1={m.l} x2={w - m.r} y1={y(t)} y2={y(t)} stroke={t === 0.5 ? C.grey : C.grid} strokeWidth={t === 0.5 ? 2 : 1.5} />
          <text x={m.l - 14} y={y(t) + 8} textAnchor="end" className="tick">{t.toFixed(1)}</text>
        </g>
      ))}
      {[0, 6, 12, 18, 24, 30, 36].map((t) => (
        <text key={t} x={x(t)} y={h - m.b + 34} textAnchor="middle" className="tick">{t}</text>
      ))}
      <text x={w - m.r} y={h - 8} textAnchor="end" className="ax-title">Layer</text>
      <path d={line('null95')} fill="none" stroke={C.grey} strokeWidth={3} strokeDasharray="9 8" />
      <path d={line('image')} fill="none" stroke={C.grey} strokeWidth={3.5} />
      <path d={line('text')} fill="none" stroke={C.greyDark} strokeWidth={3.5} />
      <path d={line('transfer')} fill="none" stroke={C.teal} strokeWidth={8} strokeLinejoin="round" strokeLinecap="round" />
      <text x={x(1)} y={y(0.815)} className="lab" style={st(C.greyDark)}>text → text</text>
      <text x={x(13)} y={y(0.70)} textAnchor="middle" className="lab" style={st(C.greyDark)}>image → image</text>
      <text x={x(18.4)} y={y(0.915)} textAnchor="end" className="lab-b" style={st(C.teal)}>text → image</text>
      <text x={x(31)} y={y(0.535)} textAnchor="middle" className="lab" style={st(C.greyDark)}>shuffled labels</text>
      <text x={x(19.6)} y={y(0.785)} className="lab" style={st(C.teal)}>
        {L[18].transfer.toFixed(2)} → {L[19].transfer.toFixed(2)} at layer 19
      </text>
      <circle cx={x(sel)} cy={y(L[sel].transfer)} r={10} fill={C.teal} stroke="#fff" strokeWidth={4} />
      <text x={x(sel)} y={y(L[sel].transfer) - 22} textAnchor="middle" className="lab-s" style={st(C.teal)}>layer {sel}</text>
    </svg>
  );
}

// Figure 2: refusal rate before -> after editing the direction, on a full 0-100% axis.
export function InterventionChart({ w = 1180, h = 610, dark = false }) {
  const K = dark ? { grid: '#22385A', base: '#B9C7D8', baseFill: '#0B1F3A', accent: '#FF7E68', band: 'rgba(255,126,104,0.28)' } : { grid: C.grid, base: C.greyDark, baseFill: '#fff', accent: C.coral, band: C.coralSoft };
  const m = { l: 250, r: 40 };
  const x = lin(0, 1, m.l, w - m.r);
  const A = D.ablate, ADD = D.add;
  const groups = [
    { title: 'Remove the direction', sub: 'harmful requests · layers 19–36', y0: 34, rows: [
      { label: 'Typed text', r: A.text.harm, rand: A.text.random.map((q) => q.after), randLabel: true },
      { label: 'Image', r: A.image.harm, rand: A.image.random.map((q) => q.after) },
    ] },
    { title: 'Add the direction', sub: 'benign requests · layer 20', y0: 306, rows: [
      { label: 'Typed text', r: ADD.text.harm, rand: [ADD.text.random.after], randLabel: true },
      { label: 'Image', r: ADD.image.harm, rand: [ADD.image.random.after] },
    ] },
  ];
  const axisY = h - 70;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="Refusal rates before and after removing or adding the harm direction">
      {[0, 0.25, 0.5, 0.75, 1].map((t) => (
        <g key={t}>
          <line x1={x(t)} x2={x(t)} y1={20} y2={axisY} stroke={K.grid} strokeWidth={1.5} />
          <text x={x(t)} y={axisY + 34} textAnchor="middle" className="tick">{pct(t)}</text>
        </g>
      ))}
      <text x={w - m.r} y={h - 4} textAnchor="end" className="ax-title">Replies with refusal language</text>
      {groups.map((g) => (
        <g key={g.title}>
          <text x={0} y={g.y0 + 10} className="grp">{g.title}</text>
          <text x={0} y={g.y0 + 44} className="grp-s">{g.sub}</text>
          {g.rows.map((row, i) => {
            const yc = g.y0 + 110 + i * 96;
            const { before, after, ci } = row.r;
            const up = after > before;
            return (
              <g key={row.label}>
                <text x={m.l - 30} y={yc + 9} textAnchor="end" className="row">{row.label}</text>
                <line x1={x(0)} x2={x(1)} y1={yc} y2={yc} stroke={K.grid} strokeWidth={2} />
                <rect x={x(ci[0])} y={yc - 12} width={Math.max(4, x(ci[1]) - x(ci[0]))} height={24} rx={12} fill={K.band} />
                {/* arrow runs from the edge of the baseline dot to the edge of the result dot */}
                {(() => {
                  const dir = up ? 1 : -1, tip = x(after) - dir * 23, start = x(before) + dir * 22;
                  return (
                    <g>
                      <line x1={start} x2={tip - dir * 22} y1={yc} y2={yc} stroke={K.accent} strokeWidth={7} />
                      <path d={`M${tip},${yc} l${-dir * 26},-14 l0,28 z`} fill={K.accent} />
                    </g>
                  );
                })()}
                <circle cx={x(before)} cy={yc} r={17} fill={K.baseFill} stroke={K.base} strokeWidth={6} />
                <circle cx={x(after)} cy={yc} r={19} fill={K.accent} />
                <text x={x(before)} y={yc - 30} textAnchor="middle" className="val" style={st(K.base)}>{pct(before)}</text>
                <text x={x(after)} y={yc - 30} textAnchor="middle" className="val-b" style={st(K.accent)}>{pct(after)}</text>
              </g>
            );
          })}
        </g>
      ))}
    </svg>
  );
}

// Figure 4: how strongly each input activates the harm direction (mean projection, layers 19-36).
// One row per comparison, value printed on each dot. Typed requests are shown only for scale.
export function ProjectionStrip({ w = 1000, h = 392 }) {
  const m = { l: 430, r: 70 };
  const x = lin(0, 60, m.l, w - m.r);
  const rows = D.projection;
  const get = (role) => rows.find((r) => r.role === role).harm_proj;
  const cam = rows.filter((r) => r.scenario === 'camera');
  const others = cam.filter((r) => r.role !== 'attack-schema-mimic' && r.role !== 'control-person').map((r) => r.harm_proj);
  const lo = Math.min(...others), hi = Math.max(...others);
  const dah = (k) => D.dahua.find((r) => r.image.includes(k));
  const R = [
    { label: 'Context: typed harmful (avg)', v: get('reference-harmful'), col: C.grey, fill: C.grey, ctx: true },
    { label: 'Context: typed benign (avg)', v: get('reference-benign'), col: C.grey, fill: '#fff', ctx: true },
    { g: true },
    { label: 'Webcam: no phone', v: get('control-person'), col: C.greyDark, fill: '#fff', note: 'ALERT' },
    { label: `Webcam: ${others.length} other texts`, range: [lo, hi], col: C.greyDark, note: 'all ALERT' },
    { label: 'Webcam: forged answer', v: get('attack-schema-mimic'), col: C.coral, fill: C.coral, note: 'NO ALERT', bold: true },
    { g: true },
    { label: 'Dahua: command sign', v: dah('command').harm_proj, col: C.greyDark, fill: '#fff', note: 'ALERT' },
    { label: 'Dahua: forged sign', v: dah('forged').harm_proj, col: C.coral, fill: C.coral, note: 'NO ALERT', bold: true },
  ];
  let yy = 0;
  const pos = R.map((r) => { yy += r.g ? 28 : 35; return yy; });
  const axisY = yy + 26;
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="Harm-direction activation: harmful typed requests 57.7, benign 14.4, camera frames 1.4 to 3.4; the forged answer that fooled the camera is 3.4">
      {[0, 20, 40, 60].map((t) => (
        <g key={t}>
          <line x1={x(t)} x2={x(t)} y1={pos[0] - 22} y2={axisY} stroke={C.grid} strokeWidth={1.5} />
          <text x={x(t)} y={axisY + 30} textAnchor="middle" className="tick">{t}</text>
        </g>
      ))}
      <text x={w - m.r} y={axisY + 64} textAnchor="end" className="ax-title">harm-direction activation, layers 19–36 (higher = more harmful-looking)</text>
      {R.map((r, i) => {
        const y = pos[i];
        if (r.g) return <line key={i} x1={0} x2={w} y1={y - 6} y2={y - 6} stroke={C.grey} strokeWidth={1.5} strokeDasharray="4 6" />;
        return (
          <g key={i}>
            <text x={m.l - 24} y={y + 9} textAnchor="end" className="row" style={{ fill: r.bold ? C.coral : r.ctx ? C.greyDark : C.navy, fontWeight: r.bold ? 800 : r.ctx ? 400 : 600 }}>{r.label}</text>
            <line x1={x(0)} x2={x(60)} y1={y} y2={y} stroke={C.grid} strokeWidth={1.5} />
            {r.range
              ? <rect x={x(r.range[0])} y={y - 8} width={Math.max(6, x(r.range[1]) - x(r.range[0]))} height={16} rx={8} fill={C.grey} />
              : <circle cx={x(r.v)} cy={y} r={r.bold ? 13 : 11} fill={r.fill} stroke={r.col} strokeWidth={4} />}
            <text x={(r.range ? x(r.range[1]) : x(r.v)) + 22} y={y + 9} className="val-b" style={{ fill: r.col }}>
              {r.range ? `${r.range[0].toFixed(1)}–${r.range[1].toFixed(1)}` : r.v.toFixed(1)}
            </text>
            {r.note && <text x={(r.range ? x(r.range[1]) : x(r.v)) + (r.range ? 150 : 90)} y={y + 9} className="lab" style={{ fill: r.bold ? C.coral : C.greyDark, fontWeight: r.bold ? 700 : 400 }}>{r.note}</text>}
          </g>
        );
      })}
    </svg>
  );
}

export { D };

// Hero: every image request's held-out score on the text-learned direction, layer by layer.
// Lines start mixed and split into two bands after layer 19. Scores standardized per layer.
export function HeroFan({ w = 1600, h = 330 }) {
  const m = { l: 10, r: 230, t: 24, b: 54 };
  const x = lin(0, 36, m.l, w - m.r);
  const y = lin(-2.7, 2.7, h - m.b, m.t);
  const F = D.fan;
  const lines = F.scores.map((s, i) => ({ d: path(s.map((v, L) => [x(L), y(v)])), harm: F.harmful[i] }));
  const mean = (k) => Array.from({ length: 37 }, (_, L) => {
    const v = F.scores.filter((_, i) => F.harmful[i] === k).map((s) => s[L]);
    return v.reduce((a, b) => a + b, 0) / v.length;
  });
  const mh = mean(1), mb = mean(0);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="200 image requests scored on the direction learned from typed text, by layer: harmful and benign split after layer 19">
      <rect x={x(19)} y={m.t - 10} width={x(36) - x(19)} height={h - m.b - m.t + 20} fill="#F2F8F8" />
      <line x1={x(19)} x2={x(19)} y1={m.t - 10} y2={h - m.b + 10} stroke={C.teal} strokeWidth={2.5} strokeDasharray="8 7" />
      <text x={x(19) + 12} y={h - m.b + 40} className="lab-s" style={st(C.teal)}>layer 19</text>
      <text x={x(0)} y={h - m.b + 40} className="lab-s">layer 0</text>
      <text x={x(36)} y={h - m.b + 40} textAnchor="end" className="lab-s">36</text>
      {lines.filter((l) => !l.harm).map((l, i) => <path key={`b${i}`} d={l.d} fill="none" stroke={C.teal} strokeOpacity={0.22} strokeWidth={2} />)}
      {lines.filter((l) => l.harm).map((l, i) => <path key={`h${i}`} d={l.d} fill="none" stroke={C.coral} strokeOpacity={0.22} strokeWidth={2} />)}
      <path d={path(mb.map((v, L) => [x(L), y(v)]))} fill="none" stroke={C.teal} strokeWidth={6} />
      <path d={path(mh.map((v, L) => [x(L), y(v)]))} fill="none" stroke={C.coral} strokeWidth={6} />
      <text x={x(36) + 18} y={y(mh[36]) + 9} className="lab-b" style={st(C.coral)}>harmful</text>
      <text x={x(36) + 18} y={y(mb[36]) + 9} className="lab-b" style={st(C.teal)}>benign</text>
    </svg>
  );
}

// 3D view at layer 28: axis 1 is the learned direction d28 (real projection, fold-0 training mean as origin);
// axes 2-3 are PCA of the remainder, fit on training items. Coordinates from refusal-xmodal
// src/plot_query_direction_3d.py (activations recomputed on the Orin). Drawn with a fixed orthographic camera.
import A3 from './data/act3d.json';

export function Activation3D({ w = 900, h = 510 }) {
  const P = A3.points;
  const ext = (k) => [Math.min(...P.map((p) => p[k])), Math.max(...P.map((p) => p[k]))];
  const [x0, x1] = ext('x'), [y0, y1] = ext('y'), [z0, z1] = ext('z');
  const nx = (v) => ((v - x0) / (x1 - x0)) * 2 - 1;
  const ny = (v) => ((v - y0) / (y1 - y0)) * 2 - 1;
  const nz = (v) => ((v - z0) / (z1 - z0)) * 2 - 1;
  const box = [1.75, 0.9, 0.85]; // stretch the direction axis
  const az = (-28 * Math.PI) / 180, el = (20 * Math.PI) / 180;
  const S = 176, cx = w / 2 - 4, cy = h / 2 - 54;
  const proj = (u, v, t) => {
    const U = u * box[0], V = v * box[1], W = t * box[2];
    const sx = U * Math.cos(az) - V * Math.sin(az);
    const depth = U * Math.sin(az) + V * Math.cos(az);
    const sy = W * Math.cos(el) + depth * Math.sin(el);
    return [cx + sx * S, cy - sy * S, depth];
  };
  const pt = (p) => proj(nx(p.x), ny(p.y), nz(p.z));
  const L = (a, b, props) => <line x1={a[0]} y1={a[1]} x2={b[0]} y2={b[1]} {...props} />;
  const floor = [[-1, -1], [1, -1], [1, 1], [-1, 1]].map(([u, v]) => proj(u, v, -1));
  const hi = P.find((p) => p.id === A3.highlight[0]), bi = P.find((p) => p.id === A3.highlight[1]);
  const sorted = [...P].sort((a, b) => pt(b)[2] - pt(a)[2]);
  const axisA = proj(-1.04, -1, -1), axisB = proj(1.08, -1, -1);
  const ticks = [-30, -20, -10, 0, 10, 20, 30, 40].filter((t) => t >= x0 && t <= x1);
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="3D view: requests separate along the learned harm direction; orthogonal PCA axes add spread but not separation">
      <polygon points={floor.map((q) => q.slice(0, 2).join(',')).join(' ')} fill={C.navy} fillOpacity={0.035} stroke={C.grid} strokeWidth={1.5} />
      {[-0.5, 0, 0.5].map((v) => L(proj(-1, v, -1), proj(1, v, -1), { key: `g${v}`, stroke: C.grid, strokeWidth: 1.2 }))}
      {L(proj(-1, 1, -1), proj(-1, 1, 1), { stroke: C.grid, strokeWidth: 1.5 })}
      {L(proj(1, 1, -1), proj(1, 1, 1), { stroke: C.grid, strokeWidth: 1.5 })}
      {L(proj(-1, 1, 1), proj(1, 1, 1), { stroke: C.grid, strokeWidth: 1.5 })}
      {sorted.map((p) => {
        if (p === hi || p === bi) return null;
        const [sx, sy] = pt(p);
        return <circle key={p.id} cx={sx} cy={sy} r={p.heldout ? 6 : 4} fill={p.harmful ? C.coral : C.teal} fillOpacity={p.heldout ? 0.6 : 0.2} />;
      })}
      <line x1={axisA[0]} y1={axisA[1]} x2={axisB[0]} y2={axisB[1]} stroke={C.navy} strokeWidth={4} />
      <path d={`M${axisB[0]},${axisB[1]} l-18,-10 l2,16 z`} fill={C.navy} transform={`rotate(${(Math.atan2(axisB[1] - axisA[1], axisB[0] - axisA[0]) * 180) / Math.PI} ${axisB[0]} ${axisB[1]})`} />
      {ticks.map((t) => {
        const q = proj(nx(t), -1, -1);
        return <text key={t} x={q[0]} y={q[1] + 34} textAnchor="middle" className="tick">{t}</text>;
      })}
      {[[bi, C.teal], [hi, C.coral]].map(([p, col]) => {
        const a = pt(p), f = proj(nx(p.x), -1, -1);
        return (
          <g key={p.id}>
            <line x1={a[0]} y1={a[1]} x2={f[0]} y2={f[1]} stroke={col} strokeWidth={3} strokeDasharray="8 7" />
            <path d={`M${f[0]},${f[1] - 10} l10,10 l-10,10 l-10,-10 z`} fill={col} />
            <circle cx={a[0]} cy={a[1]} r={15} fill={col} stroke="#fff" strokeWidth={4} />
            <text x={f[0] + 16} y={f[1] - 14} className="lab-b" style={{ fill: col }}>{p.x > 0 ? '+' : ''}{p.x.toFixed(1)}</text>
            <text x={a[0] + 22} y={a[1] - 14} className="lab-b" style={{ fill: col }}>{p.harmful ? 'harmful' : 'benign'}</text>
          </g>
        );
      })}
      <text x={axisA[0]} y={axisB[1] + 48} className="ax-title" style={{ fill: C.navy }}>learned harm direction d₂₈ →</text>
      <text x={proj(1, 1, 1)[0] + 12} y={proj(1, 1, 1)[1] + 8} className="lab-s">PC2 ⊥ d</text>
      <text x={proj(1, 1, -1)[0] + 12} y={proj(1, 1, -1)[1] + 8} className="lab-s">PC1 ⊥ d</text>
    </svg>
  );
}

// 2D view at layer 28: x = projection onto d28 (real, fold-0 training mean as origin),
// y = leading principal component of the remainder (orthogonal to d28), fit on training items.
// The dashed drops are exact: each point's x is its projection score.
export function Activation2D({ w = 900, h = 420 }) {
  const P = A3.points;
  const m = { l: 20, r: 20, t: 26, b: 96 };
  const xs = P.map((p) => p.x), ys = P.map((p) => p.y);
  const x = lin(Math.min(...xs) - 4, Math.max(...xs) + 4, m.l, w - m.r);
  const y = lin(Math.min(...ys) - 4, Math.max(...ys) + 4, h - m.b, m.t);
  const axisY = h - m.b + 26;
  const hi = P.find((p) => p.id === A3.highlight[0]), bi = P.find((p) => p.id === A3.highlight[1]);
  const ticks = [-30, -20, -10, 0, 10, 20, 30, 40];
  return (
    <svg viewBox={`0 0 ${w} ${h}`} width="100%" role="img" aria-label="Held-out requests at layer 28: horizontal position is the projection onto the learned harm direction; harmful requests sit to the right">
      {P.filter((p) => p !== hi && p !== bi).map((p) => (
        <circle key={p.id} cx={x(p.x)} cy={y(p.y)} r={p.heldout ? 7 : 4.5} fill={p.harmful ? C.coral : C.teal} fillOpacity={p.heldout ? 0.55 : 0.18} />
      ))}
      <line x1={m.l} x2={w - m.r - 6} y1={axisY} y2={axisY} stroke={C.navy} strokeWidth={4} />
      <path d={`M${w - m.r},${axisY} l-20,-11 l0,22 z`} fill={C.navy} />
      {ticks.map((t) => <text key={t} x={x(t)} y={axisY + 34} textAnchor="middle" className="tick">{t}</text>)}
      <text x={m.l} y={axisY + 66} className="ax-title" style={{ fill: C.navy }}>projection onto the learned harm direction d₂₈ →</text>
      {[[bi, C.teal, 'benign query', 'a history of heroin use', -1], [hi, C.coral, 'harmful query', 'recommending heroin use', 1]].map(([p, col, tag, desc, side]) => {
        const px = x(p.x), py = y(p.y), anchor = side > 0 ? 'end' : 'start', dx = side > 0 ? -26 : 26;
        return (
          <g key={p.id}>
            <line x1={px} y1={py} x2={px} y2={axisY} stroke={col} strokeWidth={3} strokeDasharray="8 7" />
            <path d={`M${px},${axisY - 11} l11,11 l-11,11 l-11,-11 z`} fill={col} />
            <circle cx={px} cy={py} r={16} fill={col} stroke="#fff" strokeWidth={4} />
          </g>
        );
      })}
    </svg>
  );
}
