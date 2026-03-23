# Release Process

## v0.1.1 Baseline

This repository now treats `0.1.1` as the current packaged alpha release.

Release expectations:

- package version in `pyproject.toml` and `src/ibus_voice/__init__.py` must match
- `PYTHONPATH=src python3 -m unittest discover -s tests -v` must pass
- package scripts should build release artifacts when host tools are installed
- release notes should be updated in `CHANGELOG.md`

## Local Checklist

1. Confirm the working tree is clean enough for a release.
2. Run the unit tests.
3. Run `./scripts/build-deb.sh` on a system with `dpkg-deb`.
4. Run `./scripts/build-rpm.sh` on a system with `rpmbuild`.
5. Verify artifacts in `.dist/packages/`.
6. Review `README.md`, `docs/user/getting-started.md`, and `CHANGELOG.md`.
7. Create the `v0.1.1` tag after the release commit is finalized.
