import * as THREE from 'three';
import { person, handSign, textTexture, mat } from './props.js';

const STOP_X = -0.2, START_X = -7;

export function createSecurity() {
  const scene = new THREE.Scene();
  scene.background = new THREE.Color(0x20262e);
  const camera = new THREE.PerspectiveCamera(55, 1, 0.1, 100);
  camera.position.set(2.0, 2.7, 3.4);
  camera.lookAt(-0.5, 1.05, -0.2);

  scene.add(new THREE.HemisphereLight(0xe8eef5, 0x3a3f46, 1.2));
  const key = new THREE.DirectionalLight(0xffffff, 1.6);
  key.position.set(4, 9, 5); key.castShadow = true; key.shadow.mapSize.set(1024, 1024);
  Object.assign(key.shadow.camera, { left: -10, right: 10, top: 10, bottom: -10 });
  scene.add(key);

  const tile = document.createElement('canvas'); tile.width = tile.height = 256;
  const tx = tile.getContext('2d'); tx.fillStyle = '#c9c4ba'; tx.fillRect(0, 0, 256, 256);
  tx.strokeStyle = '#a9a398'; tx.lineWidth = 4; tx.strokeRect(0, 0, 256, 256);
  const floorTex = new THREE.CanvasTexture(tile); floorTex.wrapS = floorTex.wrapT = THREE.RepeatWrapping; floorTex.repeat.set(10, 10);
  floorTex.colorSpace = THREE.SRGBColorSpace;
  const floor = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), new THREE.MeshStandardMaterial({ map: floorTex, roughness: 0.6 }));
  floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);

  const wallM = mat(0xe6e1d6);
  const back = new THREE.Mesh(new THREE.BoxGeometry(20, 4.5, 0.3), wallM); back.position.set(0, 2.25, -4); back.receiveShadow = true; scene.add(back);
  const left = new THREE.Mesh(new THREE.BoxGeometry(0.3, 4.5, 20), wallM); left.position.set(-8, 2.25, 0); left.receiveShadow = true; scene.add(left);
  const door = new THREE.Mesh(new THREE.BoxGeometry(1.6, 2.6, 0.1), mat(0x6d4f36)); door.position.set(-3.5, 1.3, -3.82); scene.add(door);
  const desk = new THREE.Mesh(new THREE.BoxGeometry(3, 1.1, 1), mat(0x3d4a5a)); desk.position.set(2.6, 0.55, -2.6); desk.castShadow = true; scene.add(desk);
  const logo = new THREE.Mesh(new THREE.PlaneGeometry(3, 0.7), new THREE.MeshBasicMaterial({ map: textTexture(['ACME LABS · LOBBY'], { w: 768, h: 180 }) }));
  logo.position.set(2.6, 3.1, -3.84); scene.add(logo);
  for (const x of [-5.5, 5.5]) {
    const plant = new THREE.Group();
    const pot = new THREE.Mesh(new THREE.CylinderGeometry(0.35, 0.28, 0.6, 12), mat(0x8a5a3c)); pot.position.y = 0.3; plant.add(pot);
    const leaves = new THREE.Mesh(new THREE.IcosahedronGeometry(0.6, 0), mat(0x3f7d3a)); leaves.position.y = 1.1; plant.add(leaves);
    plant.position.set(x, 0, -3.2); plant.traverse((o) => { o.castShadow = true; }); scene.add(plant);
  }

  let actor = null, cur = null;
  const st = { phase: 'idle', t: 0 };
  let ui = null;

  function build(c) {
    if (actor) scene.remove(actor);
    cur = c;
    actor = person({ seed: c.id.length });
    if (c.sign) {
      const s = handSign(c.sign.lines, c.sign.style); s.position.set(0, 1.18, 0.36); s.scale.setScalar(1.45); actor.add(s);
    }
    scene.add(actor); reset();
  }

  function reset() {
    Object.assign(st, { phase: 'idle', t: 0 });
    if (!actor) return;
    actor.position.set(START_X, 0, 0.6); actor.rotation.set(0, Math.PI / 2, 0);
    pose(0);
  }

  function pose(k) {
    for (const n of ['armL', 'armR']) {
      const a = actor.getObjectByName(n); if (a) { a.rotation.x = -1.1 * k; a.position.z = 0.18 * k; }
    }
  }

  // answer = [decision, full model response], a recorded answer replayed by the demo
  function run(answer, u) {
    ui = u; reset(); st.answer = answer; st.phase = 'walk';
  }

  function update(dt) {
    st.t += dt;
    if (!actor) return;
    if (st.phase === 'walk') {
      const k = Math.min(1, st.t / 3.2);
      actor.position.x = START_X + (STOP_X - START_X) * k;
      actor.position.y = Math.abs(Math.sin(st.t * 7)) * 0.05;
      pose(cur.sign ? 0.6 : 0);
      if (k >= 1) { st.phase = 'turn'; st.t = 0; }
    } else if (st.phase === 'turn') {
      const k = Math.min(1, st.t / 0.8);
      const target = Math.atan2(camera.position.x - actor.position.x, camera.position.z - actor.position.z);
      actor.rotation.y = Math.PI / 2 + (target - Math.PI / 2) * k;
      actor.position.y = 0;
      pose(cur.sign ? 0.6 + 0.4 * k : 0);
      if (k >= 1) { st.phase = 'hold'; st.t = 0; }
    } else if (st.phase === 'hold') {
      if (st.t > 0.7) { st.phase = 'think'; st.t = 0; ui.think(); }
    } else if (st.phase === 'think') {
      if (st.t > 1.8) { st.phase = 'done'; st.t = 0; ui.decision(st.answer); }
    }
  }

  // Freeze at the moment the model is asked: actor stopped, facing the camera, sign raised.
  function freeze() {
    reset();
    actor.position.set(STOP_X, 0, 0.6);
    actor.rotation.y = Math.atan2(camera.position.x - STOP_X, camera.position.z - 0.6);
    pose(cur.sign ? 1 : 0);
  }

  return { scene, camera, build, run, update, reset, freeze, get phase() { return st.phase; } };
}
