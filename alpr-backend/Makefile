REGION     := us-west-2
STACK_NAME := alpr-citations-stack
LAMBDA_DIR := lambda

# All functions are now managed by the SAM stack in template.yaml.
# make deploy fn=<name>  — fast code-only update via update-function-code (skips CloudFormation)
# make deploy-stack      — full SAM build + deploy (required for infrastructure changes)
ALL_FUNCTIONS := \
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

.PHONY: help build deploy-stack deploy deploy-all package test logs

help:
	@echo "Usage:"
	@echo "  make deploy-stack        sam build + deploy — use for infrastructure changes"
	@echo "                           (template.yaml edits: env vars, new routes, new functions)"
	@echo "  make deploy fn=<name>    fast code-only update for a single function"
	@echo "  make deploy-all          fast code-only update for all functions"
	@echo "  make test fn=<name>      invoke a function with its test-payload.json"
	@echo "  make logs fn=<name>      tail CloudWatch logs for a function"

# ── SAM stack (infrastructure + code) ────────────────────────────────────────

build:
	sam build --template template.yaml

deploy-stack: build
	sam deploy \
	  --stack-name $(STACK_NAME) \
	  --region $(REGION) \
	  --capabilities CAPABILITY_IAM CAPABILITY_AUTO_EXPAND \
	  --resolve-s3 \
	  --no-fail-on-empty-changeset

# ── Fast code-only updates (bypass CloudFormation) ───────────────────────────

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
	@echo "Deploying $(fn)..."
	aws lambda update-function-code \
	  --function-name $(fn) \
	  --zip-file fileb://$(LAMBDA_DIR)/$(fn)/function.zip \
	  --region $(REGION) \
	  --query '{FunctionName: FunctionName, LastModified: LastModified, CodeSize: CodeSize}' \
	  --output table
	@echo "Done."

deploy-all:
	@for fn in $(ALL_FUNCTIONS); do \
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
