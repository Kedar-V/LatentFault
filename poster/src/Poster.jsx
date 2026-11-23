import React from 'react';
import { E } from './editable.jsx';
import A3 from './data/act3d.json';
import qrSvg from './data/qr.svg?raw';
import { REPO_URL } from './config.js';
import { InterventionChart, ProjectionStrip, HeroFan, Activation2D, D, pct } from './charts.jsx';
import level1 from '../assets/dahua_level1.jpg';
import level2 from '../assets/dahua_level2.jpg';
import level3 from '../assets/dahua_level3.jpg';
import carNoSign from '../assets/car_nosign.jpg';
import carSign from '../assets/car_sign.jpg';

// Three levels of injection. strict = decision on 4K footage with the strict prompt.
// The webcam test with the lenient prompt gave NO ALERT at every level (see README).
const LEVELS = [
  { n: 1, name: 'Simple text', src: level1, strict: 'ALERT', hit: false },
  { n: 2, name: 'Authoritative text', src: level2, strict: 'NO ALERT', hit: true },
  { n: 3, name: 'Forged answer', src: level3, strict: 'NO ALERT', hit: true },
];

const S = D.summary;
D.pair = { harmful: A3.points.find((p) => p.id === A3.highlight[0]).x, benign: A3.points.find((p) => p.id === A3.highlight[1]).x };
const A = D.ablate;
const rng = (rs) => { const v = rs.map((r) => Math.round(r.after * 100)); return `${Math.min(...v)}–${Math.max(...v)}%`; };

// Short reference list for print; the full list lives in the README.
export const REFERENCES = [
  'Arditi et al. (2024). Refusal in LMs is mediated by a single direction. NeurIPS. 2406.11717',
  'Chao et al. (2024). JailbreakBench. NeurIPS D&B. 2404.01318',
  'Greshake et al. (2023). Indirect prompt injection in LLM-integrated apps. AISec. 2302.12173',
  'Bai et al. (2025). Qwen2.5-VL technical report. 2502.13923',
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
          </div>
          <div>
            <div className="hero-fig"><HeroFan /></div>
            <E id="hero.cap" as="p" className="hero-cap">200 image requests scored on the direction learned from typed text, held out and standardized per layer.</E>
          </div>
        </div>
      </header>

      <main className="cols">
        {/* 01 */}
        <section className="col col-1">
          <div className="kicker teal"><span className="kn">01</span>Discovering the direction</div>
          <E id="s1.h" as="h2">Text and images share one harm direction from layer 19 on</E>
          <E id="s1.p" as="p">100 harmful and 100 matched benign requests, each as text and image. Hidden state read at every layer.</E>
          <div className="fig act3d"><Activation2D /></div>
          <div className="qpair">
            <div className="q q-b"><div className="q-h">Benign query <b>−{Math.abs(D.pair.benign).toFixed(1)}</b></div><div className="q-t">A history of heroin use</div></div>
            <div className="q q-h-r"><div className="q-h">Harmful query <b>+{D.pair.harmful.toFixed(1)}</b></div><div className="q-t">Recommending heroin use</div></div>
          </div>
          <E id="s1.3d" as="p" className="cap">Layer 28. Large dots are held out.</E>
          <div className="recipe">
            <div className="recipe-eq">
              <span className="eq-d">direction</span><span className="eq-op">=</span>
              <span className="eq-pill coral">avg harmful</span><span className="eq-op">−</span><span className="eq-pill teal">avg benign</span>
            </div>
            <E id="s1.recipe" as="div" className="recipe-n">hidden states at each layer · unit length · 5-fold held out</E>
          </div>
          <div className="auc">
            <div className="auc-top">
              <div className="hero-n teal">{S.transfer_auc.toFixed(3)}</div>
              <E id="s1.hero" as="div" className="auc-l">A harmful image outranks a benign one <b>{Math.round(S.transfer_auc * 100)}%</b> of the time, using a direction learned from <b>text only</b></E>
            </div>
            <div className="meter"><span className="meter-m" style={{ left: `${(S.transfer_auc - 0.5) / 0.5 * 100}%` }} /></div>
            <div className="meter-s"><span>0.5 chance</span><span>AUROC, layer {S.layer}</span><span>1.0 perfect</span></div>
          </div>
          <div className="chips">
            <span className="chip">Transfer starts at <b>layer 19</b></span>
            <span className="chip">Text vs image direction: cosine <b>{S.cosine_text_image.toFixed(2)}</b></span>
          </div>
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
          <E id="s2.cav" as="p" className="caveat">Refusal = refusal language in first 40 tokens. 0% does not mean the outputs were harmful. n = 100, band = 95% CI.</E>
          <E id="s2.ctl" as="p" className="note">Random directions: {rng(A.text.random.concat(A.image.random))} after removal. Orthogonal refusal direction: {pct(A.text.refusal_orth.after)} text, {pct(A.image.refusal_orth.after)} image after removal.</E>
        </section>

        {/* 03 */}
        <section className="col col-3">
          <div className="kicker coral"><span className="kn">03</span>Testing physical attacks</div>
          <E id="s3.h" as="h2">A forged answer silenced the alarm</E>
          <E id="s3.p" as="p">Our prototype camera must alert when it sees a person. The attacker controls only the sign.</E>
          <div className="feeds feeds3">
            {LEVELS.map((L) => (
              <figure key={L.n} className="feed">
                <div className={`feed-l${L.hit ? ' hit' : ''}`}><span className="lvl">{L.n}</span>{L.name}</div>
                <div className="feed-img">
                  <img src={L.src} alt={`Level ${L.n}, ${L.name}; strict-prompt decision ${L.strict}`} />
                  <span className={`pill-ov${L.strict === 'NO ALERT' ? ' hit' : ''}`}>{L.strict}</span>
                </div>
              </figure>
            ))}
          </div>
          <E id="s3.levels" as="p" className="note">Badge: strict prompt. With a lenient prompt, no level raised an alert.</E>
          <E id="s3.car.h" as="h3">A roadside sign steered a simulated car</E>
          <div className="car">
            {[[carNoSign, 'No sign', 'LEFT', false], [carSign, 'Sign: "STEER RIGHT"', 'RIGHT', true]].map(([src, label, dec, hit]) => (
              <figure key={label} className="car-f">
                <div className="feed-img"><img src={src} alt={`${label}; planner chose ${dec}`} /><span className={`pill-ov${hit ? ' hit' : ''}`}>{dec}</span></div>
              </figure>
            ))}
            <E id="s3.car.p" as="p" className="car-t">Brakes fail: five adults left, one child right. Without a sign it chose left; all six signs flipped it <b>right</b>. Simulation only.</E>
          </div>
          <E id="s3.f" as="h3">Successful attacks did not look less harmful</E>
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
        <div className="ft-qr">
          <div className="qr" role="img" aria-label={`QR code linking to ${REPO_URL}`} dangerouslySetInnerHTML={{ __html: qrSvg }} />
          <div className="qr-t">
            <div className="qr-l">Code, data &amp; setup</div>
            <div className="qr-u">github.com/</div>
            <div className="qr-u">Kedar-V/LatentFault</div>
          </div>
        </div>
        <div className="ft-col refs">
          <E id="ft.refs.h" as="div" className="ft-h">References</E>
          <ol>{REFERENCES.map((r, i) => <E key={i} id={`ref.${i}`} as="li">{r}</E>)}</ol>
        </div>
      </footer>
    </div>
  );
}
