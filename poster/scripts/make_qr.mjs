// Writes src/data/qr.svg (vector QR for the repo URL in src/config.js). Run: node scripts/make_qr.mjs
import QRCode from 'qrcode';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const cfg = fs.readFileSync(path.join(root, 'src', 'config.js'), 'utf8');
const url = cfg.match(/REPO_URL = '([^']*)'/)[1];
if (!url) throw new Error('REPO_URL is empty in src/config.js');
const svg = await QRCode.toString(url, { type: 'svg', margin: 0, errorCorrectionLevel: 'M', color: { dark: '#0B1F3A', light: '#00000000' } });
fs.writeFileSync(path.join(root, 'src', 'data', 'qr.svg'), svg);
console.log('wrote src/data/qr.svg for', url);
