import { test, expect } from '@playwright/test';
import { pathwaysOfGene, genesInCollection, type Pathways } from '../src/scripts/pathways';

// Pure-logic tests for the Reactome pathway picker on /gene (F20).
const data: Pathways = { release: '95', pathways: [
  { id: 'R-HSA-1', name: 'Big', genes: ['TP53', 'BAX', 'KRAS', 'NRAS'] },
  { id: 'R-HSA-2', name: 'Small', genes: ['TP53', 'BAX'] },
  { id: 'R-HSA-3', name: 'Other', genes: ['BRCA1'] },
] };

test('pathwaysOfGene: case-insensitive, most specific pathway first, limited', () => {
  expect(pathwaysOfGene(data, 'tp53').map((p) => p.id)).toEqual(['R-HSA-2', 'R-HSA-1']);
  expect(pathwaysOfGene(data, 'TP53', 1).map((p) => p.id)).toEqual(['R-HSA-2']);
  expect(pathwaysOfGene(data, 'ZZZ')).toEqual([]);
});

test('genesInCollection: keeps only genes in the screens, with the collection\'s own spelling', () => {
  expect(genesInCollection(data.pathways[0], ['Tp53', 'KRAS', 'EGFR'])).toEqual(['Tp53', 'KRAS']);
});
