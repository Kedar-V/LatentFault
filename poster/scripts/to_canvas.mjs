// Turn the rendered poster into a static Design-canvas artboard (.dc.html):
// CSS rules are copied onto each element as inline styles (so the canvas editor can edit them),
// classes and editor attributes are dropped. Usage: npm run build && node scripts/to_canvas.mjs <out.dc.html>
import { preview } from 'vite';
import puppeteer from 'puppeteer-core';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const out = process.argv[2];
const chrome = process.env.CHROME || '/Applications/Google Chrome.app/Contents/MacOS/Google Chrome';
const server = await preview({ root, preview: { port: 4186, strictPort: false }, logLevel: 'silent' });
const browser = await puppeteer.launch({ executablePath: chrome, headless: true });
try {
  const page = await browser.newPage();
  await page.setViewport({ width: 3456, height: 2304 });
  await page.goto(server.resolvedUrls.local[0] + '?print=1', { waitUntil: 'networkidle0' });
  await page.evaluate(() => document.fonts.ready);
  const html = await page.evaluate(() => {
    const poster = document.getElementById('poster');
    const props = new Map(); // element -> Set of longhand property names its rules/inline style declare
    const lh = new Map(); // specified (unitless) line-height per element, cascade order
    const note = (el, style) => {
      if (!props.has(el)) props.set(el, new Set());
      for (let i = 0; i < style.length; i++) if (!style[i].startsWith('--')) props.get(el).add(style[i]);
      const v = style.getPropertyValue('line-height');
      if (v) lh.set(el, v);
    };
    for (const sheet of document.styleSheets) {
      let rules; try { rules = sheet.cssRules; } catch { continue; }
      for (const r of rules) {
        if (!(r instanceof CSSStyleRule)) continue;
        if (/^(html|body|\*|\.app|\.toolbar|\.stage|\.sizer|\.scaler|\.print-root|\.tb|\.is-editable)/.test(r.selectorText)) continue;
        let els; try { els = [...poster.querySelectorAll(r.selectorText)]; } catch { continue; }
        if (poster.matches(r.selectorText)) els.unshift(poster);
        for (const el of els) note(el, r.style);
      }
    }
    const all = [poster, ...poster.querySelectorAll('*')];
    for (const el of all) note(el, el.style);
    ['font-family', 'line-height', 'font-size', 'color', 'background-color', 'width', 'height', 'overflow-x', 'overflow-y']
      .forEach((q) => props.get(poster).add(q));
    // freeze grid tracks to px so the artboard lays out the same everywhere
    const styles = all.map((el) => {
      const cs = getComputedStyle(el);
      const set = props.get(el) || new Set();
      set.add('box-sizing');
      if (el.tagName === 'svg' && el.closest('#poster') !== el) { set.add('width'); set.add('height'); set.add('display'); }
      const out = [];
      for (const q of set) {
        const v = q === 'line-height' && lh.has(el) ? lh.get(el) : cs.getPropertyValue(q);
        if (v !== '') out.push(`${q}: ${v}`);
      }
      return out.join('; ');
    });
    all.forEach((el, i) => {
      if (styles[i]) el.setAttribute('style', styles[i]); else el.removeAttribute('style');
      for (const a of ['class', 'contenteditable', 'spellcheck', 'data-edit-id']) el.removeAttribute(a);
    });
    return poster.outerHTML;
  });
  // images: point each <img> at the asset uploaded to the canvas (scripts/canvas_assets.json, keyed by file stem)
  const assets = JSON.parse(fs.readFileSync(path.join(root, 'scripts', 'canvas_assets.json'), 'utf8'));
  let html2 = html.replace(/<img([^>]*?)src="([^"]+)"/g, (m, pre, src) => {
    const key = Object.keys(assets).find((k) => src.includes(k));
    if (!key) throw new Error(`no canvas asset for image ${src}; upload it and add it to scripts/canvas_assets.json`);
    return `<img${pre}src="${assets[key]}"`;
  });
  const doc = `<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>LatentFault poster</title>
<script src="./support.js"></script>
</head>
<body>
<x-dc>
<helmet>
<style>
@font-face{font-family:'Inter';font-style:normal;font-weight:400;font-display:block;src:url(/_blob/27428d0e4f0e12c85031117da3eaf20b) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:'Inter';font-style:normal;font-weight:500;font-display:block;src:url(/_blob/fb617435b1c87f6e4db3702654e5804d) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:'Inter';font-style:normal;font-weight:600;font-display:block;src:url(/_blob/9fa71ffb720440ad5d41cf883d9facfb) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:'Inter';font-style:normal;font-weight:700;font-display:block;src:url(/_blob/958ae143174e4fea91995ee5fec18c3b) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:'Inter';font-style:normal;font-weight:800;font-display:block;src:url(/_blob/065ced5102d3e8d2666949c624d58809) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:'Inter';font-style:normal;font-weight:400;font-display:block;src:url(/_blob/04b68865c4d8cf41534e06278dd8752a) format('woff2');unicode-range:U+0370-0377,U+037A-037F,U+0384-038A,U+038C,U+038E-03A1,U+03A3-03FF}
@font-face{font-family:'Inter';font-style:normal;font-weight:700;font-display:block;src:url(/_blob/76739314e51615fad100a4d1c0703aa1) format('woff2');unicode-range:U+0370-0377,U+037A-037F,U+0384-038A,U+038C,U+038E-03A1,U+03A3-03FF}
@font-face{font-family:'JetBrains Mono';font-style:normal;font-weight:500;font-display:block;src:url(/_blob/3f720cfd6ec68925f719aadd0ee32429) format('woff2');unicode-range:U+0000-00FF,U+0131,U+0152-0153,U+02BB-02BC,U+02C6,U+02DA,U+02DC,U+0304,U+0308,U+0329,U+2000-206F,U+2074,U+20AC,U+2122,U+2191,U+2193,U+2212,U+2215,U+FEFF,U+FFFD}
@font-face{font-family:'JetBrains Mono';font-style:normal;font-weight:500;font-display:block;src:url(/_blob/9c31dbe2288fcb5be25499256d000462) format('woff2');unicode-range:U+0370-0377,U+037A-037F,U+0384-038A,U+038C,U+038E-03A1,U+03A3-03FF}
body{margin:0}
a{color:#0B8793}a:hover{color:#0B1F3A}
</style>
</helmet>
${html2}
</x-dc>
<script type="text/x-dc" data-dc-script data-props='{"$preview":{"width":3456,"height":2304}}'>
class Component extends DCLogic {
renderVals() {
return {};
}
}
</script>
</body>
</html>
`;
  fs.mkdirSync(path.dirname(out), { recursive: true });
  fs.writeFileSync(out, doc);
  console.log('wrote', out, (doc.length / 1024).toFixed(0), 'KB');
} finally {
  await browser.close();
  server.httpServer.close();
}
