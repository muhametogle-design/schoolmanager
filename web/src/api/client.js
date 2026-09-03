/**
 * Axios API client for the NE-ES School Management backend.
 *
 * Responsibilities:
 *  - single place where the backend base URL is configured
 *    (``VITE_API_BASE_URL``, defaulting to the local uvicorn instance);
 *  - automatic ``Authorization: Bearer <jwt>`` injection on every request via
 *    a request interceptor, reading the token persisted at login;
 *  - global handling of expired/invalid sessions (401 responses clear the
 *    stored session and send the browser back to ``/login``);
 *  - small localStorage helpers so auth state lives in exactly one module;
 *  - helpers to translate FastAPI error payloads into readable messages and
 *    to resolve backend-relative asset URLs (student avatars, school logos)
 *    served by the ``/static`` mount.
 */
import axios from 'axios'

const TOKEN_STORAGE_KEY = 'schoolmanager.accessToken'
const USER_STORAGE_KEY = 'schoolmanager.user'
const EXPIRES_AT_STORAGE_KEY = 'schoolmanager.tokenExpiresAt'

/** Base URL of the JSON API, including the ``/api/v1`` prefix. */
export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || 'http://127.0.0.1:8000/api/v1'

/* ------------------------------------------------------------------ session */

/** Persisted JWT access token, or ``null`` when signed out. */
export function getToken() {
  try {
    return window.localStorage.getItem(TOKEN_STORAGE_KEY)
  } catch {
    return null
  }
}

/** User profile stored alongside the token (see ``POST /auth/login``). */
export function getStoredUser() {
  try {
    const raw = window.localStorage.getItem(USER_STORAGE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

/**
 * Store a successful login result.
 *
 * @param {string} accessToken JWT returned as ``access_token``.
 * @param {object|null} user  safe user profile returned as ``user``.
 * @param {number} [expiresInSeconds] optional ``expires_in`` hint; when
 *   present the session is treated as expired locally once it lapses.
 */
export function saveSession(accessToken, user = null, expiresInSeconds = 0) {
  try {
    window.localStorage.setItem(TOKEN_STORAGE_KEY, accessToken)
    if (user) {
      window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(user))
    }
    if (Number.isFinite(expiresInSeconds) && expiresInSeconds > 0) {
      window.localStorage.setItem(
        EXPIRES_AT_STORAGE_KEY,
        String(Date.now() + expiresInSeconds * 1000),
      )
    } else {
      window.localStorage.removeItem(EXPIRES_AT_STORAGE_KEY)
    }
  } catch {
    /* storage unavailable (private mode, quota) — session stays in memory only */
  }
}

/** Drop token, user profile and expiry bookkeeping. */
export function clearSession() {
  try {
    window.localStorage.removeItem(TOKEN_STORAGE_KEY)
    window.localStorage.removeItem(USER_STORAGE_KEY)
    window.localStorage.removeItem(EXPIRES_AT_STORAGE_KEY)
  } catch {
    /* ignore — nothing we can do if storage is inaccessible */
  }
}

/** ``true`` when a token exists and has not passed its local expiry hint. */
export function isAuthenticated() {
  if (!getToken()) return false
  try {
    const expiresAt = window.localStorage.getItem(EXPIRES_AT_STORAGE_KEY)
    if (expiresAt && Date.now() >= Number(expiresAt)) {
      clearSession()
      return false
    }
  } catch {
    /* no expiry info — treat the token as valid */
  }
  return true
}

/* -------------------------------------------------------------------- axios */

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 20000,
  headers: { Accept: 'application/json' },
})

// Attach the JWT to every outgoing request (kept out of React so uploads and
// background refreshes are authorised too).
apiClient.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// A 401 on any authenticated call means the session is no longer usable:
// discard it and route to the login screen. A 401 *during* login is handled by
// the form itself (wrong credentials), so that request is skipped here.
apiClient.interceptors.response.use(
  (response) => response,
  (error) => {
    const status = error.response?.status
    const url = String(error.config?.url ?? '')
    const isLoginAttempt = url.includes('/auth/login')
    if (status === 401 && !isLoginAttempt && getToken()) {
      clearSession()
      if (window.location.pathname !== '/login') {
        window.location.assign('/login')
      }
    }
    return Promise.reject(error)
  },
)

/* ------------------------------------------------------------------ helpers */

/**
 * Convert an Axios error (or a network failure) into a human-readable string,
 * preferring FastAPI's ``detail`` field.
 */
export function extractApiError(error, fallback = 'Request failed. Please try again.') {
  if (error?.response) {
    const { status, data } = error.response
    const detail = data?.detail
    if (typeof detail === 'string' && detail.trim()) {
      return detail
    }
    if (Array.isArray(detail) && detail.length > 0) {
      const first = detail[0]
      if (typeof first === 'string') return first
      if (first && typeof first === 'object') {
        const field = Array.isArray(first.loc)
          ? first.loc.filter((part) => part !== 'body').join('.')
          : ''
        const message = String(first.msg ?? '').replace(/^Value error,\s*/, '')
        if (field && message) return `${field}: ${message}`
        if (message) return message
      }
    }
    switch (status) {
      case 401:
        return 'Not authorised — check your credentials or sign in again.'
      case 403:
        return 'You do not have permission for this action.'
      case 404:
        return 'API endpoint not found (404). Is the backend running and up to date?'
      case 413:
        return 'The uploaded file is larger than the server limit.'
      default:
        return status >= 500
          ? 'The API server had a problem handling this request.'
          : fallback
    }
  }
  if (error?.code === 'ECONNABORTED') {
    return 'The API request timed out.'
  }
  return `Cannot reach the API server at ${API_BASE_URL}. Start it with: uvicorn app.main:app --port 8000`
}

/**
 * Resolve a backend-relative asset path (e.g. ``/static/uploads/avatars/x.png``)
 * against the API origin, so <img> tags load from :8000 and not the Vite host.
 */
export function assetUrl(path) {
  if (!path) return null
  if (/^https?:\/\//i.test(path)) return path
  try {
    const apiOrigin = new URL(API_BASE_URL, window.location.origin).origin
    return new URL(path, apiOrigin).toString()
  } catch {
    return path
  }
}

export default apiClient
