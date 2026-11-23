// Records one demo run per video beat into ../video/public/clips/*.mp4, frame by frame at exactly 30 fps.
// The page's timers run on a virtual clock and the 3D scene is stepped 1/30 s per frame, so playback is real speed
// however slowly headless Chrome renders. Needs the dev server and ffmpeg.
// Each clip replays a recorded answer from the model's most common decision; `prefer` picks which one by its text.
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { execFileSync } from 'node:child_process';
import puppeteer from 'puppeteer-core';

const chrome = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const url = process.env.DEMO_URL || 'http://localhost:5190/';
const out = new URL('../../video/public/clips/', import.meta.url).pathname;
const FPS = 30;
fs.mkdirSync(out, { recursive: true });

const CLIPS = [
  { name: 'empty_nosign', mode: 'driving', id: 'emptyright', model: '7b', sign: false, gt: false, prefer: 'therefore more dangerous', secs: 12 },
  { name: 'empty_sign', mode: 'driving', id: 'emptyright', model: '7b', sign: true, gt: false, prefer: 'people in the right lane', secs: 12 },
  { name: 'brake_nosign', mode: 'driving', id: 'brake', model: '7b', sign: false, gt: false, prefer: 'crossing the road in front of the vehicle', secs: 12 },
  { name: 'brake_sign', mode: 'driving', id: 'brake', model: '7b', sign: true, gt: false, prefer: 'no immediate obstacle in the right lane', secs: 12 },
  { name: 'cam_control', mode: 'camera', id: 'control', model: '7b', prefer: 'A person is visible', secs: 10 },
  { name: 'cam_forged', mode: 'camera', id: 'forged', model: '7b', prefer: 'The area is empty', secs: 10 },
  { name: 'cam_mannequin', mode: 'camera', id: 'mannequin', model: '7b', prefer: 'a mannequin, not a person', secs: 10 },
];
const only = process.argv.slice(2);

// Virtual clock: setTimeout callbacks fire only when __advance moves time forward.
const VIRTUAL_TIME = () => {
  window.__manual = true;
  const queue = [];
  let now = 0;
  window.setTimeout = (fn, ms = 0, ...args) => { queue.push({ t: now + ms, fn, args }); return queue.length; };
  window.__advance = (ms) => {
    const end = now + ms;
    for (;;) {
      queue.sort((a, b) => a.t - b.t);
      if (!queue.length || queue[0].t > end) break;
      const next = queue.shift(); now = next.t; next.fn(...next.args);
    }
    now = end;
  };
};

const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--use-angle=metal', '--enable-gpu'] });
for (const c of CLIPS.filter((c) => !only.length || only.includes(c.name))) {
  const page = await browser.newPage();
  await page.setViewport({ width: 1920, height: 1080 });
  await page.evaluateOnNewDocument(VIRTUAL_TIME);
  await page.goto(url, { waitUntil: 'networkidle0' });
  await page.evaluate((c) => {
    const q = (s) => document.querySelector(s);
    q(`[data-mode=${c.mode}]`).click();
    q(`[data-id=${c.id}]`).click();
    const m = q('#model'); m.value = c.model; m.dispatchEvent(new Event('change'));
    if (c.mode === 'driving') {
      q(`#sign-seg [data-v="${c.sign ? 1 : 0}"]`).click();
      q(`#think-seg [data-v="${c.gt ? 1 : 0}"]`).click();
    }
    window.__prefer = c.prefer;
    document.body.classList.add('record');
    window.dispatchEvent(new Event('resize'));
  }, c);
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), `clip-${c.name}-`));
  const total = c.secs * FPS, lead = Math.round(0.6 * FPS);
  for (let i = 0; i < total; i++) {
    if (i === lead) await page.evaluate(() => document.querySelector('#run').click());
    await page.evaluate((fps) => { window.__advance(1000 / fps); window.__step(1 / fps); }, FPS);
    await page.screenshot({ path: path.join(dir, `${String(i).padStart(4, '0')}.jpg`), type: 'jpeg', quality: 92 });
  }
  await page.close();
  execFileSync('ffmpeg', ['-y', '-loglevel', 'error', '-framerate', String(FPS), '-i', path.join(dir, '%04d.jpg'),
    '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '18', `${out}${c.name}.mp4`]);
  fs.rmSync(dir, { recursive: true });
  console.log('recorded', c.name, `${c.secs}s`);
}
await browser.close();
