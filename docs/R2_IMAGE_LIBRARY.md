# Cloudflare R2 Image Library

Content Factory uses Cloudflare R2 as the persistent image library while GitHub remains the source for code and workflows.

## Bucket

Default bucket name:

`content-factory-images`

Suggested object layout:

- `episodes/<episode-id>/scenes/<scene-id>.png`
- `characters/<character-id>/<version>.png`
- `branding/<asset>.png`
- `references/<topic>/<asset>.png`
- `archive/<yyyy>/<mm>/<asset>.png`

## Required GitHub configuration

Repository secrets:

- `CLOUDFLARE_ACCOUNT_ID`
- `R2_ACCESS_KEY_ID`
- `R2_SECRET_ACCESS_KEY`

Repository variable:

- `R2_BUCKET=content-factory-images`

## Workflow

Run `.github/workflows/r2-library.yml` manually.

Actions:

- `list`: validates connectivity and lists objects.
- `upload`: uploads a repository file to R2.

## Local usage

Install dependency:

```bash
pip install boto3
```

List:

```bash
python scripts/r2_library.py list
```

Upload:

```bash
python scripts/r2_library.py upload path/to/image.png --key episodes/001/scenes/scene-01.png
```

## Security

Never commit R2 credentials. Use scoped R2 credentials limited to this bucket whenever possible.
