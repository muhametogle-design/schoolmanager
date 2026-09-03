/**
 * Dashboard view: renders the school registry fetched by ``App.jsx`` from
 * ``GET /management/schools``. Loading, error (with retry) and empty states are
 * all explicit — see the three ``status`` branches below.
 */
import { assetUrl } from '../api/client'

function schoolInitials(school) {
  const base = (school.code || school.name || '?').trim()
  const parts = base.split(/[\s\-_]+/).filter(Boolean)
  if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
  return base.slice(0, 2).toUpperCase()
}

function formatDate(iso) {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

export default function Dashboard({ schools = [], status = 'loading', error = null, onRetry }) {
  const withLogo = schools.filter((school) => school.logo_url).length
  const withEmail = schools.filter((school) => school.email).length

  return (
    <section className="page">
      <div className="stats-row">
        <article className="stat-tile">
          <span className="stat-label">Schools registered</span>
          <strong className="stat-value">{status === 'ready' ? schools.length : '—'}</strong>
        </article>
        <article className="stat-tile">
          <span className="stat-label">With logo</span>
          <strong className="stat-value">{status === 'ready' ? withLogo : '—'}</strong>
        </article>
        <article className="stat-tile">
          <span className="stat-label">With contact email</span>
          <strong className="stat-value">{status === 'ready' ? withEmail : '—'}</strong>
        </article>
      </div>

      <div className="card">
        <header className="card-header">
          <div>
            <h2>Schools</h2>
            <p>Records served by the management API at <code>/management/schools</code>.</p>
          </div>
          <button type="button" className="btn btn-ghost btn-sm" onClick={onRetry} disabled={status === 'loading'}>
            ↻ Refresh
          </button>
        </header>

        {status === 'loading' && (
          <div className="school-grid" aria-live="polite" aria-busy="true">
            {Array.from({ length: 3 }, (_, index) => (
              <div className="school-card skeleton-card" key={index}>
                <div className="skeleton skeleton-logo" />
                <div className="skeleton skeleton-title" />
                <div className="skeleton skeleton-line" />
                <div className="skeleton skeleton-line short" />
              </div>
            ))}
            <p className="muted center">Loading schools from the API…</p>
          </div>
        )}

        {status === 'error' && (
          <div className="alert alert-error" role="alert">
            <strong>Could not load schools.</strong> {error}
            <div className="alert-actions">
              <button type="button" className="btn btn-primary btn-sm" onClick={onRetry}>
                Try again
              </button>
            </div>
          </div>
        )}

        {status === 'ready' && schools.length === 0 && (
          <div className="empty-state">
            <h3>No schools yet</h3>
            <p>
              The API is reachable but the registry is empty. Create one with{' '}
              <code>POST /api/v1/management/schools</code> — a body like{' '}
              <code>{'{"name": "North East Elementary", "code": "NE-ES"}'}</code>.
            </p>
          </div>
        )}

        {status === 'ready' && schools.length > 0 && (
          <div className="school-grid">
            {schools.map((school) => (
              <article className="school-card" key={school.id}>
                <header>
                  {school.logo_url ? (
                    <img className="school-logo" src={assetUrl(school.logo_url)} alt={`${school.name} logo`} />
                  ) : (
                    <span className="school-logo school-logo-fallback" aria-hidden="true">
                      {schoolInitials(school)}
                    </span>
                  )}
                  <div className="school-heading">
                    <h3 title={school.name}>{school.name}</h3>
                    <span className="badge badge-code">{school.code}</span>
                  </div>
                </header>
                <dl>
                  <div>
                    <dt>Address</dt>
                    <dd>{school.address || '—'}</dd>
                  </div>
                  <div>
                    <dt>Email</dt>
                    <dd>
                      {school.email ? (
                        <a href={`mailto:${school.email}`}>{school.email}</a>
                      ) : (
                        '—'
                      )}
                    </dd>
                  </div>
                  <div>
                    <dt>Added</dt>
                    <dd>{formatDate(school.created_at)}</dd>
                  </div>
                </dl>
                <footer>
                  <span className="muted">School ID #{school.id}</span>
                  <span className="badge badge-ok">Active</span>
                </footer>
              </article>
            ))}
          </div>
        )}
      </div>
    </section>
  )
}
