# R2 staging bucket (prototype data)

Status: set up by Richard on 2026-10-11. Dashboard steps below were written without access to Cloudflare's
current docs; fix them when the dashboard differs.

- Bucket: `data-webpage-staging`, public development URL `https://pub-fe3fcf6faccd4f81b4acaee420db9af5.r2.dev`.
- Files: `biogrid-orcs/0.1.0-staging/` holds the Parquet tables, manifest, validation report, and `site/` (gzipped JSON the website reads).
- GitHub repository secrets: `R2_ACCOUNT_ID`, `R2_ACCESS_KEY_ID`, `R2_SECRET_ACCESS_KEY` (token: Object Read & Write, this bucket only).
- Upload: Actions > "Publish data to R2 staging" > Run workflow. Manual only; stops if the upload would exceed 3 GB.
- This is staging, not a data release: the bioinformatician review and the `data-release` gate in spec 6.3 still apply.
- The r2.dev URL is rate-limited and meant for development; production needs a custom domain with caching (spec 16.1).

CORS policy on the bucket (required: without it the pages show "Data not available. TypeError: Failed to fetch", even though the files open directly in a browser tab):
```json
[{"AllowedOrigins": ["https://data-webpage.richard-izrael.workers.dev", "http://localhost:4321"],
  "AllowedMethods": ["GET", "HEAD"], "AllowedHeaders": ["Range"],
  "ExposeHeaders": ["Content-Length", "Content-Range", "ETag"], "MaxAgeSeconds": 3600}]
```

**Kill switch:** delete the token in Cloudflare (stops uploads) or turn off the public URL (stops reads).
