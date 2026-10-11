# Kill switch: take the site and data offline

Use this if costs spike, data was published by mistake, or something abusive is happening. Details of the exact clicks are filled in during M1 and M2b, when the services exist.

1. Cloudflare Pages: unpublish the production deployment, or roll back to the last good one.
2. Cloudflare R2: turn off public access on the `public` bucket (or remove the custom domain).
3. Rotate any token you think leaked (Cloudflare, GitHub, Sanity).
4. Write down what happened and when, then tell the agent. Do not delete data; versions are immutable and can be restored.

Practice this once before launch (milestone M6).
