import { defineConfig } from 'astro/config';

// Build id for data URLs: a new deploy asks for fresh copies of the R2 files (they are cached for up to an hour).
const buildId = (process.env.CF_PAGES_COMMIT_SHA ?? process.env.WORKERS_CI_COMMIT_SHA ?? Date.now().toString(36)).slice(0, 12);

export default defineConfig({
  output: 'static',
  devToolbar: { enabled: false },
  vite: { define: { __BUILD_ID__: JSON.stringify(buildId) } },
});
