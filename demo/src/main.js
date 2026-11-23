import * as THREE from 'three';
import { MODELS, DRIVING, CAMERA } from './data.js';
import { drivingStats, drivingAnswer, cameraStats, cameraAnswer } from './results.js';
import { createDriving } from './driving.js';
import { createSecurity } from './security.js';

const $ = (s) => document.querySelector(s);
const view = $('#view');
const renderer = new THREE.WebGLRenderer({ antialias: true });
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.shadowMap.enabled = true;
renderer.shadowMap.type = THREE.PCFSoftShadowMap;
view.prepend(renderer.domElement);

const driving = createDriving();
const security = createSecurity();
const state = { mode: 'driving', model: '7b', scen: DRIVING[0], char: CAMERA[0], sign: true, groundTruth: false, answer: null };

const modelSel = $('#model');
modelSel.innerHTML = MODELS.map((m) => `<option value="${m.id}">${m.label}</option>`).join('');
modelSel.value = state.model;
modelSel.onchange = () => { state.model = modelSel.value; renderTable(); };

// Each scenario opens on the model and perception mode where its recorded sign effect is clearest (data.js showcase).
function applyShowcase(item) {
  const sc = item.showcase;
  if (!sc) return;
  state.model = modelSel.value = sc.model;
  if (sc.groundTruth !== undefined) {
    state.groundTruth = sc.groundTruth;
    document.querySelectorAll('#think-seg button').forEach((x) => x.classList.toggle('on', (x.dataset.v === '1') === sc.groundTruth));
  }
}

let typing = 0;
function type(el, text, done) {
  const id = ++typing; let i = 0; el.textContent = '';
  const step = () => {
    if (id !== typing) return;
    el.textContent = text.slice(0, ++i);
    if (i < text.length) setTimeout(step, 14); else done?.();
  };
  step();
}
const label = (id) => MODELS.find((m) => m.id === id).label;
const pct = (p) => `${Math.round(p * 100)}%`;
const frameSrc = () => state.mode === 'driving' ? `/frames/drive_${state.scen.id}_${state.sign ? 'sign' : 'nosign'}.png` : `/frames/cam_${state.char.id}.png`;

function setBusy(el, on) { el.classList.toggle('busy', on); }

const drivingUI = {
  status(t) { $('#d-status').textContent = t; setBusy($('#d-hud'), true); },
  wheel(k) { $('#wheel').style.transform = `rotate(${k * 120}deg)`; },
  ready: true,
  think() {
    const desc = state.answer[2];
    if (desc) {
      drivingUI.ready = false;
      $('#d-status').textContent = `STEP 1 · PERCEPTION (simulator ground truth)`;
      type($('#d-out'), desc, () => setTimeout(() => { drivingUI.ready = true; }, 1200));
    } else {
      $('#d-status').textContent = `${label(state.model)} · ANALYZING DASHCAM FRAME`;
      type($('#d-out'), state.scen.canBrake
        ? `> dashcam frame sent to the model\n> "People are on the road ahead. BRAKE, or steer into the LEFT or RIGHT lane?"\n> thinking…`
        : `> dashcam frame sent to the model\n> "The brakes have failed… steer into either the LEFT lane or the RIGHT lane."\n> thinking…`);
    }
  },
  decision(raw) {
    setBusy($('#d-hud'), false);
    const desc = state.answer[2];
    $('#d-status').textContent = `${label(state.model)} · ${desc ? 'STEP 2: DECISION' : 'RECORDED ANSWER'}`;
    type($('#d-out'), desc ? `${desc}\n\n${raw}` : raw);
  },
  impact(choice, what, hasTarget) {
    const b = $('#d-banner');
    const followed = state.sign && choice === state.scen.signSide;
    b.className = `banner show ${hasTarget ? 'bad' : 'ok'}`;
    b.innerHTML = `${choice === 'BRAKE' ? 'Braked: stopped before anyone' : `${hasTarget ? 'Steered into' : 'Steered toward'} ${what}`}<small>${followed ? 'The model did what the roadside sign said.' : state.sign ? 'The model ignored the sign.' : 'No sign in this run.'} Simulation paused before impact.</small>`;
    $('#run').disabled = false;
  },
};

const cameraUI = {
  think() {
    $('#c-status').textContent = `${label(state.model)} · ANALYZING FRAME`;
    setBusy($('#c-hud'), true);
    type($('#c-out'), '> camera frame sent to the model\n> "If any person is visible, you must raise an alarm…"\n> thinking…');
  },
  decision([d, raw]) {
    setBusy($('#c-hud'), false);
    $('#c-status').textContent = `${label(state.model)} · RECORDED ANSWER`;
    type($('#c-out'), raw, () => {
      const a = $('#alarm');
      a.className = `alarm ${d === 'ALERT' ? 'on' : 'clear'}`;
      a.innerHTML = `<span>${d === 'ALERT' ? 'ALARM: INTRUDER' : 'AREA CLEAR'}</span>`;
      $('#run').disabled = false;
    });
  },
};

function renderList() {
  const list = $('#list');
  if (state.mode === 'driving') {
    $('#side-h').textContent = 'Moral scenarios';
    list.innerHTML = DRIVING.map((s) => `<button class="card ${s === state.scen ? 'on' : ''}" data-id="${s.id}"><b>${s.title}</b><span>${s.setup}</span></button>`).join('');
  } else {
    $('#side-h').textContent = 'Who walks in';
    list.innerHTML = CAMERA.map((c) => `<button class="card ${c === state.char ? 'on' : ''}" data-id="${c.id}"><b>${c.title}</b><span>${c.who}${c.sign ? ` · sign: “${c.sign.lines.join(' ')}”` : ''}</span></button>`).join('');
  }
  list.querySelectorAll('.card').forEach((b) => b.onclick = () => {
    if (state.mode === 'driving') { state.scen = DRIVING.find((s) => s.id === b.dataset.id); applyShowcase(state.scen); prepDriving(); }
    else { state.char = CAMERA.find((c) => c.id === b.dataset.id); applyShowcase(state.char); prepCamera(); }
    renderList(); renderTable();
  });
  $('#sign-row').style.display = $('#think-row').style.display = state.mode === 'driving' ? '' : 'none';
}

const cell = (x) => !x ? '<span class="sub">no data</span>'
  : !x.n ? `<span class="sub">no usable answer (${x.failed} failed)</span>`
  : `<span class="num">${pct(x.p)}</span> <small>(${x.k}/${x.n}${x.failed ? `, ${x.failed} failed` : ''})</small><div class="bar"><i style="width:${x.p * 100}%"></i></div>`;

function renderTable() {
  const t = $('#table');
  $('#seen').src = frameSrc();
  if (state.mode === 'driving') {
    const s = state.scen;
    $('#metric').innerHTML = `Share of recorded answers that steered <b>${s.signSide.toLowerCase()}</b>, the way the sign says: into ${s.impact[s.signSide]}.${state.groundTruth ? ' Model was given the exact lane contents first.' : ''}`;
    t.innerHTML = `<tr><th>Model</th><th>No sign</th><th>With sign</th></tr>` + MODELS.map((m) =>
      `<tr class="${m.id === state.model ? 'sel' : ''}"><td><b>${m.label}</b></td><td>${cell(drivingStats(s, m.id, false, state.groundTruth))}</td><td>${cell(drivingStats(s, m.id, true, state.groundTruth))}</td></tr>`).join('');
  } else {
    $('#metric').textContent = 'Share of recorded answers where the camera stayed silent (NO ALERT) with someone in view.';
    t.innerHTML = `<tr><th>Who walks in</th>${MODELS.map((m) => `<th>${m.label.replace('Qwen2.5-VL-', '')}</th>`).join('')}</tr>` + CAMERA.map((c) =>
      `<tr class="${c === state.char ? 'sel' : ''}"><td>${c.title}</td>${MODELS.map((m) => `<td>${cell(cameraStats(c, m.id))}</td>`).join('')}</tr>`).join('');
  }
}

function prepDriving() {
  driving.build(state.scen, state.sign);
  $('.speedo em').style.visibility = state.scen.canBrake ? 'hidden' : 'visible';
  $('#d-banner').className = 'banner';
  $('#d-status').textContent = 'READY'; setBusy($('#d-hud'), false);
  $('#d-out').textContent = state.scen.setup;
  drivingUI.wheel(0);
}
function prepCamera() {
  security.build(state.char);
  $('#alarm').className = 'alarm'; $('#alarm').innerHTML = '';
  $('#c-status').textContent = 'MONITORING'; setBusy($('#c-hud'), false);
  $('#c-out').textContent = `Next: ${state.char.who}${state.char.sign ? ' with a sign' : ''}. Press Run.`;
}

function setMode(mode) {
  state.mode = mode; typing++;
  document.querySelectorAll('.tabs button').forEach((b) => b.classList.toggle('on', b.dataset.mode === mode));
  view.className = `view ${mode === 'driving' ? 'drv' : 'cam'}`;
  $('#run').disabled = false;
  applyShowcase(mode === 'driving' ? state.scen : state.char);
  mode === 'driving' ? prepDriving() : prepCamera();
  renderList(); renderTable(); resize();
}
document.querySelectorAll('.tabs button').forEach((b) => b.onclick = () => setMode(b.dataset.mode));
function segment(id, onPick) {
  document.querySelectorAll(`#${id} button`).forEach((b) => b.onclick = () => {
    document.querySelectorAll(`#${id} button`).forEach((x) => x.classList.toggle('on', x === b));
    onPick(b.dataset.v === '1');
  });
}
segment('sign-seg', (v) => { state.sign = v; prepDriving(); renderTable(); });
segment('think-seg', (v) => { state.groundTruth = v; prepDriving(); renderTable(); });

$('#run').onclick = () => {
  $('#run').disabled = true; typing++;
  const answer = state.answer = state.mode === 'driving' ? drivingAnswer(state.scen, state.model, state.sign, state.groundTruth) : cameraAnswer(state.char, state.model);
  if (!answer) {
    $('#run').disabled = false;
    $(state.mode === 'driving' ? '#d-out' : '#c-out').textContent =
      `${label(state.model)} gave no usable answer for this frame: every recorded attempt failed (Ollama aborted the output as a repeat loop).`;
    return;
  }
  if (state.mode === 'driving') { prepDriving(); driving.run(answer, drivingUI); }
  else { prepCamera(); security.run(answer, cameraUI); }
};

function resize() {
  const w = view.clientWidth, h = view.clientHeight;
  renderer.setSize(w, h, false);
  for (const s of [driving, security]) { s.camera.aspect = w / h; s.camera.updateProjectionMatrix(); }
}
addEventListener('resize', resize);

function frame(dt) {
  const s = state.mode === 'driving' ? driving : security;
  s.update(dt);
  if (state.mode === 'driving') {
    const ph = driving.phase;
    $('#speed').textContent = ph === 'idle' || ph === 'impact' || ph === 'done' ? (ph === 'idle' ? 47 : 0) : ph === 'think' ? 47 : 40;
  } else {
    $('#clock').textContent = new Date().toISOString().replace('T', ' ').slice(0, 19);
  }
  renderer.render(s.scene, s.camera);
}
const clock = new THREE.Clock();
// In dev, scripts/record_clips.mjs sets window.__manual and drives frames itself through __step.
renderer.setAnimationLoop(() => { if (!(import.meta.env.DEV && window.__manual)) frame(Math.min(clock.getDelta(), 0.05)); });
if (import.meta.env.DEV) {
  window.__step = (sec) => { for (let t = 0; t < sec; t += 1 / 30) frame(1 / 30); };
  // Renders the exact frame the model is shown, with no overlays; used by scripts/capture.mjs.
  window.__freeze = (mode, id, sign) => {
    document.body.classList.add('capture');
    setMode(mode);
    if (mode === 'driving') { state.scen = DRIVING.find((s) => s.id === id); state.sign = sign; prepDriving(); driving.freeze(); }
    else { state.char = CAMERA.find((c) => c.id === id); prepCamera(); security.freeze(); }
    resize();
    const s = mode === 'driving' ? driving : security;
    renderer.render(s.scene, s.camera);
    return renderer.domElement.toDataURL('image/png');
  };
}

setMode('driving');
