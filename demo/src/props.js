import * as THREE from 'three';

const mat = (color, opts = {}) => new THREE.MeshStandardMaterial({ color, roughness: 0.8, ...opts });
const SKIN = [0xf1c27d, 0xc68642, 0x8d5524, 0xe0ac69, 0xffdbac];
const SHIRT = [0x2a6fdb, 0xd2483c, 0x2e9e6a, 0xe8b400, 0x7a4fd1, 0x0b7f8a, 0xf08a24];

export function person({ scale = 1, shirt, skin, pants = 0x2b3445, seed = 0 } = {}) {
  const g = new THREE.Group();
  const s = mat(skin ?? SKIN[seed % SKIN.length]);
  const sh = mat(shirt ?? SHIRT[seed % SHIRT.length]);
  const pa = mat(pants);
  const legGeo = new THREE.BoxGeometry(0.16, 0.8, 0.18);
  for (const x of [-0.11, 0.11]) {
    const leg = new THREE.Mesh(legGeo, pa); leg.position.set(x, 0.4, 0); g.add(leg);
  }
  const torso = new THREE.Mesh(new THREE.CapsuleGeometry(0.22, 0.45, 4, 10), sh);
  torso.position.y = 1.12; g.add(torso);
  const armGeo = new THREE.CapsuleGeometry(0.06, 0.5, 4, 8);
  for (const x of [-0.3, 0.3]) {
    const arm = new THREE.Mesh(armGeo, sh); arm.position.set(x, 1.1, 0); arm.name = x < 0 ? 'armL' : 'armR'; g.add(arm);
  }
  const head = new THREE.Mesh(new THREE.SphereGeometry(0.16, 16, 12), s);
  head.position.y = 1.62; g.add(head);
  g.scale.setScalar(scale);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return g;
}

export function textTexture(lines, { style = 'plain', w = 512, h = 384 } = {}) {
  const c = document.createElement('canvas'); c.width = w; c.height = h;
  const x = c.getContext('2d');
  const bg = style === 'road' ? '#f2c200' : '#f4f1ea';
  const fg = '#141414';
  x.fillStyle = bg; x.fillRect(0, 0, w, h);
  if (style === 'road') { x.lineWidth = 14; x.strokeStyle = '#141414'; x.strokeRect(10, 10, w - 20, h - 20); }
  const mono = style === 'mono';
  const n = lines.length;
  let size = Math.min(110, (h * 0.8) / n / 1.15);
  const font = (sz) => `${mono ? '600' : '800'} ${sz}px ${mono ? 'Menlo, monospace' : 'Inter, Helvetica, Arial, sans-serif'}`;
  x.font = font(size);
  const widest = Math.max(...lines.map((l) => x.measureText(l).width));
  if (widest > w * 0.88) { size *= (w * 0.88) / widest; x.font = font(size); }
  x.fillStyle = fg; x.textAlign = 'center'; x.textBaseline = 'middle';
  const lh = size * 1.18, y0 = h / 2 - (lh * (n - 1)) / 2;
  lines.forEach((l, i) => x.fillText(l, w / 2, y0 + i * lh));
  const t = new THREE.CanvasTexture(c); t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8;
  return t;
}

export function roadSign(lines, style = 'road') {
  const g = new THREE.Group();
  const post = new THREE.Mesh(new THREE.CylinderGeometry(0.06, 0.06, 2.6, 8), mat(0x777f89, { metalness: 0.6 }));
  post.position.y = 1.3; g.add(post);
  const board = new THREE.Mesh(new THREE.BoxGeometry(2.2, 1.5, 0.06), [mat(0x333), mat(0x333), mat(0x333), mat(0x333),
    new THREE.MeshStandardMaterial({ map: textTexture(lines, { style }), roughness: 0.6 }), mat(0x555)]);
  board.position.y = 3.2; g.add(board);
  g.traverse((o) => { if (o.isMesh) o.castShadow = true; });
  return g;
}

export function handSign(lines, style = 'plain') {
  const geo = new THREE.BoxGeometry(0.62, 0.46, 0.02);
  const face = new THREE.MeshStandardMaterial({ map: textTexture(lines, { style, w: 512, h: 380 }), roughness: 0.7 });
  const edge = mat(0xdedad0);
  return new THREE.Mesh(geo, [edge, edge, edge, edge, face, edge]);
}

export function barrier() {
  const g = new THREE.Group();
  const geo = new THREE.BoxGeometry(1.0, 0.9, 0.5);
  for (let i = 0; i < 3; i++) {
    const b = new THREE.Mesh(geo, mat(i % 2 ? 0xd2483c : 0xf0f0f0)); b.position.set(-1 + i, 0.45, 0); b.castShadow = true; g.add(b);
  }
  return g;
}

export function ball() {
  const m = new THREE.Mesh(new THREE.SphereGeometry(0.13, 16, 12), mat(0xff5a1f, { roughness: 0.5 }));
  m.position.y = 0.13; m.castShadow = true; return m;
}

export { mat };
