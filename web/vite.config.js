import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Origin of the FastAPI backend used by the dev/preview-server proxies below.
// By default the app talks to the absolute ``VITE_API_BASE_URL`` from
// .env.local. Setting ``VITE_API_BASE_URL=/api/v1`` instead routes every API
// request (and the /static uploads served by FastAPI) through this proxy,
// which sidesteps CORS during local development.
const DEV_API_TARGET = 'http://127.0.0.1:8000'

const proxy = {
  '/api/v1': { target: DEV_API_TARGET, changeOrigin: true },
  '/static': { target: DEV_API_TARGET, changeOrigin: true },
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  // allowedHosts: true — the dev/preview server also runs behind the sandbox
  // preview proxy, which uses non-localhost host names.
  server: { host: true, allowedHosts: true, proxy },
  preview: { host: true, allowedHosts: true, proxy },
})
