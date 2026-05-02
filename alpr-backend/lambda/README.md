# Testing Guide - Lambda Functions

## Quick Test for Each Function

### Function 1: presigned-url-generator

```bash
cat > payload.json << 'EOF'
{}
EOF

aws lambda invoke \
  --function-name presigned-url-generator \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**: Returns `uploadUrl`, `expiresIn`, `key`

---

### Function 2: permit-checker (Valid Vehicle)

```bash
cat > payload.json << 'EOF'
{"queryStringParameters":{"vehicleId":"ABC-1234"}}
EOF

aws lambda invoke \
  --function-name permit-checker \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**: 
- `statusCode`: 200
- `vehicleId`: "ABC-1234"
- `owner`: "John Doe"
- `permitStatus`: "VALID"

---

### Function 2: permit-checker (Invalid Vehicle)

```bash
cat > payload.json << 'EOF'
{"queryStringParameters":{"vehicleId":"INVALID-9999"}}
EOF

aws lambda invoke \
  --function-name permit-checker \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**: 
- `statusCode`: 404
- `error`: "Vehicle INVALID-9999 not found"

---

### Function 3: event-retriever

```bash
cat > payload.json << 'EOF'
{"queryStringParameters":{"limit":"10"}}
EOF

aws lambda invoke \
  --function-name event-retriever \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**: 
- `statusCode`: 200
- Array of events with `timestamp`, `vehicleId`, `plateText`, `confidence`, `permitStatus`, `eventType`

---

### Function 4: plate-submission-handler

```bash
cat > payload.json << 'EOF'
{
  "body": {
    "vehicleId": "ABC-1234",
    "plateText": "ABC-1234",
    "confidence": 0.95,
    "permitStatus": "VALID",
    "eventType": "ENTRY"
  }
}
EOF

aws lambda invoke \
  --function-name plate-submission-handler \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**: 
- `statusCode`: 201
- `message`: "Event recorded"
- `timestamp`: (current time in milliseconds)

---

### Function 5: validation-backlog-handler (Low Confidence)

```bash
cat > payload.json << 'EOF'
{
  "body": {
    "vehicleId": "LOW-TEST-001",
    "plateText": "LOW-TEST-001",
    "confidence": 0.45,
    "permitStatus": "UNKNOWN",
    "eventType": "ENTRY"
  }
}
EOF

aws lambda invoke \
  --function-name validation-backlog-handler \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**:
- `statusCode`: 201
- `message`: "Low-confidence result queued for review"
- `backlogId`: UUID

---

### Function 6: s3-uploader

```bash
cat > payload.json << 'EOF'
{
  "body": "{\"imageBase64\":\"<base64-encoded-image>\",\"fileName\":\"test.jpg\"}"
}
EOF

aws lambda invoke \
  --function-name s3-uploader \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**:
- `statusCode`: 200
- `imageUrl`: S3 URL of the uploaded image

---

### Function 7: validation-backlog-admin-handler (List Reviews)

```bash
cat > payload.json << 'EOF'
{"httpMethod":"GET","queryStringParameters":{"limit":"5"}}
EOF

aws lambda invoke \
  --function-name validation-backlog-admin-handler \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**:
- `statusCode`: 200
- `items`: Array of backlog items
- `count`: Number of returned items

---

### Function 8: gateevents-stream-router

```bash
cat > payload.json << 'EOF'
{
  "Records": [
    {
      "eventName": "INSERT",
      "dynamodb": {
        "NewImage": {
          "vehicle_id": { "S": "LOW-TEST-STREAM" },
          "plate_text": { "S": "LOW-TEST-STREAM" },
          "confidence": { "N": "0.40" },
          "event_type": { "S": "entry" },
          "timestamp": { "N": "1777672800001" }
        }
      }
    },
    {
      "eventName": "INSERT",
      "dynamodb": {
        "NewImage": {
          "vehicle_id": { "S": "HIGH-TEST-STREAM" },
          "plate_text": { "S": "HIGH-TEST-STREAM" },
          "confidence": { "N": "0.95" },
          "event_type": { "S": "entry" },
          "timestamp": { "N": "1777672800002" }
        }
      }
    }
  ]
}
EOF

aws lambda invoke \
  --function-name gateevents-stream-router \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected** (with default `ORPHAN_POLICY=review`, two stream records as above):
- `statusCode`: 200
- `processed`: 2
- `routedToValidationBacklog`: 1 (low-confidence record)
- `waitingForCounterpart`: 1 (high-confidence entry alone; no matching exit yet)
- `routedToPermitChecker` / `routedToCitationCreate`: depend on pairing, grace period, and permit outcome (see `lambda/gateevents-stream-router/response.json` for full counter list)

`NewImage` must include `timestamp` (ms) along with `vehicle_id`, `plate_text`, `confidence`, and `event_type`, or the record is skipped (`skippedInvalidPayload`).

---

### Function 9: citation-create-handler

```bash
cat > payload.json << 'EOF'
{
  "httpMethod": "POST",
  "body": {
    "vehicleId": "CIT-TEST-001",
    "plateText": "CIT-TEST-001",
    "reason": "No valid permit",
    "amount": 120,
    "issuedBy": "admin-user"
  }
}
EOF

aws lambda invoke \
  --function-name citation-create-handler \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**:
- `statusCode`: 201
- `message`: "Citation created"
- `citationId`: UUID

---

### Function 10: citation-lookup-handler

```bash
cat > payload.json << 'EOF'
{"queryStringParameters":{"plateText":"ABC-1234"}}
EOF

aws lambda invoke \
  --function-name citation-lookup-handler \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**:
- `statusCode`: 200
- Array of citation objects for the given plate, or an empty array

---

### Function 11: permit-admin-handler

**List all permits (GET)**
```bash
cat > payload.json << 'EOF'
{"httpMethod":"GET","queryStringParameters":{"limit":"10"}}
EOF

aws lambda invoke \
  --function-name permit-admin-handler \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**: `statusCode` 200, `items` array of permits, `count`

**Create a permit (POST)**
```bash
cat > payload.json << 'EOF'
{
  "httpMethod": "POST",
  "body": "{\"vehicleId\":\"TEST-9999\",\"owner\":\"Test User\",\"expiryDate\":\"2026-12-31\"}"
}
EOF

aws lambda invoke \
  --function-name permit-admin-handler \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**: `statusCode` 201, `permit` object with `permitStatus: "VALID"`

**Update a permit (PUT)**
```bash
cat > payload.json << 'EOF'
{
  "httpMethod": "PUT",
  "body": "{\"vehicleId\":\"TEST-9999\",\"status\":\"REVOKED\"}"
}
EOF

aws lambda invoke \
  --function-name permit-admin-handler \
  --cli-binary-format raw-in-base64-out \
  --payload file://payload.json \
  --region us-west-2 \
  response.json

cat response.json
```

**Expected**: `statusCode` 200, updated `permit` object

---

## Verify All Functions Deployed

```bash
aws lambda list-functions \
  --region us-west-2 \
  --query 'Functions[].FunctionName' \
  --output table
```

You should see:
- presigned-url-generator
- permit-checker
- permit-admin-handler
- event-retriever
- plate-submission-handler
- validation-backlog-handler
- validation-backlog-admin-handler
- gateevents-stream-router
- citation-create-handler
- s3-uploader
- citation-lookup-handler
- citation-admin-handler

---

## Quick Checklist

- [ ] presigned-url-generator returns 200 with uploadUrl
- [ ] permit-checker returns 200 for ABC-1234
- [ ] permit-checker returns 404 for INVALID-9999
- [ ] event-retriever returns 200 with event array
- [ ] plate-submission-handler returns 201
- [ ] s3-uploader returns 200 with imageUrl
- [ ] validation-backlog-handler returns 201 for low confidence
- [ ] validation-backlog-admin-handler GET returns 200 with items
- [ ] gateevents-stream-router routes records by confidence threshold
- [ ] citation-create-handler returns 201 with citationId
- [ ] citation-lookup-handler returns 200 with citations array
- [ ] citation-admin-handler GET returns 200 with items array
- [ ] citation-admin-handler PUT returns 200 for status update
- [ ] permit-admin-handler GET returns 200 with permits
- [ ] permit-admin-handler POST returns 201 for new permit
- [ ] permit-admin-handler PUT returns 200 for status update
- [ ] All 12 functions appear in list-functions

---

## Troubleshooting

**Error: "Invalid base64"**
- Use `--cli-binary-format raw-in-base64-out` flag
- Use `file://` for payloads

**Error: "Function not found"**
- Check function name spelling
- Verify region is `us-west-2`
- Run `aws lambda list-functions --region us-west-2`

**Error: "AccessDenied"**
- Lambda role doesn't have DynamoDB permissions
- Check role has: `AmazonDynamoDBFullAccess`, `CloudWatchLogsFullAccess`, `AmazonS3FullAccess`

**Response shows error in body**
- Check response.json for error details
- Look at CloudWatch logs: `aws logs tail /aws/lambda/FUNCTION_NAME --follow --region us-west-2`
