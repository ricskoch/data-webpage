// Reactome pathways (CC BY 4.0, confirmed by Richard 2026-10-18): which genes belong to which pathway.
// Built by datasets/pathways/build.py. Optional: the gene page works unchanged when the file is not published.
export const PATHWAY_URL = 'https://pub-fe3fcf6faccd4f81b4acaee420db9af5.r2.dev/pathways/0.1.0-staging/site/pathways.json';

export interface Pathway { id: string; name: string; genes: string[] }
export interface Pathways { release: string; pathways: Pathway[] }

export async function loadPathways(): Promise<Pathways | null> {
  try {
    const res = await fetch(PATHWAY_URL);
    return res.ok ? ((await res.json()) as Pathways) : null;
  } catch {
    return null;
  }
}

/** The pathways that contain `symbol` (case-insensitive), most specific (fewest genes) first, at most `limit`. */
export function pathwaysOfGene(data: Pathways, symbol: string, limit = 8): Pathway[] {
  const u = symbol.toUpperCase();
  return data.pathways.filter((p) => p.genes.some((g) => g.toUpperCase() === u))
    .sort((a, b) => a.genes.length - b.genes.length || a.name.localeCompare(b.name, 'en')).slice(0, limit);
}

/** Genes of one pathway that exist in the screen collection (`known` = symbols from genes.json), in the pathway's order. */
export function genesInCollection(p: Pathway, known: string[]): string[] {
  const byUpper = new Map(known.map((k) => [k.toUpperCase(), k]));
  return p.genes.flatMap((g) => byUpper.get(g.toUpperCase()) ?? []);
}
