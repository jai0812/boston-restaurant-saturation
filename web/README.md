# Web dashboard

Next.js 14 (App Router) + Tailwind + MapLibre + Recharts + SWR. Talks to the
FastAPI service in `../app/api.py`.

## Run

```bash
# 1. backend
cd ..
uvicorn app.api:app --port 8000 --reload

# 2. web
cd web
npm install
npm run dev
# open http://localhost:3000
```

`next.config.js` rewrites `/api/*` → `http://127.0.0.1:8000/*` so the client has no CORS to deal with.
