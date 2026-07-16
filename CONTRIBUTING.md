# Contributing to BackupCheckup

Contributions are welcome for bug fixes, documentation, translations, and focused
feature improvements.

## Before opening a pull request

1. Search existing issues and pull requests.
2. Keep changes focused on one problem or feature.
3. Preserve entity unique IDs unless a documented migration is included.
4. Keep verification read-only and never expose backup contents or passwords.
5. Update `CHANGELOG.md` and documentation when behavior changes.
6. Keep all translations structurally aligned with `strings.json`.

## Local validation

Run at least:

```bash
ruff format --check .
ruff check .
pytest --cov=custom_components.backup_checkup --cov-fail-under=70
bandit -q -r custom_components/backup_checkup -x tests
python -m compileall custom_components tests
python -m json.tool custom_components/backup_checkup/manifest.json
```

Integrity changes should also be tested against unprotected and protected SecureTar
archives, an included SQLite database, an incorrect password, and a deliberately
corrupted inner archive.

The repository workflow additionally runs these checks on every push and pull
request together with HACS validation and Home Assistant hassfest.

## Translations

`strings.json` is the English source. Translation files are stored in
`custom_components/backup_checkup/translations/`.

Do not change entity keys in only one language. Every translation file must contain
the same structure and placeholders as `strings.json`.

## Release process

1. Update the version in `custom_components/backup_checkup/manifest.json`,
   `custom_components/backup_checkup/const.py`, the README, and the changelog.
2. Create a Git tag and GitHub release with the same version, for example
   `v2.2.0-beta4`. Mark beta versions as pre-releases.
3. Keep the standard HACS repository layout under
   `custom_components/backup_checkup`.
4. Do not enable `zip_release` and do not attach a required integration ZIP asset.
   HACS installs the integration directly from the tagged repository source.
5. Put the user-facing release notes in the GitHub release so HACS can show them
   in Home Assistant's update dialog.
