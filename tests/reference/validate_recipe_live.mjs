// Known-biology check for biological workflows on the published staging data (run by the "Validate recipes" workflow).
// Splits: mutation, expression off, copy loss, copy gain. Each case is textbook biology; the workflow must reproduce its direction with a 95% interval that excludes 0.
// Needs node --experimental-strip-types and network access to the R2 bucket.
import { DATA_URL } from '../../src/scripts/data.ts';
import { CTX_URL } from '../../src/scripts/context.ts';
import { makeGrouping } from '../../src/scripts/grouping.ts';
import { dependencyByMutation, verdict } from '../../src/scripts/workflow.ts';

const CASES = [ // [knocked-out gene X, gene Y, expected sign of median(group A) - median(group B), why, split (default mutation)]
  ['KRAS', 'KRAS', -1, 'oncogene addiction: KRAS-mutant lines need KRAS'],
  ['BRAF', 'BRAF', -1, 'oncogene addiction: BRAF-mutant (mostly melanoma) lines need BRAF'],
  ['PIK3CA', 'PIK3CA', -1, 'PIK3CA-mutant lines depend on PIK3CA'],
  ['TP53', 'TP53', -1, 'losing TP53 helps TP53-wild-type lines grow; mutant lines have nothing left to lose'],
  ['MDM2', 'TP53', 1, 'MDM2 is needed only to hold back working TP53, so mutant lines do not need it'],
  ['ERBB2', 'ERBB2', -1, 'copy-number artefact check: lines with extra ERBB2 copies need ERBB2', 'gain'],
  ['SMARCA2', 'SMARCA4', -1, 'paralog pair: SMARCA2 is needed when SMARCA4 is switched off', 'expression'],
  ['ARID1B', 'ARID1A', -1, 'paralog pair: ARID1B is needed when ARID1A is mutated'],
  ['PRMT5', 'MTAP', -1, 'PRMT5 is needed when its neighbour-linked partner MTAP is lost', 'copy'],
];
const get = async (url) => { const r = await fetch(url); if (!r.ok) throw new Error(`${url}: HTTP ${r.status}`); return r.json(); };
const shard = (n) => String(n).padStart(4, '0');

const [genes, screens, lines] = await Promise.all([get(`${DATA_URL}/genes.json`), get(`${DATA_URL}/screens.json`), get(`${CTX_URL}/lines.json`)]);
let failed = 0;
for (const [x, y, sign, why, kind = 'mutation'] of CASES) {
  const [px, sx] = genes[x], [py, sy] = genes[y];
  const rows = (await get(`${DATA_URL}/g/${shard(sx)}.json`))[px] ?? [];
  const yctx = (await get(`${CTX_URL}/g/${shard(sy)}.json`))[py];
  const perScreen = rows.flatMap((r) => {
    const li = lines.screen_line[String(screens[r[0]].screen_id)];
    return li === undefined || r[2] === null ? [] : [{ line: li, value: r[2] }];
  });
  const g = makeGrouping(kind, lines, y, yctx);
  const c = dependencyByMutation(perScreen, g.group, g.include);
  const ok = c.testable && (sign < 0 ? c.ci[1] < 0 : c.ci[0] > 0);
  if (!ok) failed++;
  console.log(`${ok ? 'PASS' : 'FAIL'} ${x} | ${g.a} vs ${g.b}: ${c.mutant.length} vs ${c.wildtype.length} lines, `
    + `difference ${c.diff.toFixed(2)} (95% ${c.ci?.map((v) => v.toFixed(2)).join(' to ') ?? 'n/a'}), p = ${c.p?.toExponential(1) ?? 'n/a'}. `
    + `${verdict(c, x, y, { a: g.a, b: g.b })} Expected because ${why}.`);
}
console.log(`${CASES.length - failed} of ${CASES.length} known-biology cases reproduced.`);
process.exit(failed ? 1 : 0);
