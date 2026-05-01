REGION     := us-west-2
STACK_NAME := alpr-citations-stack
LAMBDA_DIR := lambda

# All functions that can be updated with zip + update-function-code.
# This includes citation-lookup-handler — SAM only needs to run when template.yaml
# changes (new routes, env vars, permissions). For code-only changes, make deploy works.
EXISTING_FUNCTIONS := \
  presigned-url-generator \
  permit-checker \
  event-retriever \
  plate-submission-handler \
  validation-backlog-handler \
  validation-backlog-admin-handler \
  gateevents-stream-router \
  citation-create-handler \
  citation-lookup-handler \
  s3-uploader

.PHONY: help build deploy deploy-stack deploy-all package test logs

help:
	@echo "Usage:"
	@echo "  make build               sam build (SAM-managed functions)"
	@echo "  make deploy-stack        sam build + deploy the SAM stack (first-time or updates)"
	@echo "  make deploy fn=<name>    zip + update-function-code for an existing function"
	@echo "  make deploy-all          redeploy all existing (non-SAM) functions"
	@echo "  make test fn=<name>      invoke a function with its test-payload.json"
	@echo "  make logs fn=<name>      tail CloudWatch logs for a function"

# ── SAM-managed stack ─────────────────────────────────────────────────────────

build:
	sam build --template template.yaml

# --resolve-s3 lets SAM create and manage its own S3 bucket for artifacts.
# On first run this prompts for stack name/region; answers are saved to samconfig.toml.
deploy-stack: build
	sam deploy \
	  --stack-name $(STACK_NAME) \
	  --region $(REGION) \
	  --capabilities CAPABILITY_IAM \
	  --resolve-s3 \
	  --no-fail-on-empty-changeset

# ── Existing functions (zip + update-function-code) ───────────────────────────

package:
	@test -n "$(fn)" || (echo "ERROR: fn=<function-name> required" && exit 1)
	@echo "Packaging $(fn)..."
	@cd $(LAMBDA_DIR)/$(fn) && \
	  pip install -r requirements.txt -t ./package --quiet && \
	  cp handler.py ./package/ && \
	  cd ./package && zip -r ../function.zip . -x "*.pyc" "**/__pycache__/*" > /dev/null && \
	  cd .. && rm -rf ./package
	@echo "Created $(LAMBDA_DIR)/$(fn)/function.zip"

deploy: package
	@echo "Deploying $(fn) to Lambda..."
	aws lambda update-function-code \
	  --function-name $(fn) \
	  --zip-file fileb://$(LAMBDA_DIR)/$(fn)/function.zip \
	  --region $(REGION) \
	  --query '{FunctionName: FunctionName, LastModified: LastModified, CodeSize: CodeSize}' \
	  --output table
	@echo "Done."

deploy-all:
	@for fn in $(EXISTING_FUNCTIONS); do \
	  echo ""; \
	  echo "==> Deploying $$fn..."; \
	  $(MAKE) deploy fn=$$fn; \
	done

# ── Debugging helpers ─────────────────────────────────────────────────────────

test:
	@test -n "$(fn)" || (echo "ERROR: fn=<function-name> required" && exit 1)
	aws lambda invoke \
	  --function-name $(fn) \
	  --cli-binary-format raw-in-base64-out \
	  --payload file://$(LAMBDA_DIR)/$(fn)/test-payload.json \
	  --region $(REGION) \
	  /tmp/$(fn)-response.json && cat /tmp/$(fn)-response.json

logs:
	@test -n "$(fn)" || (echo "ERROR: fn=<function-name> required" && exit 1)
	aws logs tail /aws/lambda/$(fn) --follow --region $(REGION)
