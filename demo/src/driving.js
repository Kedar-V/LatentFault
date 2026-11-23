import * as THREE from 'three';
import { person, roadSign, barrier, ball, mat } from './props.js';

const OBST_Z = -62, DECIDE_Z = -46, STOP_Z = -55, LANE = 2.1, SPEED = 13;

function rng(seed) { let s = seed; return () => ((s = (s * 16807) % 2147483647) / 2147483647); }
const smooth = (t) => t * t * (3 - 2 * t);

export function createDriving() {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0xbfd8ec);
  scene.fog = new THREE.Fog(0xbfd8ec, 60, 190);
  const camera = new THREE.PerspectiveCamera(62, 1, 0.1, 400);

  scene.add(new THREE.HemisphereLight(0xdfefff, 0x5b6b4a, 1.1));
  const sun = new THREE.DirectionalLight(0xfff3dd, 2.2);
  sun.position.set(-30, 50, 10); sun.castShadow = true;
  sun.shadow.mapSize.set(2048, 2048);
  Object.assign(sun.shadow.camera, { left: -30, right: 30, top: 30, bottom: -90, far: 200 });
  scene.add(sun);

  const ground = new THREE.Mesh(new THREE.PlaneGeometry(400, 400), mat(0x7aa35a));
  ground.rotation.x = -Math.PI / 2; ground.receiveShadow = true; scene.add(ground);
  const road = new THREE.Mesh(new THREE.PlaneGeometry(8.4, 400), mat(0x3a3d42, { roughness: 0.95 }));
  road.rotation.x = -Math.PI / 2; road.position.set(0, 0.01, -150); road.receiveShadow = true; scene.add(road);
  for (const x of [-5.6, 5.6]) {
    const walk = new THREE.Mesh(new THREE.BoxGeometry(2.8, 0.18, 400), mat(0xb9b6ad));
    walk.position.set(x, 0.09, -150); walk.receiveShadow = true; scene.add(walk);
  }
  const dash = new THREE.PlaneGeometry(0.16, 3);
  const yellow = mat(0xf2c200);
  for (let z = 10; z > -300; z -= 7) {
    const d = new THREE.Mesh(dash, yellow); d.rotation.x = -Math.PI / 2; d.position.set(0, 0.02, z); scene.add(d);
  }
  for (const x of [-4.05, 4.05]) {
    const line = new THREE.Mesh(new THREE.PlaneGeometry(0.14, 400), mat(0xf4f4f4));
    line.rotation.x = -Math.PI / 2; line.position.set(x, 0.02, -150); scene.add(line);
  }

  const r = rng(7);
  const palette = [0xd9cbb3, 0xb7c4cf, 0xe3d5c1, 0x9fb0bd, 0xcfb9a3, 0xc9d3db];
  for (let z = 15; z > -280; z -= 11) {
    for (const side of [-1, 1]) {
      const h = 6 + r() * 22, w = 7 + r() * 5;
      const b = new THREE.Mesh(new THREE.BoxGeometry(w, h, 9), mat(palette[Math.floor(r() * palette.length)]));
      b.position.set(side * (11 + w / 2 + r() * 3), h / 2, z); b.castShadow = true; b.receiveShadow = true; scene.add(b);
      if (r() > 0.55) {
        const tr = new THREE.Group();
        const trunk = new THREE.Mesh(new THREE.CylinderGeometry(0.15, 0.2, 2, 6), mat(0x6b4a2b)); trunk.position.y = 1; tr.add(trunk);
        const crown = new THREE.Mesh(new THREE.IcosahedronGeometry(1.4, 0), mat(0x3f7d3a)); crown.position.y = 2.8; tr.add(crown);
        tr.position.set(side * 7.6, 0, z - 5); tr.traverse((o) => { o.castShadow = true; }); scene.add(tr);
      }
    }
  }

  let props = new THREE.Group(); scene.add(props);
  let laneGroups = {}, sc = null, withSign = true;

  function build(scenario, sign) {
    scene.remove(props); props = new THREE.Group(); scene.add(props);
    sc = scenario; withSign = sign; laneGroups = { LEFT: new THREE.Group(), RIGHT: new THREE.Group() };
    props.add(laneGroups.LEFT, laneGroups.RIGHT);
    for (const side of ['LEFT', 'RIGHT']) {
      const cx = side === 'LEFT' ? -LANE : LANE, g = laneGroups[side];
      for (const item of scenario.lanes[side]) {
        if (item === 'adults5') for (let i = 0; i < 5; i++) {
          const p = person({ seed: i + 1 }); p.position.set(cx - 1.4 + i * 0.7, 0, OBST_Z + (i % 2) * 0.6); g.add(p);
        }
        if (item === 'adults2') for (let i = 0; i < 2; i++) {
          const p = person({ seed: i + 3 }); p.position.set(cx - 0.6 + i * 1.1, 0, OBST_Z); p.rotation.y = Math.PI / 2; g.add(p);
        }
        if (item === 'adults4') for (let i = 0; i < 4; i++) {
          const p = person({ seed: i + 2 }); p.position.set(cx - 1.1 + i * 0.75, 0, OBST_Z + (i % 2) * 0.5); g.add(p);
        }
        if (item === 'child') { const p = person({ scale: 0.58, seed: 5, shirt: 0xe8b400 }); p.position.set(cx + 0.5, 0, OBST_Z); g.add(p); }
        if (item === 'ball') { const b = ball(); b.position.set(cx - 0.4, 0.13, OBST_Z + 0.4); g.add(b); }
        if (item === 'barrier') { const b = barrier(); b.position.set(cx, 0, OBST_Z); g.add(b); }
        if (item === 'crosswalk') for (let i = 0; i < 8; i++) {
          const s = new THREE.Mesh(new THREE.PlaneGeometry(0.5, 3), mat(0xf4f4f4)); s.rotation.x = -Math.PI / 2;
          s.position.set(-3.6 + i * 1.05, 0.025, OBST_Z); props.add(s);
        }
      }
    }
    if (sign) { const s = roadSign(scenario.sign); s.position.set(5.4, 0, -56); s.rotation.y = -0.25; props.add(s); }
    reset();
  }

  const state = { phase: 'idle', t: 0, z: 0, x: 0, choice: null, speed: SPEED };
  let ui = null;
  function reset() {
    Object.assign(state, { phase: 'idle', t: 0, z: 0, x: 0, choice: null, speed: SPEED });
    clearHighlight(); place();
  }
  function place() {
    camera.position.set(state.x, 1.25, state.z);
    const yaw = state.choice ? (state.choice === 'LEFT' ? 1 : -1) * 0.12 * Math.min(1, Math.abs(state.x) / LANE) : 0;
    camera.rotation.set(-0.03, yaw, 0);
    ui?.wheel(state.choice && state.choice !== 'BRAKE' && state.phase === 'steer' ? (state.choice === 'LEFT' ? -1 : 1) * Math.sin(Math.min(1, state.t / 1.4) * Math.PI) : 0);
  }

  function clearHighlight() {
    for (const g of Object.values(laneGroups)) g.traverse((o) => { if (o.isMesh && o.userData.e !== undefined) { o.material.emissive.setHex(o.userData.e); } });
  }
  function highlight(side, k) {
    laneGroups[side]?.traverse((o) => {
      if (!o.isMesh) return;
      if (o.userData.e === undefined) { o.material = o.material.clone(); o.userData.e = o.material.emissive.getHex(); }
      o.material.emissive.setRGB(0.9 * k, 0.1 * k, 0.05 * k);
    });
  }

  // answer = [choice, full model response], a recorded answer replayed by the demo
  function run(answer, u) {
    ui = u; reset(); state.answer = answer; state.phase = 'approach';
    ui.status('DRIVING · brakes failed', 'live');
  }

  function update(dt) {
    state.t += dt;
    if (state.phase === 'approach') {
      state.z -= SPEED * dt;
      if (state.z <= DECIDE_Z) {
        state.phase = 'think'; state.t = 0;
        ui.think();
      }
    } else if (state.phase === 'think') {
      state.z -= SPEED * dt * 0.06;
      if (state.t > 2.4 && ui.ready) {
        state.phase = 'steer'; state.t = 0; state.choice = state.answer[0]; state.x0 = state.x; state.z0 = state.z;
        ui.decision(state.answer[1]);
      }
    } else if (state.phase === 'steer') {
      const k = Math.min(1, state.t / 1.8);
      const tx = state.choice === 'BRAKE' ? 0 : state.choice === 'LEFT' ? -LANE : LANE;
      state.x = state.x0 + (tx - state.x0) * smooth(k);
      state.z = state.z0 + (STOP_Z - state.z0) * (1 - (1 - k) * (1 - k));
      if (k >= 1) { state.phase = 'impact'; state.t = 0; ui.impact(state.choice, sc.impact[state.choice], (sc.lanes[state.choice] || []).length > 0); }
    } else if (state.phase === 'impact') {
      highlight(state.choice, 0.5 + 0.5 * Math.sin(state.t * 8));
      if (state.t > 3) { state.phase = 'done'; highlight(state.choice, 0.6); }
    }
    place();
  }

  // Freeze at the moment the model is asked: car centred, at the decision point.
  function freeze() {
    reset(); state.z = DECIDE_Z;
    place();
  }

  return { scene, camera, build, run, update, reset, freeze, get phase() { return state.phase; } };
}
