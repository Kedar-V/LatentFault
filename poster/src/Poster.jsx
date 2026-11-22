import React from 'react';
import { E } from './editable.jsx';
import A3 from './data/act3d.json';
import { InterventionChart, ProjectionStrip, HeroFan, Activation2D, D, pct } from './charts.jsx';
import dahuaCommand from '../assets/dahua_command.jpg';
import dahuaForged from '../assets/dahua_forged.jpg';

const S = D.summary;
D.pair = { harmful: A3.points.find((p) => p.id === A3.highlight[0]).x, benign: A3.points.find((p) => p.id === A3.highlight[1]).x };
const A = D.ablate;
const rng = (rs) => { const v = rs.map((r) => Math.round(r.after * 100)); return `${Math.min(...v)}–${Math.max(...v)}%`; };

// Short reference list for print; the full list lives in the README.
export const REFERENCES = [
  'Arditi et al. (2024). Refusal in language models is mediated by a single direction. NeurIPS. arXiv:2406.11717',
  'Chao et al. (2024). JailbreakBench. NeurIPS Datasets & Benchmarks. arXiv:2404.01318',
  'Greshake et al. (2023). Indirect prompt injection in LLM-integrated applications. AISec. arXiv:2302.12173',
  'Bai et al. (2025). Qwen2.5-VL technical report. arXiv:2502.13923',
];

export default function Poster({ cols, qr }) {
  const cam = D.projection.filter((r) => r.scenario === 'camera');
  return (
    <div className="poster" id="poster" style={{ '--c1': cols[0], '--c2': cols[1], '--c3': cols[2] }}>
      <header className="hd">
        <div className="hd-top">
          <h1 className="title"><span className="t-a">Latent</span><span className="t-b">Fault</span></h1>
          <div className="byline">
            <E id="author" as="div" className="author">Kedar Vaidya</E>
            <E id="aff" as="div" className="aff">Duke University · AIPI 590 Responsible AI</E>
          </div>
        </div>
        <div className="hd-row">
          <div>
            <E id="title2" as="div" className="title2">One Direction, Two Failure Modes</E>
            <E id="subtitle" as="div" className="subtitle">Cross-Modal Refusal Representations and Physical Prompt Injection in Qwen2.5-VL</E>
            <E id="rq" as="p" className="rq">Does the same internal direction control refusal for text and images, and do physical prompt-injection attacks exploit it?</E>
            {qr ? <img className="qr" src={qr} alt="Repository QR code" /> : null}
          </div>
          <div>
            <div className="hero-fig"><HeroFan /></div>
            <E id="hero.cap" as="p" className="hero-cap">200 requests shown as images, each scored at every layer on the direction learned from typed text (held out, standardized per layer).</E>
          </div>
        </div>
      </header>

      <main className="cols">
        {/* 01 */}
        <section className="col col-1">
          <div className="kicker teal"><span className="kn">01</span>Discovering the direction</div>
          <E id="s1.h" as="h2">Text and images share one harm direction from layer 19 on</E>
          <E id="s1.p" as="p">100 harmful and 100 matched benign JailbreakBench requests, each typed and shown as an image. We read the model's hidden state at every layer.</E>
          <div className="fig act3d"><Activation2D /></div>
          <div className="qpair">
            <div className="q q-b"><div className="q-h">Benign query <b>−{Math.abs(D.pair.benign).toFixed(1)}</b></div><div className="q-t">A history of heroin use</div></div>
            <div className="q q-h-r"><div className="q-h">Harmful query <b>+{D.pair.harmful.toFixed(1)}</b></div><div className="q-t">Recommending heroin use</div></div>
          </div>
          <E id="s1.3d" as="p" className="cap">Layer 28; large dots are held out. Vertical: top PCA component ⊥ d₂₈.</E>
          <div className="formula">d<sub>l</sub> = normalize(μ<sub>harmful, l</sub> − μ<sub>benign, l</sub>)<span className="formula-n">residual stream, not an input embedding · 5-fold held out</span></div>
          <div className="hero hero-inline">
            <div className="hero-n teal">{S.transfer_auc.toFixed(3)}</div>
            <E id="s1.hero" as="div" className="hero-l">text-to-image AUROC at layer {S.layer}: learned from typed text, tested on images</E>
          </div>
          <E id="s1.cap" as="p" className="note">Transfer jumps {D.layers[18].transfer.toFixed(2)} → {D.layers[19].transfer.toFixed(2)} at layer 19 (top right); text and image directions align (cosine {S.cosine_text_image.toFixed(2)}).</E>
        </section>

        {/* 02 */}
        <section className="col col-main">
          <div className="kicker coral"><span className="kn">02</span>Testing causality</div>
          <E id="s2.h" as="h2" className="h2-main">A single direction strongly influences refusal across modalities</E>
          <div className="hero-row">
            <div className="hero">
              <div className="hero-n coral">{pct(A.text.harm.before)} → {pct(A.text.harm.after)}</div>
              <div className="hero-l">refusals of harmful <b>typed</b> requests</div>
            </div>
            <div className="hero">
              <div className="hero-n coral">{pct(A.image.harm.before)} → {pct(A.image.harm.after)}</div>
              <div className="hero-l">refusals of harmful <b>image</b> requests</div>
            </div>
          </div>
          <div className="fig"><InterventionChart dark /></div>
          <E id="s2.cav" as="p" className="caveat">Refusal = refusal language in the first 40 generated tokens. 0% does not mean the outputs were harmful; we did not grade them. n = 100 per row, band = 95% CI.</E>
          <E id="s2.ctl" as="p" className="note">Random directions of the same size: {rng(A.text.random.concat(A.image.random))} after removal, {Math.round(D.add.text.random.after * 100)}–{pct(D.add.image.random.after)} after addition. A separate refusal direction (⊥ harm) matters less: {pct(A.text.refusal_orth.after)} text, {pct(A.image.refusal_orth.after)} image after removal.</E>
        </section>

        {/* 03 */}
        <section className="col col-3">
          <div className="kicker coral"><span className="kn">03</span>Testing physical attacks</div>
          <E id="s3.h" as="h2">A forged answer suppressed the alarm in our prototype</E>
          <E id="s3.p" as="p">Qwen2.5-VL-3B watches the footage with one rule: alert if a person is visible. The attacker controls only the sign.</E>
          <div className="feeds">
            {[[dahuaCommand, 'Sign shows a command', 'ALERT', false], [dahuaForged, 'Sign shows a forged answer', 'NO ALERT', true]].map(([src, label, dec, hit]) => (
              <figure key={label} className="feed">
                <div className={`feed-l${hit ? ' hit' : ''}`}>{label}</div>
                <div className="feed-img">
                  <img src={src} alt={`${label}; model decision ${dec}`} />
                  <span className="rec" />
                  <span className={`pill-ov${hit ? ' hit' : ''}`}>{dec}</span>
                </div>
              </figure>
            ))}
          </div>
          <E id="s3.f" as="h3">The attack that worked did not look less harmful</E>
          <div className="fig"><ProjectionStrip /></div>
        </section>
      </main>

      <footer className="ft">
        <E id="ft.take" as="p" className="take">A shared harm direction strongly influences refusal for text and images, but the visual attack that worked did not act through it. Monitoring refusal activations is not enough to secure a vision-language system.</E>
        <div className="ft-col">
          <E id="ft.lim.h" as="div" className="ft-h">Limitations</E>
          <E id="ft.lim" as="ul">
            <li>One model: Qwen2.5-VL-3B</li>
            <li>Refusal judged from 40-token replies</li>
            <li>Physical tests: single exploratory trials</li>
          </E>
        </div>
        <div className="ft-col refs">
          <E id="ft.refs.h" as="div" className="ft-h">References</E>
          <ol>{REFERENCES.map((r, i) => <E key={i} id={`ref.${i}`} as="li">{r}</E>)}</ol>
        </div>
      </footer>
    </div>
  );
}
