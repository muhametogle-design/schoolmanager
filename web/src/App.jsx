/**
 * NE-ES School Management Dashboard — application root.
 *
 * Replaces the default Vite starter UI with the real product shell:
 *  - routing via ``react-router-dom`` (``/login`` plus a protected area with
 *    the ``/`` dashboard and ``/students`` management view);
 *  - the dashboard layout itself: sidebar navigation, top bar with the signed-in
 *    user and sign-out action;
 *  - the school registry is fetched **once here** from
 *    ``GET /management/schools`` through ``web/src/api/client.js`` and passed
 *    to the Dashboard (rendering) and Students (school selector) views, with
 *    explicit loading / error / retry states.
 */
import { useCallback, useEffect, useState } from 'react'
import {
  BrowserRouter,
  NavLink,
  Navigate,
  Route,
  Routes,
  useLocation,
  useNavigate,
} from 'react-router-dom'
import apiClient, {
  API_BASE_URL,
  clearSession,
  extractApiError,
  getStoredUser,
  getToken,
} from './api/client'
import Dashboard from './components/Dashboard'
import Login from './components/Login'
import Students from './components/Students'

/** Gate for the authenticated area: bounce anonymous visitors to /login. */
function RequireAuth({ children }) {
  const location = useLocation()
  if (!getToken()) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }
  return children
}

function initialsOf(user) {
  const name = user?.full_name || user?.username || '?'
  const parts = name.trim().split(/\s+/)
  return ((parts[0]?.[0] ?? '') + (parts[1]?.[0] ?? '')).toUpperCase() || '?'
}

/**
 * Protected shell: layout + the shared schools fetch.
 */
function Shell() {
  const navigate = useNavigate()
  const location = useLocation()
  const user = getStoredUser()

  const [schools, setSchools] = useState([])
  const [schoolsStatus, setSchoolsStatus] = useState('loading')
  const [schoolsError, setSchoolsError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)

  // Fetch the school registry on mount and whenever ``reloadKey`` changes.
  // Only promise callbacks touch state, so the effect never re-renders
  // synchronously; the ``loading`` status comes from initial state / reload().
  useEffect(() => {
    const controller = new AbortController()
    let alive = true
    apiClient
      .get('/management/schools', { signal: controller.signal })
      .then(({ data }) => {
        if (!alive) return
        setSchools(data)
        setSchoolsError(null)
        setSchoolsStatus('ready')
      })
      .catch((err) => {
        if (!alive || err.code === 'ERR_CANCELED') return
        setSchoolsError(extractApiError(err, 'Could not load the school registry.'))
        setSchoolsStatus('error')
      })
    return () => {
      alive = false
      controller.abort()
    }
  }, [reloadKey])

  const reloadSchools = useCallback(() => {
    setSchoolsStatus('loading')
    setReloadKey((key) => key + 1)
  }, [])

  function handleLogout() {
    clearSession()
    navigate('/login', { replace: true })
  }

  const isStudents = location.pathname.startsWith('/students')

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <span className="brand-mark">NE‑ES</span>
          <span className="brand-name">
            School Management
            <small>Dashboard</small>
          </span>
        </div>

        <nav className="side-nav" aria-label="Primary">
          <NavLink to="/" end className={({ isActive }) => (isActive ? 'active' : '')}>
            <span className="nav-icon" aria-hidden="true">▦</span> Dashboard
          </NavLink>
          <NavLink to="/students" className={({ isActive }) => (isActive ? 'active' : '')}>
            <span className="nav-icon" aria-hidden="true">☺</span> Students
          </NavLink>
        </nav>

        <footer className="sidebar-footer">
          <span className="muted">API</span>
          <code className="api-target" title={API_BASE_URL}>
            {API_BASE_URL}
          </code>
        </footer>
      </aside>

      <div className="content">
        <header className="topbar">
          <div>
            <h1>{isStudents ? 'Student management' : 'Schools overview'}</h1>
            <p className="muted">
              {isStudents
                ? 'Enrol students and manage their avatar photos.'
                : 'Every school registered in the NE-ES network.'}
            </p>
          </div>
          <div className="user-zone">
            <span className="avatar avatar-fallback" style={{ backgroundColor: '#0d9488' }} aria-hidden="true">
              {initialsOf(user)}
            </span>
            <span className="user-meta">
              <strong>{user?.full_name || user?.username || 'Signed in'}</strong>
              {user?.role && <span className="badge badge-role">{user.role}</span>}
            </span>
            <button type="button" className="btn btn-ghost btn-sm" onClick={handleLogout}>
              Sign out
            </button>
          </div>
        </header>

        <main className="page-scroll">
          <Routes>
            <Route
              path="/"
              element={
                <Dashboard
                  schools={schools}
                  status={schoolsStatus}
                  error={schoolsError}
                  onRetry={reloadSchools}
                />
              }
            />
            <Route
              path="/students"
              element={<Students schools={schools} schoolsStatus={schoolsStatus} />}
            />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route
          path="/*"
          element={
            <RequireAuth>
              <Shell />
            </RequireAuth>
          }
        />
      </Routes>
    </BrowserRouter>
  )
}
