# Secure Genomic Variant Search

A research repository containing a **local plaintext VCF browser explorer** and Python-based **synthetic metric auditing demonstrations**. The current code does **not** implement Path ORAM, encrypted VCF storage, homomorphic encryption, access-pattern hiding, or privacy-preserving federated search. It must not be used for clinical decision support or considered HIPAA/GDPR compliant.

## Browser VCF explorer

Open the standalone interface in [web/](web/), or serve it locally:

~~~bash
python -m http.server 8080 --directory web
~~~

Then open http://127.0.0.1:8080/ .

- Load a **plain-text, uncompressed VCF** (maximum 10 MiB / 100,000 records), or select the synthetic example.
- Filter by chromosome, inclusive 1-based coordinate interval, or text in ID/REF/ALT/INFO.
- Review up to 250 matching records on screen and export all matches to CSV.
- Chromosomes with and without the "chr" prefix are treated equivalently.

The browser does not upload genomic files or use a remote API to perform searches. Files and query results remain in browser memory during the session. This is **not** an encrypted/ORAM implementation; use synthetic or appropriately authorized data only. It does not interpret variant pathogenicity, normalize alleles, or perform genotype analysis.

GitHub Pages is configured for static deployment via the Pages workflow, but deployment depends on GitHub Pages being enabled for the repository.

## Python CLI

Requires Python 3.10+.

~~~bash
python -m pip install -e '.[server,test]'
secure-genomic-variant-search audit --task-id SYNTHETIC-01 --target TEST
secure-genomic-variant-search chat "What does this demo do?"
secure-genomic-variant-search batch --input sample.csv --output results.csv
secure-genomic-variant-search verify-audit
python -m pytest -q
node --test tests/web.test.cjs
~~~

The Python CLI audits generic numerical metrics using fixed demo thresholds and an in-memory HMAC event chain. The secure_variant_search package contains a separate legacy auditing CLI; the installed command uses the top-level CLI to match the Docker entrypoint. The enrichment.py modules are threshold-based demonstration models rather than implementations of the cryptographic algorithms named by their classes.

### HTTP API

~~~bash
export AUDIT_SECRET_KEY="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
export API_ACCESS_TOKEN="$(python -c 'import secrets; print(secrets.token_urlsafe(48))')"
secure-genomic-variant-search serve --host 127.0.0.1 --port 8000
~~~

GET /health is publicly available; other routes require the X-API-Key header with the value of API_ACCESS_TOKEN, and return an error if no token is configured. The API is **not hardened for direct public Internet exposure**: put it behind TLS, strong network controls, and appropriate authentication/rate limiting for any nonlocal use.

### Docker

Copy .env.example to .env, populate both secret variables with independently generated high-entropy values, then run **docker compose up --build**. Docker Compose binds the service to 127.0.0.1:8000 by default; do not publish it externally without additional controls.

## Security and limitations

- The identifier-pattern guard is **heuristic**. It cannot guarantee PHI removal or comprehensive de-identification.
- The HMAC audit chain checks signatures and parent links, but exists **only in process memory**. Without a configured secret it uses a random process-local key, and events cannot be verified across restarts. A production-grade append-only audit backend is not included.
- The backend retains up to 1,000 recent dossiers in memory; it is not a permanent protected record store.
- API authentication is a shared static secret. Do not expose it in a browser-based public site.
- The VCF web application is purely static JavaScript, so no Python/Pyodide runtime is required on GitHub Pages.

## Development

CI runs Python tests on 3.10, 3.11, 3.12 and Node.js tests for VCF parsing, search, and CSV export. The project uses Python, Pydantic, FastAPI (optional server), and plain browser JavaScript. See the [MIT license](LICENSE).
