# Automated License Plate Recognition (ALPR) System

A cloud-native AWS-based system for automated license plate detection and recognition.

## Project Structure

- `alpr-frontend/` — React/Vite frontend application
- `alpr-backend/` — AWS Lambda backend functions
- `notebooks/` — Jupyter notebooks for ML pipeline
- `aws-config.txt` — AWS resource configuration (do not commit)

## Deployment

### Frontend

The frontend is hosted as a static site on S3, served via CloudFront over HTTPS.

| Resource | Value |
|---|---|
| S3 Bucket | `alpr-frontend-static-cmpe281` |
| CloudFront Domain | `https://d6a851qo7fohd.cloudfront.net` |
| AWS Region | `us-west-2` |

From the `alpr-frontend/` directory:

```bash
make deploy
```

Builds the app, syncs to S3, and invalidates the CloudFront cache in one step. See `alpr-frontend/README.md` for local development setup and full details.

### Backend

All Lambda functions and infrastructure are managed by AWS SAM / CloudFormation. From the `alpr-backend/` directory:

```bash
make deploy-stack   # infrastructure + code changes (template.yaml edits)
make deploy fn=<name>  # code-only update for a single function
```

See `alpr-backend/README.md` for prerequisites and full details.

