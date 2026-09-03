# NE-ES School Management — Web Frontend

React + Vite frontend for the NE-ES School Management System. It replaces the
Vite starter UI with the dashboard that talks to the FastAPI backend
(`app/` at the repo root).

## Stack

| Concern   | Choice                                          |
| --------- | ----------------------------------------------- |
| Framework | React 19 + Vite 8                                |
| Routing   | `react-router-dom` v7                            |
| HTTP      | `axios` — one configured instance in `src/api/client.js` |
| Lint      | `oxlint` (`.oxlintrc.json`)                      |

## Getting started

```bash
npm install
cp .env.example .env.local   # adjust VITE_API_BASE_URL if the API is elsewhere
npm run dev                  # requires the backend on :8000 (see repo README)
```

`VITE_API_BASE_URL` is the only configuration the client needs — defaults to
`http://127.0.0.1:8000/api/v1`. If the backend does not send CORS headers, set
`VITE_API_BASE_URL=/api/v1` instead: `vite.config.js` proxies `/api/v1` and
`/static` to `http://127.0.0.1:8000`, so the browser stays same-origin.

## Layout

```
src/
  api/client.js        axios instance: base URL, JWT request interceptor,
                       401 → clear session + redirect, error + asset-URL helpers
  components/Login.jsx     POST /auth/login, persists token in localStorage
  components/Dashboard.jsx school registry grid (GET /management/schools)
  components/Students.jsx  table + enrolment form + avatar uploads
                           (POST/DELETE /management/students/{id}/avatar)
  App.jsx                router, auth guard and dashboard layout (sidebar/topbar)
  index.css              dashboard design system
```

## Auth model

`POST /auth/login` returns `{access_token, expires_in, user}`. The token is
stored under `localStorage` (`schoolmanager.accessToken`); every request made
through `apiClient` gets an `Authorization: Bearer …` header automatically and
any `401` from the API clears the session and redirects to `/login`.

## QA

```bash
npm run lint    # oxlint
npm run build   # production bundle
```
