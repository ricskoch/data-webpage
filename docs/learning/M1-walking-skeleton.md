# M1: Walking skeleton

**What we build:** the smallest real website: Home, About, Data policy and a 404 page, with automatic checks, before any data work. "Walking skeleton" means it goes through the whole path (code, review, preview, production, rollback) even though it does almost nothing yet.

**New concepts:** static site, build, preview deployment, accessibility test, deploy, rollback.

**What you can check yourself**
1. On the PR, the `site` check runs typecheck, build, dependency audit and 22 browser tests. Open it and read the list of test names; they describe what the site promises.
2. Locally (optional): `npm ci`, `npm run dev`, open http://localhost:4321.
3. The tests include: no accessibility violations, no sideways scrolling on a phone-width screen, and no cookies.

**Deploying to Cloudflare Pages (your clicks, after merge; I will not touch Cloudflare)**
1. Cloudflare dashboard > Workers & Pages > Create > Pages > Connect to Git, pick `ricskoch/data-webpage`.
2. Production branch: `main`. Build command: `npm run build`. Output directory: `dist`. Environment variable: `NODE_VERSION` = `22`.
3. Do not add any paid add-on. Leave Web Analytics for later.
4. After the first deploy, open the `*.pages.dev` address and click through the three pages.

**Rollback practice (do once):** in Pages > Deployments, find the previous deployment and choose "Rollback to this deployment"; then deploy forward again. This is the emergency procedure; you want to have done it once when nothing is wrong.

**Note (learned during the first deploy):** Cloudflare now creates new projects as Workers projects, which run `npx wrangler deploy` after the build. `wrangler.jsonc` tells it to publish the `dist` folder as static files. Without it, wrangler tried to reconfigure the Astro project and failed.

**How it can go wrong:** the build fails on Cloudflare because of the Node version (the repo now pins Node 22 in `.node-version`; Cloudflare reads it automatically); a dependency update breaks a page (tests catch most of it); you forget the preview exists and the live site differs (check the deployment list).
