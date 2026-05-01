# ALPR Backend

Python Lambda functions and API Gateway configuration for the ALPR parking system.

All `make` commands must be run from the `alpr-backend/` directory.

---

## Prerequisites

- **AWS CLI** configured with credentials for the `us-west-2` region
- **AWS SAM CLI** — installed via pip: `pip3 install aws-sam-cli`
  - After install, add the SAM binary to your PATH:
    ```bash
    export PATH="$PATH:/Users/<your-username>/Library/Python/3.9/bin"
    ```
  - Add the line above to `~/.zshrc` to make it permanent
- **Python 3** and `pip` available locally (used to bundle dependencies when packaging)

---

## Lambda Function Overview

| Function | API Route |
|---|---|
| `presigned-url-generator` | `POST /presigned-url` |
| `permit-checker` | `GET /check-permit` |
| `event-retriever` | `GET /get-events` |
| `plate-submission-handler` | `POST /submit-plate` |
| `validation-backlog-handler` | — (internal) |
| `validation-backlog-admin-handler` | — (internal) |
| `gateevents-stream-router` | — (DynamoDB stream trigger) |
| `citation-create-handler` | `POST /citation` |
| `s3-uploader` | `POST /upload-image` |
| `citation-lookup-handler` | `GET /get-citations` |

**Code changes** to any function are deployed the same way — `make deploy fn=<name>` — which zips the handler and calls `aws lambda update-function-code`.

**Infrastructure changes** (new API Gateway routes, environment variables, IAM permissions) must go through SAM. `citation-lookup-handler`'s API route and permissions are defined in `template.yaml` and were provisioned with `make deploy-stack` when the function was first created. Run `make deploy-stack` again any time `template.yaml` changes — for everything else, `make deploy` is sufficient.

---

## Deploying Code Changes

### Updating an existing (manually-managed) function

```bash
make deploy fn=<function-name>
```

Example — update the permit checker after editing `lambda/permit-checker/handler.py`:

```bash
make deploy fn=permit-checker
```

This packages the handler and its dependencies into a zip file, uploads it to Lambda, and prints a confirmation table with the function name, last modified time, and code size.

### Updating all existing functions at once

```bash
make deploy-all
```

Iterates through every manually-managed function and runs `make deploy` on each. Useful after a shared utility change or a batch update.

### Updating the SAM-managed stack (`citation-lookup-handler`)

```bash
make deploy-stack
```

Runs `sam build` followed by `sam deploy`. This packages the Lambda code, uploads it to S3, and applies the CloudFormation changeset. Use this any time you change `lambda/citation-lookup-handler/handler.py`, `template.yaml`, or `samconfig.toml`.

> **Note:** `make deploy-stack` also controls the API Gateway route (`GET /get-citations`). Any new Lambda functions or routes added to `template.yaml` will be created automatically on the next `deploy-stack` run.

---

## Debugging

### Tail CloudWatch logs for any function

```bash
make logs fn=<function-name>
```

Streams live log output from the function's CloudWatch log group. Press `Ctrl+C` to stop.

### Invoke a function locally with its test payload

```bash
make test fn=<function-name>
```

Each function directory contains a `test-payload.json` with a representative input event. The response is printed to the terminal and also saved to `/tmp/<function-name>-response.json`.

---

## Adding a New Lambda Function

**If the function needs a new API Gateway route**, add it to `template.yaml` following the pattern used by `CitationLookupFunction` and its associated `AWS::ApiGateway::*` resources. Deploy with `make deploy-stack`.

**If the function is standalone** (stream trigger, internal), you can create it manually in the AWS Console using the same IAM role (`ALPRLambdaExecutionRole`) and then use `make deploy fn=<name>` for future code updates. Add the function name to the `EXISTING_FUNCTIONS` list in the `Makefile` to include it in `make deploy-all`.

---

## Project Structure

```
alpr-backend/
├── template.yaml          # SAM template — SAM-managed Lambdas + API Gateway resources
├── samconfig.toml         # Persisted SAM deploy settings (stack name, region, S3 bucket)
├── Makefile               # Deploy, test, and log commands
└── lambda/
    ├── citation-lookup-handler/   # SAM-managed
    │   ├── handler.py
    │   ├── requirements.txt
    │   └── test-payload.json
    ├── permit-checker/            # Manually managed
    │   ├── handler.py
    │   ├── requirements.txt
    │   └── test-payload.json
    └── ...                        # Other functions follow the same structure
```
