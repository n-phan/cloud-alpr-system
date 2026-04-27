# Automated License Plate Recognition (ALPR) System

A cloud-native AWS-based system for automated license plate detection and recognition.

## Project Structure

- `alpr-frontend/` — React/Vite frontend application
- `alpr-backend/` — AWS Lambda backend functions
- `notebooks/` — Jupyter notebooks for ML pipeline
- `aws-config.txt` — AWS resource configuration (do not commit)

## Frontend Deployment

The frontend is hosted as a static site on S3, served via CloudFront over HTTPS.

### Resources

| Resource | Value |
|---|---|
| S3 Bucket | `alpr-frontend-static-cmpe281` |
| AWS Region | `us-west-2` |
| CloudFront Domain | `d6a851qo7fohd.cloudfront.net` |

### Prerequisites

- AWS CLI installed and configured (`aws configure`)
- Node.js and npm installed
- Sufficient IAM permissions for S3 and CloudFront

### Re-deploy (updating the frontend)

Run these commands from the `alpr-frontend/` directory each time you want to push changes.

**1. Build the static files**
```bash
npm run build
```

**2. Upload to S3**
```bash
aws s3 sync dist/ s3://alpr-frontend-static-cmpe281/ \
  --region us-west-2 \
  --delete
```

**3. Invalidate the CloudFront cache**
```bash
aws cloudfront create-invalidation \
  --distribution-id YOUR_DISTRIBUTION_ID \
  --paths "/*"
```

Replace `YOUR_DISTRIBUTION_ID` with the CloudFront Distribution ID (find it in the AWS Console under CloudFront > Distributions).

**4. Verify deployment**
```bash
aws cloudfront get-distribution \
  --id YOUR_DISTRIBUTION_ID \
  --query "Distribution.Status"
```

Wait until the status returns `"Deployed"`, then verify the site at `https://d6a851qo7fohd.cloudfront.net`.

