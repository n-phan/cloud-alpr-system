# ALPR Parking System - Frontend

React + Vite frontend for automated license plate recognition.

## Quick Start

```bash
npm install
npm run dev
```

Open `http://localhost:5173`

---

## Environment Variables

Create `.env.local`:
```
VITE_COGNITO_REGION=us-west-2
VITE_COGNITO_USER_POOL_ID=us-west-2_xxxxxxxxxxxxx
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxxxxxxxxxxxxx
VITE_API_ENDPOINT=http://localhost:3001
```

---

## Components

### ImageUpload
**Test**: Click "Upload Image" tab
- Drag/drop an image or click to select
- Image preview displays
- Click "Upload & Analyze"
- See mock result card (plate: ABC-1234, confidence: 98%, status: VALID)

### PermitDashboard
**Test**: Click "Check Permit" tab
- Enter vehicle ID: `ABC-1234`, `XYZ-5678`, or `DEF-9012`
- Press Enter or click "Lookup"
- See permit card with owner name and status

### EventLogStaff
**Test**: Staff Dashboard → "Recent Events" tab
- Shows table: Time, Vehicle ID, Plate, Permit Status, Event Type
- NO Confidence column (staff can't see)
- Type in filter box to search by vehicle ID or plate

### EventLogAdmin
**Test**: Admin Dashboard → Events table
- Shows all columns INCLUDING Confidence (%)
- "View Event" button in each row
- Click "View Event" → Modal pops up with event details + image placeholder
- Filter same as staff version

### Login
**Test**: Sign in/out flow
- Test User: `newuser@example.com` / `Test123!@`
- Admin User: `admin@example.com` / `Admin123!@`
- Sign in → redirects to dashboard
- Sign out → redirects to login

### Dashboard (Staff)
**Test**: `/dashboard`
- 3 tabs: Upload Image, Check Permit, Recent Events
- No "Admin" badge in header

### Admin
**Test**: `/admin`
- Shows "Admin" badge in header
- Advanced event table with confidence + View Event button
- Try accessing `/admin` as non-admin → redirects to dashboard

---

## File Structure

```
src/
├── components/
│   ├── ImageUpload.jsx
│   ├── PermitDashboard.jsx
│   ├── EventLogStaff.jsx
│   ├── EventLogAdmin.jsx
│   └── ProtectedRoute.jsx
├── pages/
│   ├── Login.jsx
│   ├── Dashboard.jsx
│   └── Admin.jsx
├── services/
│   ├── auth.js
│   └── api.js
├── styles/
│   └── [CSS files]
└── App.jsx
```

---

## Test Users

```
Staff:   newuser@example.com / Test123!@
Admin:   admin@example.com / Admin123!@
```

---

## Mock Data

**Permit Status**:
- `ABC-1234` → VALID
- `XYZ-5678` → EXPIRED
- `DEF-9012` → VALID

**Events**: 4 mock events auto-generated
