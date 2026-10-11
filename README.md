# data-webpage

A website for exploring human CRISPR screen data in one standard format: browse, compare and check reproducibility across screens, with experiment metadata attached.

Status: M1 (walking skeleton). The site has placeholder pages only; no data yet. The source of truth is [docs/spec.md](docs/spec.md).

- Working rules for humans and coding agents: [AGENTS.md](AGENTS.md)
- Learning notes per milestone: [docs/learning/](docs/learning/)
- Glossary: [docs/glossary.md](docs/glossary.md)
- Cost and emergency runbooks: [docs/ops/](docs/ops/)

## Develop

Requires Node 22 or newer.

```
npm ci
npm run dev       # http://localhost:4321
npm run check     # typecheck
npm run build
npm test          # browser tests (needs: npx playwright install chromium)
```
