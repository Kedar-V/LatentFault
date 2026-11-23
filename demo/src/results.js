// Recorded model answers (scripts/run_orin.py, scripts/run_orin_perception.py -> scripts/build_recorded.py).
import REC from './recorded.json';

const USABLE = ['LEFT', 'RIGHT', 'BRAKE', 'ALERT', 'NO ALERT'];

function stats(cell, hit) {
  if (!cell) return null;
  const c = cell.counts;
  const n = USABLE.reduce((a, k) => a + (c[k] || 0), 0);
  const failed = Object.entries(c).filter(([k]) => !USABLE.includes(k)).reduce((a, [, v]) => a + v, 0);
  const k = c[hit] || 0;
  return { k, n, p: n ? k / n : 0, failed };
}

// Replays a representative answer: one whose decision is the model's most common decision in this setting.
// window.__prefer (dev only, used by scripts/record_clips.mjs) selects which of those answers to replay by its text.
function pick(cell) {
  if (!cell?.answers.length) return null;
  const top = Math.max(...USABLE.map((d) => cell.counts[d] || 0));
  const modal = USABLE.filter((d) => (cell.counts[d] || 0) === top);
  const pool = cell.answers.filter((a) => modal.includes(a[0]));
  const preferred = import.meta.env.DEV && window.__prefer && pool.find((a) => a[1].includes(window.__prefer));
  return preferred || pool[Math.floor(Math.random() * pool.length)];
}

// groundTruth: the model was given the simulator's exact lane contents (perfect perception) before deciding.
export const drivingCell = (scen, model, sign, groundTruth) => REC[groundTruth ? 'driving_gt' : 'driving']?.[scen.id]?.[model]?.[sign ? 'sign' : 'none'];
export const drivingStats = (scen, model, sign, groundTruth) => stats(drivingCell(scen, model, sign, groundTruth), scen.signSide);
export const drivingAnswer = (scen, model, sign, groundTruth) => pick(drivingCell(scen, model, sign, groundTruth));

export const cameraCell = (c, model) => REC.camera[c.id]?.[model]?.all;
export const cameraStats = (c, model) => stats(cameraCell(c, model), 'NO ALERT');
export const cameraAnswer = (c, model) => pick(cameraCell(c, model));
