// Build-independent export: serves dist/ with `vite preview`, opens ?print=1 in headless Chrome,
// checks for clipped text, then writes poster.pdf (36 × 24 in, vector) and poster.png (2× = 6912 × 4608).
// Usage: npm run build && npm run export   (CHROME env var overrides the browser path)
import { preview } from 'vite';
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const chrome = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const server = await preview({ root, preview: { port: 4185, strictPort: false }, logLevel: 'silent' });
const url = server.resolvedUrls.local[0] + '?print=1';
const browser = await puppeteer.launch({ executablePath: chrome, headless: true, args: ['--font-render-hinting=none'] });
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 3456, height: 2304, deviceScaleFactor: 2 });
  await page.goto(url, { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  const problems = await page.evaluate(() => {
    const out = [];
    const poster = document.getElementById('poster').getBoundingClientRect();
    for (const el of document.querySelectorAll('#poster *')) {
      const r = el.getBoundingClientRect();
      if (!r.width || !r.height) continue;
      if (r.right > poster.right + 1 || r.bottom > poster.bottom + 1) out.push(`outside poster: <${el.tagName.toLowerCase()} class="${el.className?.baseVal ?? el.className}"> ${(el.textContent || '').slice(0, 50)}`);
    }
    for (const el of document.querySelectorAll('.col, .ft > div, .panel, .tile, .chip')) {
      if (el.scrollHeight > el.clientHeight + 2 || el.scrollWidth > el.clientWidth + 2) out.push(`overflow in .${el.className}: +${el.scrollHeight - el.clientHeight}px tall, +${el.scrollWidth - el.clientWidth}px wide`);
    }
    for (const col of document.querySelectorAll('.col')) {
      const last = [...col.children].at(-1).getBoundingClientRect();
      const box = col.getBoundingClientRect();
      if (last.bottom > box.bottom + 1) out.push(`column .${col.className} content ends ${Math.round(last.bottom - box.bottom)}px below its box`);
    }
    return [...new Set(out)].slice(0, 40);
  });
  if (problems.length) console.log('LAYOUT WARNINGS:\n  ' + problems.join('\n  '));
  else console.log('layout check: no clipping or overflow found');
  const space = await page.evaluate(() => [...document.querySelectorAll('.col')].map((c) => {
    const last = [...c.children].at(-1).getBoundingClientRect();
    return `${c.className}: ${Math.round(c.getBoundingClientRect().bottom - last.bottom)}px free`;
  }));
  console.log(space.join(' | '));
  await page.pdf({ path: path.join(root, 'poster.pdf'), width: '36in', height: '24in', printBackground: true, preferCSSPageSize: true, pageRanges: '1' });
  await page.screenshot({ path: path.join(root, 'poster.png'), clip: { x: 0, y: 0, width: 3456, height: 2304 } });
  const pdf = fs.readFileSync(path.join(root, 'poster.pdf'), 'latin1');
  const boxes = [...pdf.matchAll(/\/MediaBox\s*\[\s*([\d.]+)\s+([\d.]+)\s+([\d.]+)\s+([\d.]+)\s*\]/g)].map((m) => [m[3] - m[1], m[4] - m[2]]);
  console.log(`poster.pdf: ${boxes.length} page(s), ${boxes.map(([w, h]) => `${w / 72} × ${h / 72} in`).join(', ')}`);
} finally {
  await browser.close();
  server.httpServer.close();
}
