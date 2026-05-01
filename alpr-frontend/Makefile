REGION  := us-west-2
BUCKET  := alpr-frontend-static-cmpe281
CF_DIST := E117ECCVHXLW0J

.PHONY: help build deploy

help:
	@echo "Usage:"
	@echo "  make deploy    build + sync to S3 + invalidate CloudFront"
	@echo "  make build     vite build only"

build:
	npm run build

deploy: build
	@echo "Syncing to s3://$(BUCKET)..."
	aws s3 sync dist/ s3://$(BUCKET)/ \
	  --region $(REGION) \
	  --delete
	@echo "Invalidating CloudFront distribution $(CF_DIST)..."
	aws cloudfront create-invalidation \
	  --distribution-id $(CF_DIST) \
	  --paths "/*" \
	  --query 'Invalidation.{Id:Id,Status:Status}' \
	  --output table
	@echo "Deploy complete. Live at https://d6a851qo7fohd.cloudfront.net"
