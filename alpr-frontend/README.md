# ALPR Parking System — Frontend

React + Vite frontend for automated license plate recognition, served via CloudFront → S3.

---

## Local Development

```bash
npm install
npm run dev
```

Open `http://localhost:5173`

### Environment Variables

Create `.env.local` in the project root:

```
VITE_COGNITO_REGION=us-west-2
VITE_COGNITO_USER_POOL_ID=us-west-2_xxxxxxxxxxxxx
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxx
VITE_API_ENDPOINT=https://o5h6jttjtc.execute-api.us-west-2.amazonaws.com/prod
```

---

## Deployment

The Makefile handles building and deploying to S3 + CloudFront in one command.

| Command | Description |
|---|---|
| `make deploy` | Vite build → sync to S3 → invalidate CloudFront cache |
| `make build` | Vite build only (outputs to `dist/`) |

### Deploy

```bash
make deploy
```

This runs three steps:
1. `npm run build` — compiles the app into `dist/`
2. `aws s3 sync dist/ s3://alpr-frontend-static-cmpe281/ --delete` — uploads changed files, removes deleted ones
3. `aws cloudfront create-invalidation --paths "/*"` — purges the CDN cache so users get the new build immediately

**Prerequisites**: AWS CLI configured with credentials that have S3 write and CloudFront invalidation permissions.

### Build Only

```bash
make build
```

Useful for verifying the production build locally before pushing. Serve it with:

```bash
npm run preview
```

---

## Routes

| Path | Access | Description |
|---|---|---|
| `/` | Public | Citation lookup by license plate + permit status |
| `/login` | Public | Staff / Admin login (redirects to `/dashboard` if already signed in) |
| `/dashboard` | Staff + Admin | Image upload, validation backlog, recent events |
| `/admin` | Admin only | Full event log with confidence scores |

---

## Pages & Components

### Citations (`/`) — Public
- Search for citations by license plate
- Displays permit status alongside citation results, even when no citations are found
- "Staff / Admin Login" link at the bottom navigates to `/login`

### Login (`/login`)
- Email + password sign-in via Cognito
- Test credentials:
  ```
  Staff: newuser@example.com / Test123!@
  Admin: admin@example.com  / Admin123!@
  ```
- Successful login redirects to `/dashboard`

### Dashboard (`/dashboard`) — Staff + Admin
Three tabs:

**Upload Image**
- Drag-and-drop or click to select multiple images
- Images are validated before upload: must be a real image file, ≤ 10 MB, and at least 100×100 px
- Each file is processed independently — status shown per card (Ready → Processing → Done / Failed)
- On success each card confirms the image was uploaded and queued for processing

**Validation Backlog**
- Lists low-confidence uploads queued for manual review from the `ValidationBacklog` DynamoDB table
- Filter by status: Pending / Approved / Rejected
- Each card shows the captured image, plate text, confidence bar, and metadata
- Pending items can be approved or rejected with optional notes
- Admin users can re-review already-approved or rejected items to correct a prior decision
- Actioning a card removes it from the current view immediately

**Recent Events**
- Live event table (auto-refreshes every 10 seconds)
- Columns: Time, Vehicle ID, Plate Text, Permit Status, Event Type
- "View Event" button opens a detail modal per row
- Filter by vehicle ID or plate text

### Admin (`/admin`) — Admin only
- Summary cards row showing Total Events, Valid Permits, Expired/Revoked, and Pending Validation (auto-refreshes every 30 s)
- Three tabs:
  - **Event Log** — full event table with Confidence column, filter by vehicle ID or plate
  - **Permit Management** — table of all permits with Activate/Revoke actions, inline editing of owner and expiry date, and an Add Permit form
  - **Citations** — table of all citations with status filter (All / Issued / Paid / Disputed / Voided) and inline status update with optional notes
- Header badge toggles between **Admin** (navigates to `/admin`) and **Dashboard** (navigates to `/dashboard`) depending on current page

---

## File Structure

```
src/
├── components/
│   ├── ImageUpload.jsx        — multi-file upload with validation
│   ├── ValidationBacklog.jsx  — manual review queue for low-confidence images
│   ├── EventLogStaff.jsx      — event table for staff (with View Event modal)
│   ├── EventLogAdmin.jsx      — event table for admins (adds Confidence column)
│   ├── AdminSummaryCards.jsx  — stat cards for the admin dashboard
│   ├── PermitManager.jsx      — permit list with add, edit, activate, and revoke
│   ├── CitationManager.jsx    — citation list with status filter and inline status update
│   └── ProtectedRoute.jsx     — auth guard for protected routes
├── pages/
│   ├── Citations.jsx          — public citation + permit lookup
│   ├── Login.jsx              — Cognito sign-in
│   ├── Dashboard.jsx          — staff dashboard (tabbed)
│   └── Admin.jsx              — admin dashboard
├── services/
│   ├── auth.js                — Cognito auth helpers
│   └── api.js                 — API Gateway client (axios)
├── styles/
│   └── [CSS files]
└── App.jsx                    — routing + auth state + header
```

---

## Test Users

```
Staff:  newuser@example.com / Test123!@
Admin:  admin@example.com   / Admin123!@
```

Both must be verified in Cognito before use.

---

