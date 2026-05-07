# Security Policy

## Supported versions

This project is a demonstration build. Only the latest commit on `main` is
actively maintained.

## Reporting a vulnerability

If you discover a security vulnerability, please do not open a public GitHub
issue. Instead, report it privately:

- Email: [your preferred contact email]
- GitHub: Use the private vulnerability reporting feature under the Security
  tab of this repository

Please include:
- A description of the vulnerability
- Steps to reproduce
- Potential impact
- Any suggested remediation

You can expect an acknowledgment within 48 hours.

## Known security posture of this build

This is a demo-grade build. The following security measures are intentionally
absent and are documented as production upgrade paths in the spec documents:

- **No authentication** — the API is open. Do not deploy publicly without
  adding authentication (see FastAPI Routes Spec, Production Callouts).
- **No rate limiting** — enforced at the API gateway layer in production.
- **No input sanitization beyond Pydantic validation** — sufficient for demo,
  production deployments should add additional validation.
- **Base64 audio in JSON** — not a security issue but is inefficient; see
  production callout in Rime TTS Integration Spec.

## API keys

All API keys and secrets are loaded from environment variables. The
`.env.example` file contains placeholder values only — no real credentials
are ever committed to this repository. If you discover a committed credential,
report it immediately via the process above.
