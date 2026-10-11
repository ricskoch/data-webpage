# ADR 0002: Code layout and tooling for the site

Status: accepted, 2026-10-11

**Decision**
- Astro static site in `src/` (`pages/`, `layouts/`, `styles/`), TypeScript strict mode, no UI framework yet.
- Tests in `tests/` with Playwright: smoke, navigation, 404, accessibility (axe, WCAG 2.2 AA tags), no horizontal scroll at 375 px, no cookies. Each runs at desktop and mobile width.
- CI runs typecheck, build, `npm audit` (high and above), and the tests on every PR.
- Plain hand-written CSS with light and dark colors. No CSS framework, no web fonts, no third-party scripts.
- Node 22 or newer.

**Why:** the fewest moving parts that satisfy the spec. Fewer dependencies means fewer updates, fewer vulnerabilities and less for an agent to get wrong.

**Trade-off:** hand-written CSS needs more care as the site grows. Revisit when the workspace pages (M4) need shared components.

**Cost:** none.

**Change when:** interactive workspace work starts in M4 (then decide on a component approach, recorded in a new ADR).
