# Security Policy

## Reporting a vulnerability

If you discover a security issue, **do not file a public issue.**

Instead, use GitHub's private vulnerability reporting:
`https://github.com/justcheburek0-design/remna-sub-injector/security/advisories/new`

Or contact the maintainer directly.

## Known security considerations

- The injector has **no built-in authentication**. Security depends on:
  - Keeping port 3020 private (firewall / Docker network).
  - Secrecy of the subscription token in the URL.
- The injector itself does **not** serve TLS. Use a reverse proxy (nginx, Caddy) with TLS termination for production deployments.
- Do **not** commit `config.toml`, `data/`, or any file containing proxy URIs with credentials to public repositories.
