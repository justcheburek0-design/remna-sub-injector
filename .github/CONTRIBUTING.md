# Contributing

Thanks for helping improve `remna-sub-injector`.

## Before you start

- Fork the repo and create a feature branch.
- Keep changes focused and small.
- Avoid committing local runtime data, credentials, or generated binaries.

## Development workflow

1. Install the Rust toolchain.
2. Run tests locally:
   ```bash
   cargo test
   ```
3. Format code before opening a PR:
   ```bash
   cargo fmt
   ```
4. If you change behavior, update docs and examples.

## What belongs in a PR

- Code changes
- Tests for new logic or regressions
- Docs updates when configuration or behavior changes

## What should not be committed

- Secrets, tokens, subscriptions, or link dumps
- `config.toml`
- `docker-compose.yml`
- `bin/`
- `target/`
- Runtime `data/` files containing credentials

## PR review checklist

- [ ] Tests pass
- [ ] Code is formatted
- [ ] Docs are updated
- [ ] No secrets or private URLs are included
