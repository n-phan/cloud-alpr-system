# ALPR Backend

Python Lambda functions and API Gateway configuration for the ALPR parking system.
All infrastructure is defined as code in `template.yaml` and managed by AWS SAM / CloudFormation.

All `make` commands must be run from the `alpr-backend/` directory.

---

## Prerequisites

- **AWS CLI** configured with credentials for the `us-west-2` region
- **AWS SAM CLI** — install via Homebrew (recommended on macOS):
  ```bash
  brew install aws-sam-cli
  ```
  > **macOS note:** A known libexpat symbol conflict between Homebrew Python 3.13 and the macOS system library can break `sam build`. The Makefile automatically works around this by preferring Homebrew's expat when it is present — no manual fix needed.
- **Python 3** and `pip` available locally (used to bundle dependencies when packaging)

---

## Lambda Function Overview

All 13 functions are defined in `template.yaml` and tracked by the `alpr-citations-stack`
CloudFormation stack. Functions originally created manually were migrated into the stack via CloudFormation resource import.

| Function | API Route |
|---|---|
| `presigned-url-generator` | `POST /presigned-url` |
| `permit-checker` | `GET /check-permit` |
| `permit-admin-handler` | `GET /permits`, `POST /permits`, `PUT /permits` |
| `event-retriever` | `GET /get-events` |
| `plate-submission-handler` | `POST /submit-plate` |
| `validation-backlog-handler` | — (internal; queues low-confidence detections) |
| `validation-backlog-admin-handler` | `GET /validation-backlog`, `PUT /validation-backlog` |
| `gateevents-stream-router` | — (DynamoDB stream trigger; runs permit check and auto-creates citation when permit is invalid) |
| `citation-create-handler` | `POST /citation` |
| `s3-uploader` | `POST /upload-image` |
| `citation-lookup-handler` | `GET /get-citations` |
| `citation-admin-handler` | `GET /admin-citations`, `PUT /admin-citations` |
| `orphan-scan-handler` | — (EventBridge Scheduler trigger; resolves unmatched entry/exit events after matching window expires) |

---

## Deploying Changes

There are two deployment paths depending on what changed.

### Infrastructure changes — `make deploy-stack`

Use this when you edit `template.yaml`: adding a new function, changing environment variables, modifying a timeout, adding an API Gateway route, etc.

```bash
make deploy-stack
```

Runs `sam build` (packages all functions) followed by `sam deploy` (applies the CloudFormation
changeset). SAM manages an S3 bucket for build artifacts automatically.

### Code-only changes — `make deploy fn=<name>`

Use this for a quick code push when only `handler.py` changed. It zips the function and calls
`aws lambda update-function-code` directly, bypassing CloudFormation for speed.

```bash
make deploy fn=permit-checker
```

The function is still tracked by the SAM stack — the next `make deploy-stack` will bring its
code back in sync with whatever is in `template.yaml`.

### Redeploy all functions at once

```bash
make deploy-all
```

Runs `make deploy` on every function. Useful after a dependency update or a shared utility change.

---

## How SAM Deployment Works (and Why S3 Is Involved)

CloudFormation is a cloud service that runs on AWS's servers, not your local machine. When you run `make deploy-stack`, SAM needs to get your Lambda code (the zipped handler + dependencies) to CloudFormation somehow — it can't pass a local file path because CloudFormation has no access to your laptop.

S3 is the bridge. The deployment process works in three steps:

1. **`sam build`** — packages each function into a zip locally, stored under `.aws-sam/build/`
2. **`sam deploy`** — uploads each zip to the SAM-managed S3 bucket, then sends CloudFormation
   a template where every local `CodeUri` has been replaced with the corresponding S3 location
   (e.g., `s3://aws-sam-cli-managed-.../abc123.zip`)
3. **CloudFormation** — reads the template, fetches the zips from S3, and deploys them to Lambda

The bucket named `aws-sam-cli-managed-default-samclisourcebucket-...` was created automatically by the `--resolve-s3` flag the first time `make deploy-stack` was run. You do not need to manage it manually — SAM handles uploads and versioning.

**Why `make deploy fn=<name>` doesn't use S3:**
`make deploy` calls `aws lambda update-function-code --zip-file fileb://function.zip`, which uploads the zip directly from your machine to Lambda in one step — no CloudFormation, no S3.
This is faster for code-only changes but bypasses the IaC lifecycle (no change preview, no rollback, no state tracking in the stack). Infrastructure changes always go through
`make deploy-stack`.

---

## Adding a New Lambda Function

1. Create a directory under `lambda/` with `handler.py` and `requirements.txt`
2. Add a `test-payload.json` with a representative input event
3. Add a new `AWS::Serverless::Function` block to `template.yaml`, following the pattern of any
   existing function
4. If the function needs an API Gateway route, add the corresponding `AWS::ApiGateway::Resource`,
   `AWS::ApiGateway::Method`, `AWS::Lambda::Permission`, and `AWS::ApiGateway::Deployment`
   resources to `template.yaml`
5. Run `make deploy-stack` to provision everything

---

## Debugging

### Tail CloudWatch logs

```bash
make logs fn=<function-name>
```

Streams live output from the function's CloudWatch log group. Press `Ctrl+C` to stop.

### Invoke a function with its test payload

```bash
make test fn=<function-name>
```

Sends `lambda/<function-name>/test-payload.json` to Lambda and prints the response.

---

## Project Structure

```
alpr-backend/
├── template.yaml          # SAM template — all Lambda functions, API Gateway, and S3 bucket policy
├── samconfig.toml         # Persisted SAM deploy settings (stack name, region, S3 bucket)
├── Makefile               # Deploy, test, and log commands
├── lambda/
│   ├── citation-lookup-handler/
│   │   ├── handler.py
│   │   ├── requirements.txt
│   │   └── test-payload.json
│   ├── permit-checker/
│   │   ├── handler.py
│   │   ├── requirements.txt
│   │   └── test-payload.json
│   └── ...                # All other functions follow the same structure
└── ecs/                   # ECS worker — YOLO detection + Rekognition OCR pipeline
```
