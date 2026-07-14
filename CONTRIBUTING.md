# Contributing to BackupCheckup

Contributions are welcome for bug fixes, documentation, translations, and focused
feature improvements.

## Before opening a pull request

1. Search existing issues and pull requests.
2. Keep changes focused on one problem or feature.
3. Preserve existing entity unique IDs unless a breaking migration is included.
4. Update `CHANGELOG.md` and documentation when behavior changes.
5. Keep all translations structurally aligned with `strings.json`.

## Local validation

Run at least:

```bash
python -m compileall custom_components/backup_checkup
python -m json.tool custom_components/backup_checkup/manifest.json
```

The repository workflow also runs HACS validation and Home Assistant hassfest.

## Translations

`strings.json` is the English source. Translation files are stored in
`custom_components/backup_checkup/translations/`.

Do not change entity keys in only one language. Every translation file must contain
the same structure as `strings.json`.
