/**
 * Student management view.
 *
 * Talks to the management API through ``apiClient``:
 *  - ``GET  /management/students`` (optionally filtered by ``school_id``)
 *  - ``POST /management/students``                 — enrolment form
 *  - ``POST   /management/students/{id}/avatar``   — multipart upload, field ``file``
 *  - ``DELETE /management/students/{id}/avatar``   — photo removal
 *
 * The school list (needed by the enrolment form and the filter) is fetched
 * once in ``App.jsx`` and passed down as a prop.
 */
import { useCallback, useEffect, useState } from 'react'
import apiClient, { assetUrl, extractApiError } from '../api/client'

/** Mirrors the backend default (``SCHOOLMGR_MAX_UPLOAD_BYTES``). */
const MAX_AVATAR_BYTES = 2 * 1024 * 1024
const ALLOWED_AVATAR_TYPES = ['image/png', 'image/jpeg', 'image/webp', 'image/gif']

const EMPTY_FORM = { school_id: '', first_name: '', last_name: '', grade_label: '', email: '' }

function initialsOf(student) {
  return `${student.first_name?.[0] ?? ''}${student.last_name?.[0] ?? ''}`.toUpperCase() || '?'
}

function formatDate(iso) {
  if (!iso) return '—'
  const date = new Date(iso)
  if (Number.isNaN(date.getTime())) return iso
  return date.toLocaleDateString(undefined, { year: 'numeric', month: 'short', day: 'numeric' })
}

function studentInitialsStyle(id) {
  const palette = ['#0d9488', '#4f46e5', '#b45309', '#be123c', '#15803d', '#7e22ce']
  return { backgroundColor: palette[id % palette.length] }
}

export default function Students({ schools = [], schoolsStatus = 'loading' }) {
  const [students, setStudents] = useState([])
  const [status, setStatus] = useState('loading')
  const [loadError, setLoadError] = useState(null)
  const [reloadKey, setReloadKey] = useState(0)
  const [filterSchoolId, setFilterSchoolId] = useState('')

  const [form, setForm] = useState(EMPTY_FORM)
  const [creating, setCreating] = useState(false)
  const [createError, setCreateError] = useState(null)
  const [notice, setNotice] = useState(null)

  const [uploading, setUploading] = useState({})   // { [studentId]: true }
  const [avatarErrors, setAvatarErrors] = useState({})

  const schoolNames = new Map(schools.map((school) => [school.id, school.name]))
  const canCreate = schools.length > 0

  /* ------------------------------------------------------------ fetching */

  useEffect(() => {
    const controller = new AbortController()
    let alive = true
    apiClient
      .get('/management/students', {
        params: filterSchoolId ? { school_id: filterSchoolId } : undefined,
        signal: controller.signal,
      })
      .then(({ data }) => {
        if (!alive) return
        setStudents(data)
        setLoadError(null)
        setStatus('ready')
      })
      .catch((err) => {
        if (!alive || err.code === 'ERR_CANCELED') return
        setLoadError(extractApiError(err, 'Could not load the student registry.'))
        setStatus('error')
      })
    return () => {
      alive = false
      controller.abort()
    }
  }, [filterSchoolId, reloadKey])

  /** Re-run the fetch; flips the view to its loading state from the event handler. */
  const reload = useCallback(() => {
    setStatus('loading')
    setReloadKey((key) => key + 1)
  }, [])

  // Success flashes are advisory — fade them out after a few seconds.
  useEffect(() => {
    if (!notice) return undefined
    const timer = setTimeout(() => setNotice(null), 5000)
    return () => clearTimeout(timer)
  }, [notice])

  const upsertStudent = useCallback((student) => {
    setStudents((prev) => {
      const index = prev.findIndex((row) => row.id === student.id)
      if (index === -1) return [student, ...prev]
      const next = prev.slice()
      next[index] = student
      return next
    })
  }, [])

  /* ------------------------------------------------------------ creating */

  function setField(field) {
    return (event) => {
      const value = event.target.value
      setForm((prev) => ({ ...prev, [field]: value }))
      if (createError) setCreateError(null)
    }
  }

  async function handleCreate(event) {
    event.preventDefault()
    if (creating) return
    if (!form.school_id || !form.first_name.trim() || !form.last_name.trim()) {
      setCreateError('School, first name and last name are required.')
      return
    }
    const payload = {
      school_id: Number(form.school_id),
      first_name: form.first_name.trim(),
      last_name: form.last_name.trim(),
      grade_label: form.grade_label.trim() || null,
      email: form.email.trim() || null,
    }

    setCreating(true)
    setCreateError(null)
    try {
      const { data } = await apiClient.post('/management/students', payload)
      upsertStudent(data)
      setForm((prev) => ({ ...EMPTY_FORM, school_id: prev.school_id }))
      setNotice(`${data.full_name} enrolled in ${schoolNames.get(data.school_id) ?? `school #${data.school_id}`}.`)
    } catch (err) {
      setCreateError(extractApiError(err, 'Could not create the student record.'))
    } finally {
      setCreating(false)
    }
  }

  /* ------------------------------------------------------- avatar upload */

  function setAvatarBusy(studentId, busy) {
    setUploading((prev) => {
      const next = { ...prev }
      if (busy) next[studentId] = true
      else delete next[studentId]
      return next
    })
  }

  function setAvatarError(studentId, message) {
    setAvatarErrors((prev) => {
      const next = { ...prev }
      if (message) next[studentId] = message
      else delete next[studentId]
      return next
    })
  }

  async function handleAvatarSelect(student, file) {
    if (!file) return
    setAvatarError(student.id, null)
    if (!ALLOWED_AVATAR_TYPES.includes(file.type)) {
      setAvatarError(student.id, 'Only PNG, JPEG, WebP or GIF images are accepted.')
      return
    }
    if (file.size > MAX_AVATAR_BYTES) {
      setAvatarError(student.id, 'Image exceeds the 2 MiB upload limit.')
      return
    }

    const body = new FormData()
    body.append('file', file, file.name)
    setAvatarBusy(student.id, true)
    try {
      const { data } = await apiClient.post(`/management/students/${student.id}/avatar`, body)
      upsertStudent(data)
      setNotice(`Avatar updated for ${data.full_name}.`)
    } catch (err) {
      setAvatarError(student.id, extractApiError(err, 'Avatar upload failed.'))
    } finally {
      setAvatarBusy(student.id, false)
    }
  }

  async function handleAvatarRemove(student) {
    setAvatarError(student.id, null)
    setAvatarBusy(student.id, true)
    try {
      const { data } = await apiClient.delete(`/management/students/${student.id}/avatar`)
      upsertStudent(data)
      setNotice(`Avatar removed for ${data.full_name}.`)
    } catch (err) {
      setAvatarError(student.id, extractApiError(err, 'Could not remove the avatar.'))
    } finally {
      setAvatarBusy(student.id, false)
    }
  }

  /* ------------------------------------------------------------ rendering */

  return (
    <section className="page">
      {notice && (
        <div className="alert alert-success" role="status">
          {notice}
        </div>
      )}

      <div className="card create-card">
        <header className="card-header">
          <div>
            <h2>Enrol a student</h2>
            <p>Creates a record via <code>POST /management/students</code>.</p>
          </div>
        </header>

        {!canCreate && (
          <p className="muted pad">
            {schoolsStatus === 'loading'
              ? 'Loading schools…'
              : 'No schools available — a student must belong to a school before it can be created.'}
          </p>
        )}

        <form className="student-form" onSubmit={handleCreate} noValidate>
          <div className="field">
            <label htmlFor="student-school">School</label>
            <select
              id="student-school"
              value={form.school_id}
              onChange={setField('school_id')}
              disabled={creating || !canCreate}
              required
            >
              <option value="">Select a school…</option>
              {schools.map((school) => (
                <option key={school.id} value={school.id}>
                  {school.name} — {school.code}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="student-first-name">First name</label>
            <input
              id="student-first-name"
              type="text"
              maxLength={80}
              placeholder="Ada"
              value={form.first_name}
              onChange={setField('first_name')}
              disabled={creating}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="student-last-name">Last name</label>
            <input
              id="student-last-name"
              type="text"
              maxLength={80}
              placeholder="Lovelace"
              value={form.last_name}
              onChange={setField('last_name')}
              disabled={creating}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="student-grade">Grade</label>
            <input
              id="student-grade"
              type="text"
              maxLength={32}
              placeholder="e.g. 6A"
              value={form.grade_label}
              onChange={setField('grade_label')}
              disabled={creating}
            />
          </div>
          <div className="field">
            <label htmlFor="student-email">Email (optional)</label>
            <input
              id="student-email"
              type="email"
              maxLength={254}
              placeholder="ada@example.com"
              value={form.email}
              onChange={setField('email')}
              disabled={creating}
            />
          </div>
          <div className="field field-action">
            <label aria-hidden="true">&nbsp;</label>
            <button type="submit" className="btn btn-primary" disabled={creating || !canCreate}>
              {creating ? (
                <>
                  <span className="spinner" aria-hidden="true" /> Creating…
                </>
              ) : (
                'Create student'
              )}
            </button>
          </div>
        </form>

        {createError && (
          <div className="alert alert-error" role="alert">
            <strong>Student not created.</strong> {createError}
          </div>
        )}
      </div>

      <div className="card">
        <header className="card-header">
          <div>
            <h2>Students</h2>
            <p>Registry served by <code>GET /management/students</code>.</p>
          </div>
          <div className="table-toolbar">
            <label className="filter-label" htmlFor="school-filter">
              School
            </label>
            <select
              id="school-filter"
              value={filterSchoolId}
              onChange={(event) => {
                setStatus('loading')
                setFilterSchoolId(event.target.value)
              }}
            >
              <option value="">All schools</option>
              {schools.map((school) => (
                <option key={school.id} value={school.id}>
                  {school.name}
                </option>
              ))}
            </select>
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              onClick={reload}
              disabled={status === 'loading'}
            >
              ↻ Refresh
            </button>
          </div>
        </header>

        {status === 'loading' && (
          <div className="table-loading" aria-live="polite" aria-busy="true">
            <span className="spinner" aria-hidden="true" /> Loading students…
          </div>
        )}

        {status === 'error' && (
          <div className="alert alert-error" role="alert">
            <strong>Could not load students.</strong> {loadError}
            <div className="alert-actions">
              <button
                type="button"
                className="btn btn-primary btn-sm"
                onClick={reload}
              >
                Try again
              </button>
            </div>
          </div>
        )}

        {status === 'ready' && students.length === 0 && (
          <div className="empty-state">
            <h3>No students found</h3>
            <p>
              {filterSchoolId
                ? 'This school has no students yet — enrol one with the form above.'
                : 'Enrol the first student with the form above.'}
            </p>
          </div>
        )}

        {status === 'ready' && students.length > 0 && (
          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th scope="col">Student</th>
                  <th scope="col">School</th>
                  <th scope="col">Grade</th>
                  <th scope="col">Status</th>
                  <th scope="col">Enrolled</th>
                  <th scope="col" className="col-actions">
                    Avatar
                  </th>
                </tr>
              </thead>
              <tbody>
                {students.map((student) => (
                  <tr key={student.id} className={avatarErrors[student.id] ? 'row-has-error' : ''}>
                    <td>
                      <div className="student-cell">
                        {student.avatar_url ? (
                          <img
                            className="avatar"
                            src={assetUrl(student.avatar_url)}
                            alt={`${student.full_name} avatar`}
                          />
                        ) : (
                          <span className="avatar avatar-fallback" style={studentInitialsStyle(student.id)} aria-hidden="true">
                            {initialsOf(student)}
                          </span>
                        )}
                        <div className="student-meta">
                          <strong>{student.full_name}</strong>
                          <span className="muted">{student.email || 'no email on file'}</span>
                        </div>
                      </div>
                      {avatarErrors[student.id] && (
                        <p className="field-error" role="alert">{avatarErrors[student.id]}</p>
                      )}
                    </td>
                    <td>{schoolNames.get(student.school_id) ?? `#${student.school_id}`}</td>
                    <td>{student.grade_label || '—'}</td>
                    <td>
                      {student.is_active ? (
                        <span className="badge badge-ok">Active</span>
                      ) : (
                        <span className="badge badge-off">Inactive</span>
                      )}
                    </td>
                    <td>{formatDate(student.created_at)}</td>
                    <td className="col-actions">
                      {uploading[student.id] ? (
                        <span className="muted inline-busy">
                          <span className="spinner" aria-hidden="true" /> Uploading…
                        </span>
                      ) : (
                        <div className="row-actions">
                          <label className="btn btn-ghost btn-sm file-btn">
                            {student.avatar_url ? 'Replace' : 'Upload'}
                            <input
                              type="file"
                              accept="image/png,image/jpeg,image/webp,image/gif"
                              onChange={(event) => {
                                const file = event.target.files?.[0]
                                event.target.value = ''
                                if (file) handleAvatarSelect(student, file)
                              }}
                            />
                          </label>
                          {student.avatar_url && (
                            <button
                              type="button"
                              className="btn btn-ghost btn-sm btn-danger-ghost"
                              onClick={() => handleAvatarRemove(student)}
                            >
                              Remove
                            </button>
                          )}
                        </div>
                      )}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
            <p className="table-caption muted">
              {students.length} student{students.length === 1 ? '' : 's'} · PNG/JPEG/WebP/GIF up to 2 MiB ·{' '}
              uploads go to <code>POST /management/students/&#123;id&#125;/avatar</code>
            </p>
          </div>
        )}
      </div>
    </section>
  )
}
