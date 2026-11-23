// Writes recorded/perception.json: the exact objects in each lane of every driving frame, taken from the scene
// definitions in src/data.js. Used as "perfect perception" context for the decision step.
import fs from 'node:fs';
import { DRIVING } from '../src/data.js';

const NAME = { adults5: '5 adults', adults4: '4 adults', adults2: '2 adults', child: '1 child', ball: '1 ball', crosswalk: 'a crosswalk', barrier: 'a concrete barrier' };
const lane = (items) => items.map((i) => NAME[i]).join(', ') || 'nothing';
const out = {};
for (const s of DRIVING) {
  for (const sign of [false, true]) {
    out[`drive_${s.id}_${sign ? 'sign' : 'nosign'}.png`] = { LEFT: lane(s.lanes.LEFT), RIGHT: lane(s.lanes.RIGHT), sign };
  }
}
fs.writeFileSync(new URL('../recorded/perception.json', import.meta.url), JSON.stringify(out, null, 1));
console.log(out);
