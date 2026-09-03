/**
 * Login screen for the NE-ES School Management dashboard.
 *
 * Posts the credentials to ``POST /auth/login`` (see ``app/api/auth.py``),
 * persists the JWT access token (+ user profile) via the helpers in
 * ``web/src/api/client.js`` and redirects to the originally requested route.
 * Failures (wrong password, unreachable backend, missing endpoint) surface as
 * an inline alert; the form stays usable for a retry.
 */
import { useState } from 'react'
import { Navigate, useLocation, useNavigate } from 'react-router-dom'
import apiClient, {
  extractApiError,
  isAuthenticated,
  saveSession,
} from '../api/client'

export default function Login() {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)

  const navigate = useNavigate()
  const location = useLocation()
  const from = location.state?.from?.pathname || '/'

  // Already signed in? Never show the form.
  if (isAuthenticated()) {
    return <Navigate to={from} replace />
  }

  async function handleSubmit(event) {
    event.preventDefault()
    if (submitting) return
    const identifier = username.trim()
    if (!identifier || !password) {
      setError('Enter your username (or email) and password.')
      return
    }

    setSubmitting(true)
    setError(null)
    try {
      const { data } = await apiClient.post('/auth/login', {
        username: identifier,
        password,
      })
      saveSession(data.access_token, data.user ?? null, data.expires_in ?? 0)
      navigate(from, { replace: true })
    } catch (err) {
      setSubmitting(false)
      setError(
        extractApiError(err, 'Login failed. Please check your credentials and try again.'),
      )
    }
  }

  return (
    <div className="auth-page">
      <aside className="auth-brand" aria-hidden="true">
        <div className="auth-brand-inner">
          <span className="brand-mark">NE‑ES</span>
          <h1>
            School Management
            <span>Dashboard</span>
          </h1>
          <p>
            Enrolment, student records, photo uploads and finance for every
            school in the network — behind one secure sign-in.
          </p>
          <ul>
            <li>School and student registries</li>
            <li>Avatar &amp; logo uploads</li>
            <li>JWT-secured API access</li>
          </ul>
        </div>
      </aside>

      <main className="auth-panel">
        <form className="auth-card" onSubmit={handleSubmit} noValidate>
          <header>
            <h2>Sign in</h2>
            <p>Use your staff account to access the dashboard.</p>
          </header>

          {error && (
            <div className="alert alert-error" role="alert">
              <strong>Could not sign in.</strong> {error}
            </div>
          )}

          <div className="field">
            <label htmlFor="login-username">Username or email</label>
            <input
              id="login-username"
              name="username"
              type="text"
              autoComplete="username"
              placeholder="e.g. admin"
              value={username}
              maxLength={50}
              disabled={submitting}
              onChange={(event) => setUsername(event.target.value)}
            />
          </div>

          <div className="field">
            <label htmlFor="login-password">Password</label>
            <div className="password-row">
              <input
                id="login-password"
                name="password"
                type={showPassword ? 'text' : 'password'}
                autoComplete="current-password"
                placeholder="••••••••"
                value={password}
                maxLength={128}
                disabled={submitting}
                onChange={(event) => setPassword(event.target.value)}
              />
              <button
                type="button"
                className="btn btn-ghost btn-sm"
                onClick={() => setShowPassword((visible) => !visible)}
              >
                {showPassword ? 'Hide' : 'Show'}
              </button>
            </div>
          </div>

          <button type="submit" className="btn btn-primary btn-block" disabled={submitting}>
            {submitting ? (
              <>
                <span className="spinner" aria-hidden="true" /> Signing in…
              </>
            ) : (
              'Sign in'
            )}
          </button>

          <footer>
            Requires the API server — <code>uvicorn app.main:app --port 8000</code>
          </footer>
        </form>
      </main>
    </div>
  )
}
