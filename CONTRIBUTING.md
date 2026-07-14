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
ruff format --check custom_components/backup_checkup
ruff check custom_components/backup_checkup
python -m compileall custom_components/backup_checkup
python -m json.tool custom_components/backup_checkup/manifest.json
```

Integrity changes should also be tested against unprotected and protected SecureTar
archives, an included SQLite database, an incorrect password, and a deliberately
corrupted inner archive.

The repository workflow additionally runs HACS validation and Home Assistant
hassfest.

## Translations

`strings.json` is the English source. Translation files are stored in
`custom_components/backup_checkup/translations/`.

Do not change entity keys in only one language. Every translation file must contain
the same structure and placeholders as `strings.json`.
