# Hidjaz media storage

Reuse the existing Cloudflare R2 account and bucket configured for BalaGo Studio.

Object key prefix: hidjaz/instagram/
- videos/
- images/
- manifests/

Keep the bucket private. Do not store credentials in GitHub. Download source media server-side, then upload and verify each object. Record SHA-256, object key, bytes, and source post ID. Preserve existing BalaGo objects and workflows. Instagram CDN URLs may expire.

Status: plan only; R2 upload is not yet connected or verified.
