# ALPR Parking System - Frontend MVP

React + Vite frontend for the Automated License Plate Recognition parking system.

## Quick Start

```bash
npm install
npm run dev
```

Open `http://localhost:5173`

---

## Components & Testing

### ImageUpload
**Test**: Click "Upload Image" tab
- Drag/drop an image or click to select
- Click "Upload & Analyze"
- Should see mock result card

### PermitDashboard
**Test**: Click "Check Permit" tab
- Enter vehicle ID: `ABC-1234`, `XYZ-5678`, or `DEF-9012`
- Press Enter or click "Lookup"
- Should see permit card with owner & status

### EventLog (Coming Soon)

---

## Environment Variables

Create `.env.local`:
```
VITE_COGNITO_REGION=us-west-2
VITE_COGNITO_USER_POOL_ID=us-west-2_xxxxx
VITE_COGNITO_CLIENT_ID=xxxxxxxxxxxxx
VITE_API_ENDPOINT=http://localhost:3001
```

---

## File Structure

```
src/
├── components/
│   ├── ImageUpload.jsx
│   ├── PermitDashboard.jsx
│   └── EventLog.jsx (coming soon)
├── services/
│   ├── auth.js
│   └── api.js
├── styles/
│   ├── App.css
│   ├── ImageUpload.css
│   └── PermitDashboard.css
└── App.jsx
```

---

## Next Steps

- Build EventLog component
- Build Login page
- Add routing