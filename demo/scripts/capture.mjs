// Renders every scenario at its decision moment and saves the frame shown to the model.
// Needs the dev server running (npm run dev). Writes public/frames/*.png (what the VLM sees).
// SCALE=2 renders the same view at 2x into recorded/frames_hires/ for the object detector.
import fs from 'node:fs';
import puppeteer from 'puppeteer-core';
import { DRIVING, CAMERA } from '../src/data.js';

const chrome = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const url = process.env.DEMO_URL || 'http://localhost:5190/';
const scale = Number(process.env.SCALE || 1);
const out = new URL(scale > 1 ? '../recorded/frames_hires/' : '../public/frames/', import.meta.url);
fs.mkdirSync(out, { recursive: true });

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--use-angle=metal', '--enable-gpu'] });
const page = await browser.newPage();
await page.setViewport({ width: 896, height: 504, deviceScaleFactor: scale });
await page.goto(url, { waitUntil: 'networkidle0' });

const shots = [
  ...DRIVING.flatMap((s) => [['driving', s.id, false], ['driving', s.id, true]]),
  ...CAMERA.map((c) => ['camera', c.id, false]),
];
const only = process.env.ONLY; // e.g. ONLY=cam_control renders just frames whose name starts with this
for (const [mode, id, sign] of shots) {
  const name = mode === 'driving' ? `drive_${id}_${sign ? 'sign' : 'nosign'}.png` : `cam_${id}.png`;
  if (only && !name.startsWith(only)) continue;
  const data = await page.evaluate((m, i, s) => window.__freeze(m, i, s), mode, id, sign);
  fs.writeFileSync(new URL(name, out), Buffer.from(data.split(',')[1], 'base64'));
  console.log('wrote', name);
}
await browser.close();
