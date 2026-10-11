// Prints recipe results for the cases given on stdin, for the SciPy reference test. Needs node --experimental-strip-types.
import { readFileSync } from 'node:fs';
import { median, mannWhitney, bootstrapDiff } from '../../src/scripts/recipe.ts';

const cases = JSON.parse(readFileSync(0, 'utf8'));
console.log(JSON.stringify(cases.map(([a, b]) => ({ diff: median(a) - median(b), ...mannWhitney(a, b), ci: bootstrapDiff(a, b) }))));
