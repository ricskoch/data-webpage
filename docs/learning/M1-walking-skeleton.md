# M1: Walking skeleton

**What we build:** the smallest real website: Home, About, Data policy and a 404 page, with automatic checks, before any data work. "Walking skeleton" means it goes through the whole path (code, review, preview, production, rollback) even though it does almost nothing yet.

**New concepts:** static site, build, preview deployment, accessibility test, deploy, rollback.

**What you can check yourself**
1. On the PR, the `site` check runs typecheck, build, dependency audit and 22 browser tests. Open it and read the list of test names; they describe what the site promises.
2. Locally (optional): `npm ci`, `npm run dev`, open http://localhost:4321.
3. The tests include: no accessibility violations, no sideways scrolling on a phone-width screen, and no cookies.

**Deploying to Cloudflare (what actually worked; menu names are from Richard's dashboard on 2026-10-11)**
1. Create a project from the GitHub repo `ricskoch/data-webpage`. Cloudflare creates it as a Workers project named `data-webpage`.
2. Production branch: `main`. Build command: `npm run build`. Deploy command: `npx wrangler deploy` (the default). Add the variable `NODE_VERSION` = `22` under "Variables and secrets".
3. Do not add any paid add-on. Leave Web Analytics for later.
4. The site address is **not shown automatically**. Open the project > **Domains** and activate the `workers.dev` address yourself. Then open it and click through the three pages.

**Rollback practice (do once):** in the project's deployments or version history, find the previous version and roll back to it, reload the site, then roll forward to the newest version again. Menu names may differ; use whatever your dashboard calls it. This is the emergency procedure; you want to have done it once when nothing is wrong.

**Rule for these instructions:** Cloudflare's menus change often. Any dashboard instructions written from memory are a guess. Check them against current Cloudflare documentation, and correct this note when reality differs, as it did here.

**Note (learned during the first deploy):** Cloudflare now creates new projects as Workers projects, which run `npx wrangler deploy` after the build. `wrangler.jsonc` tells it to publish the `dist` folder as static files. Without it, wrangler tried to reconfigure the Astro project and failed.

**Known issue, accepted (decision 2026-10-11):** the Cloudflare check "Workers Builds: data-webpage" is red on every pull request branch. Cloudflare builds PR branches with a separate preview command (`npx wrangler preview`, an open beta feature) that failed with our configuration; production builds from `main` work. Adding a `previews` block did not fix it, and Richard chose not to spend more time on it. **Ignore this one red check.** The real merge signal is the three GitHub checks: `site`, `secret-scan` and `repo-hygiene`. If a different check goes red, that is a real problem. Fallback if ever wanted: set the dashboard Preview command to `npx wrangler versions upload`.

**How it can go wrong:** the build fails on Cloudflare because of the Node version (the repo now pins Node 22 in `.node-version`; Cloudflare reads it automatically); a dependency update breaks a page (tests catch most of it); you forget the preview exists and the live site differs (check the deployment list).
