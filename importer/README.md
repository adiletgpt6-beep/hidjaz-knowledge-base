# R2 importer

Archives Instagram media into the existing private Cloudflare R2 bucket, using only the `hidjaz/instagram/` prefix. Never delete or overwrite BalaGo objects.

## One-video test

The workflow `.github/workflows/r2-test.yml` is manually dispatched from GitHub Actions. It requires four **repository Actions secrets** (not Vercel project environment variables):
- `R2_ACCOUNT_ID`
- `R2_BUCKET_NAME`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

The last two are mapped to the standard AWS SDK environment variables inside the workflow. Vercel production secrets are **not automatically available to GitHub Actions**. Never commit their values or print them in logs.

Once secrets are configured, run **Actions → Hidjaz R2 one-video test → Run workflow**. Successful output is a JSON line with `status: verified`, post code, object key, bytes and SHA-256, after an independent R2 download and hash check.

If the test reports Instagram HTTP 403/404, refresh the media URLs through a new authorized Apify Instagram scrape, matching posts by `code` or `id`. Update the catalog without losing captions and IDs, then rerun promptly. Do not substitute Instagram HTML/error pages for MP4 files.

## Verified progress — 2026-11-03

- GitHub repository source and workflow inspected.
- `importer/test_one.py` updated to stream downloads, validate MP4, upload to R2, download back, and compare SHA-256.
- Four matching sensitive production environment variable *names* confirmed in Vercel project `balago-studio`; values were not accessed.
- **Blocked:** no available connected GitHub action to create repository Actions secrets or dispatch a new workflow. No R2 upload has been executed or verified.
- **Next:** securely configure GitHub Actions secrets, manually dispatch the test, inspect logs and R2 object, then implement bulk importer with a durable per-object manifest and retries. Do not claim media archived until verified.
