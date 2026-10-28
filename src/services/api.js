const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

// Login tokens live in httpOnly cookies that the server sets for requests
// carrying X-Auth-Mode: cookie, so no script on the page (or an XSS) can read
// them. This flag only remembers that a session exists, to decide whether a
// 401 is worth a refresh attempt; it is not a secret.
const SESSION_KEY = 'hms_session'
// Earlier builds stored the tokens themselves here.
const LEGACY_TOKEN_KEYS = ['access_token', 'refresh_token']

function hasSession() {
  try {
    return localStorage.getItem(SESSION_KEY) === '1'
  } catch {
    return false
  }
}

// Called after a successful sign-in or refresh; the tokens are cookies.
function setTokens() {
  localStorage.setItem(SESSION_KEY, '1')
}

function clearTokens() {
  localStorage.removeItem(SESSION_KEY)
  for (const key of LEGACY_TOKEN_KEYS) localStorage.removeItem(key)
}

try {
  for (const key of LEGACY_TOKEN_KEYS) localStorage.removeItem(key)
} catch {
  // Storage unavailable (private mode): nothing was stored either.
}

const UNSAFE_METHODS = new Set(['POST', 'PUT', 'PATCH', 'DELETE'])
let csrfToken = null

// Cookie-authenticated writes must carry the CSRF token; the CSRF cookie is
// httpOnly, so the server hands the token out from /auth/csrf/.
async function getCsrfToken(renew = false) {
  if (!csrfToken || renew) {
    const response = await fetch(`${API_BASE_URL}/auth/csrf/`, { credentials: 'include' })
    if (!response.ok) throw new Error(`CSRF token request failed (${response.status})`)
    csrfToken = (await response.json()).csrfToken
  }
  return csrfToken
}

// Patient rows some pages keep in the browser (offline saves, the patient
// portal). Hospital PCs are shared, so they never outlive the session.
export const CACHED_PATIENT_DATA_KEYS = [
  'hospitalAppointments',
  'hospitalPatients',
  'patientData',
  'patientAppointment',
  'hospitalPrescriptions',
]

export function clearCachedPatientData() {
  for (const key of CACHED_PATIENT_DATA_KEYS) {
    try {
      localStorage.removeItem(key)
    } catch {
      // Storage may be unavailable (private mode); nothing to clear.
    }
  }
}

// The hospital chosen in the hospital switcher. Sent on every request so the
// backend scopes data and role checks to it (an explicit ?hospital= wins).
function getSelectedHospitalId() {
  try {
    const saved = JSON.parse(localStorage.getItem('selectedHospital') || 'null')
    const id = saved && typeof saved === 'object' ? saved.id : saved
    return id && /^\d+$/.test(String(id)) ? String(id) : null
  } catch {
    return null
  }
}

function buildHeaders(extra = {}, body) {
  const headers = { ...extra }
  const hospitalId = getSelectedHospitalId()
  if (hospitalId && !headers['X-Hospital-ID']) {
    headers['X-Hospital-ID'] = hospitalId
  }
  if (body && !(body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  headers['X-Auth-Mode'] = 'cookie'
  return headers
}

function parseErrorDetail(body, status) {
  if (!body) return `Request failed (${status})`
  if (typeof body === 'string') return body
  // The backend wraps errors as { error: true, message, details }.
  const text = [body.message, body.detail, body.error].find(
    (value) => typeof value === 'string' && value.trim()
  )
  return text || (typeof body === 'object' ? JSON.stringify(body.details || body) : `Request failed (${status})`)
}

let refreshPromise = null

function shouldAttemptRefresh(url) {
  return ![
    '/auth/token/refresh/',
    '/auth/staff/login/',
    '/auth/staff/logout/',
    '/auth/password/reset/',
    '/auth/patient/otp/',
    '/auth/patient/email-otp/',
    '/auth/patient/login/',
    '/auth/patient/token/',
    '/auth/google/',
    '/auth/dev/',
    '/auth/register/',
  ].some((path) => url.includes(path))
}

async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      if (!hasSession()) {
        throw new Error('Session expired')
      }
      // The refresh token is sent as an httpOnly cookie; new tokens come back as cookies.
      const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
        method: 'POST',
        credentials: 'include',
        headers: {
          'Content-Type': 'application/json',
          'X-Auth-Mode': 'cookie',
          'X-CSRFToken': await getCsrfToken(),
        },
        body: '{}',
      })
      if (!response.ok) {
        throw new Error('Session expired')
      }
      setTokens()
    })().finally(() => {
      refreshPromise = null
    })
  }
  return refreshPromise
}

function failAuthSession() {
  clearTokens()
  localStorage.removeItem('user')
  localStorage.removeItem('roles')
  localStorage.removeItem('hospitals')
  localStorage.removeItem('patientLoggedIn')
  localStorage.removeItem('patient')
  clearCachedPatientData()
  window.dispatchEvent(new Event('auth:logout'))
}

// Shared request helper with consistent error handling.
async function request(url, options = {}) {
  let response
  const { headers: extraHeaders, _retried = false, _csrfRetried = false, timeout = 8000, ...rest } = options
  const headers = buildHeaders(extraHeaders || {}, rest.body)
  const unsafe = UNSAFE_METHODS.has(String(rest.method || 'GET').toUpperCase())

  try {
    if (unsafe) headers['X-CSRFToken'] = await getCsrfToken(_csrfRetried)
    const timeoutSignal = rest.signal || AbortSignal.timeout(timeout)
    response = await fetch(url, { ...rest, headers, credentials: 'include', signal: timeoutSignal })
  } catch (networkError) {
    // fetch() only rejects when no HTTP response arrived (server down, CORS
    // blocked, timeout); its own messages ("Failed to fetch") say nothing useful.
    const timedOut = networkError.name === 'TimeoutError'
    const error = new Error(
      timedOut
        ? 'The server took too long to respond. Check whether the action completed before retrying.'
        : 'Cannot reach the server. Check that the Django backend is running and the API URL is correct.'
    )
    error.isTimeout = timedOut
    // Lets pages tell "server unreachable" apart from "server said no".
    error.isNetworkError = true
    throw error
  }

  // A cached CSRF token goes stale when the CSRF cookie rotates (e.g. after
  // signing in); fetch a fresh one and retry once.
  if (response.status === 403 && unsafe && !_csrfRetried) {
    const text = await response.clone().text()
    if (text.includes('CSRF')) {
      return request(url, { ...options, _csrfRetried: true })
    }
  }

  if (response.status === 401 && !_retried && shouldAttemptRefresh(url) && hasSession()) {
    try {
      await refreshAccessToken()
      return request(url, { ...options, _retried: true })
    } catch {
      failAuthSession()
      throw new Error('Session expired. Please sign in again.')
    }
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`
    let body = null

    try {
      body = await response.json()
      detail = parseErrorDetail(body, response.status)
    } catch (parseError) {
      // Response body was not JSON — keep the default message.
    }

    const error = new Error(detail)
    error.status = response.status
    error.body = body
    throw error
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

// Requests that wait on an email or SMS provider before the server answers.
const DELIVERY_TIMEOUT_MS = 30000

function jsonBody(data) {
  return {
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }
}

const api = {
  auth: {
    // The tokens are httpOnly cookies; this only says whether a session exists.
    getTokens: () => ({
      accessToken: hasSession() ? 'cookie' : null,
      refreshToken: hasSession() ? 'cookie' : null,
    }),
    setTokens,
    clearTokens,
    staffLogin: async (username, password) => {
      const data = await request(`${API_BASE_URL}/auth/staff/login/`, {
        method: 'POST',
        ...jsonBody({ username, password }),
      })
      setTokens({ access: data.access, refresh: data.refresh })
      if (data.user) localStorage.setItem('user', JSON.stringify(data.user))
      if (data.roles) localStorage.setItem('roles', JSON.stringify(data.roles))
      if (data.hospitals) {
        localStorage.setItem('hospitals', JSON.stringify(data.hospitals))
      }
      return data
    },
    staffLoginStartOtp: async (username, password) =>
      request(`${API_BASE_URL}/auth/staff/login/otp/start/`, {
        method: 'POST',
        timeout: DELIVERY_TIMEOUT_MS,
        ...jsonBody({ username, password }),
      }),
    // `challenge` is the signed token returned by staffLoginStartOtp.
    staffOtpVerify: async (challenge, otp) => {
      const data = await request(`${API_BASE_URL}/auth/staff/login/otp/verify/`, {
        method: 'POST',
        ...jsonBody({ challenge, otp }),
      })
      setTokens({ access: data.access, refresh: data.refresh })
      if (data.user) localStorage.setItem('user', JSON.stringify(data.user))
      if (data.roles) localStorage.setItem('roles', JSON.stringify(data.roles))
      if (data.hospitals) {
        localStorage.setItem('hospitals', JSON.stringify(data.hospitals))
      }
      return data
    },
    staffOtpResend: async (challenge) =>
      request(`${API_BASE_URL}/auth/staff/login/otp/resend/`, {
        method: 'POST',
        timeout: DELIVERY_TIMEOUT_MS,
        ...jsonBody({ challenge }),
      }),
    requestPasswordReset: async (username) =>
      request(`${API_BASE_URL}/auth/password/reset/`, {
        method: 'POST',
        ...jsonBody({ username }),
      }),
    confirmPasswordReset: async (username, code, newPassword) =>
      request(`${API_BASE_URL}/auth/password/reset/confirm/`, {
        method: 'POST',
        ...jsonBody({ username, code, new_password: newPassword }),
      }),
    getMe: async () => request(`${API_BASE_URL}/auth/staff/me/`),
    logout: async () => {
      try {
        // The server blacklists the refresh cookie and clears both cookies.
        await request(`${API_BASE_URL}/auth/staff/logout/`, {
          method: 'POST',
          ...jsonBody({}),
        })
      } catch (error) {
        // Keep logout local even if the server call fails.
      }
      clearTokens()
      localStorage.removeItem('user')
      localStorage.removeItem('roles')
      localStorage.removeItem('hospitals')
      clearCachedPatientData()
    },
    register: async (payload) =>
      request(`${API_BASE_URL}/auth/register/`, {
        method: 'POST',
        timeout: DELIVERY_TIMEOUT_MS,
        ...jsonBody(payload),
      }),
    requestPatientOtp: async (phone) =>
      request(`${API_BASE_URL}/auth/patient/otp/request/`, {
        method: 'POST',
        timeout: DELIVERY_TIMEOUT_MS,
        ...jsonBody({ phone }),
      }),
    verifyPatientOtp: async (phone, otp) => {
      const data = await request(`${API_BASE_URL}/auth/patient/otp/verify/`, {
        method: 'POST',
        ...jsonBody({ phone, otp }),
      })
      setTokens({ access: data.access, refresh: data.refresh })
      return data
    },
    requestEmailOtp: async (email) =>
      request(`${API_BASE_URL}/auth/patient/email-otp/request/`, {
        method: 'POST',
        timeout: DELIVERY_TIMEOUT_MS,
        ...jsonBody({ email }),
      }),
    verifyEmailOtp: async (email, otp) =>
      request(`${API_BASE_URL}/auth/patient/email-otp/verify/`, {
        method: 'POST',
        ...jsonBody({ email, otp }),
      }),
    patientEmailLogin: async (email, password) => {
      const data = await request(`${API_BASE_URL}/auth/patient/login/`, {
        method: 'POST',
        ...jsonBody({ email, password }),
      })
      setTokens({ access: data.access, refresh: data.refresh })
      return data
    },
    patientTokenLogin: async (identifier, password) => {
      const data = await request(`${API_BASE_URL}/auth/patient/token/`, {
        method: 'POST',
        ...jsonBody({ identifier, password }),
      })
      setTokens({ access: data.access, refresh: data.refresh })
      return data
    },
    patientMe: async () => request(`${API_BASE_URL}/auth/patient/me/`),
    // POST /api/auth/google/ with the ID token from Google Identity Services.
    googleLogin: async (credential) =>
      request(`${API_BASE_URL}/auth/google/`, {
        method: 'POST',
        ...jsonBody({ credential }),
      }),
    applySession: (data) => {
      setTokens({ access: data?.access, refresh: data?.refresh })
      return data
    },
    // Temporary shared development sign-in (backend/users/dev_login.py).
    devLoginStatus: async () =>
      request(`${API_BASE_URL}/auth/dev/login/`).catch(() => ({ enabled: false })),
    devLogin: async (identifier, password, role) =>
      request(`${API_BASE_URL}/auth/dev/login/`, {
        method: 'POST',
        ...jsonBody({ identifier, password, role }),
      }),
  },

  patients: {
    // GET /api/patients/ (optionally scoped to a hospital)
    list: async (hospitalId, page = 1, search = '') => {
      const params = new URLSearchParams()
      if (hospitalId) params.set('hospital', hospitalId)
      params.set('page', page)
      if (search) params.set('search', search)
      const query = params.toString() ? `?${params.toString()}` : ''

      return request(`${API_BASE_URL}/patients/${query}`)
    },

    get: async (id) => request(`${API_BASE_URL}/patients/${id}/`),

    // POST /api/patients/
    create: async (data) =>
      request(`${API_BASE_URL}/patients/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PUT /api/patients/{id}/
    update: async (id, data) =>
      request(`${API_BASE_URL}/patients/${id}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PATCH /api/patients/{id}/
    patch: async (id, data) =>
      request(`${API_BASE_URL}/patients/${id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // DELETE /api/patients/{id}/
    delete: async (id) => {
      await request(`${API_BASE_URL}/patients/${id}/`, {
        method: 'DELETE',
      })
      return true
    },
  },

  // Doctors are needed by the Appointments page to resolve the doctor
  // name typed/selected in the UI into a real backend foreign key.
  doctors: {
    // GET /api/doctors/ (optionally scoped to a hospital)
    list: async (hospitalId) => {
      const query = hospitalId
        ? `?hospital=${encodeURIComponent(hospitalId)}`
        : ''

      return request(`${API_BASE_URL}/doctors/${query}`)
    },

    // GET /api/doctors/{id}/
    get: async (id) => request(`${API_BASE_URL}/doctors/${id}/`),

    // POST /api/doctors/
    create: async (data) =>
      request(`${API_BASE_URL}/doctors/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PUT /api/doctors/{id}/
    update: async (id, data) =>
      request(`${API_BASE_URL}/doctors/${id}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PATCH /api/doctors/{id}/
    patch: async (id, data) =>
      request(`${API_BASE_URL}/doctors/${id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // DELETE /api/doctors/{id}/
    delete: async (id) => {
      await request(`${API_BASE_URL}/doctors/${id}/`, {
        method: 'DELETE',
      })
      return true
    },
  },

  nurses: {
    // GET /api/nurses/nurses/ (optionally scoped to a hospital)
    list: async (hospitalId) => {
      const query = hospitalId
        ? `?hospital=${encodeURIComponent(hospitalId)}`
        : ''

      return request(`${API_BASE_URL}/nurses/nurses/${query}`)
    },

    // GET /api/nurses/{id}/
    get: async (id) => request(`${API_BASE_URL}/nurses/nurses/${id}/`),

    // POST /api/nurses/
    create: async (data) =>
      request(`${API_BASE_URL}/nurses/nurses/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PUT /api/nurses/{id}/
    update: async (id, data) =>
      request(`${API_BASE_URL}/nurses/nurses/${id}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PATCH /api/nurses/{id}/
    patch: async (id, data) =>
      request(`${API_BASE_URL}/nurses/nurses/${id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // DELETE /api/nurses/{id}/
    delete: async (id) => {
      await request(`${API_BASE_URL}/nurses/nurses/${id}/`, {
        method: 'DELETE',
      })
      return true
    },

    assessments: {
      list: async (hospitalId, patientId, admissionId) => {
        const params = new URLSearchParams();
        if (hospitalId) params.set('hospital', hospitalId);
        if (patientId) params.set('patient', patientId);
        if (admissionId) params.set('admission', admissionId);
        const query = params.toString() ? `?${params.toString()}` : '';
        return request(`${API_BASE_URL}/nurses/assessments/${query}`);
      },
      get: async (id) => request(`${API_BASE_URL}/nurses/assessments/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/nurses/assessments/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      update: async (id, data) =>
        request(`${API_BASE_URL}/nurses/assessments/${id}/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      delete: async (id) => {
        await request(`${API_BASE_URL}/nurses/assessments/${id}/`, { method: 'DELETE' });
        return true;
      },
    },
    notes: {
      list: async (hospitalId, patientId, admissionId) => {
        const params = new URLSearchParams();
        if (hospitalId) params.set('hospital', hospitalId);
        if (patientId) params.set('patient', patientId);
        if (admissionId) params.set('admission', admissionId);
        const query = params.toString() ? `?${params.toString()}` : '';
        return request(`${API_BASE_URL}/nurses/notes/${query}`);
      },
      get: async (id) => request(`${API_BASE_URL}/nurses/notes/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/nurses/notes/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      update: async (id, data) =>
        request(`${API_BASE_URL}/nurses/notes/${id}/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      delete: async (id) => {
        await request(`${API_BASE_URL}/nurses/notes/${id}/`, { method: 'DELETE' });
        return true;
      },
    },
    careTasks: {
      list: async (hospitalId, patientId, admissionId, assignedNurseId, status, shiftDate) => {
        const params = new URLSearchParams();
        if (hospitalId) params.set('hospital', hospitalId);
        if (patientId) params.set('patient', patientId);
        if (admissionId) params.set('admission', admissionId);
        if (assignedNurseId) params.set('assigned_nurse', assignedNurseId);
        if (status) params.set('status', status);
        if (shiftDate) params.set('shift_date', shiftDate);
        const query = params.toString() ? `?${params.toString()}` : '';
        return request(`${API_BASE_URL}/nurses/care-tasks/${query}`);
      },
      get: async (id) => request(`${API_BASE_URL}/nurses/care-tasks/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/nurses/care-tasks/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      update: async (id, data) =>
        request(`${API_BASE_URL}/nurses/care-tasks/${id}/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      start: async (id) =>
        request(`${API_BASE_URL}/nurses/care-tasks/${id}/start/`, { method: 'POST' }),
      complete: async (id, data) =>
        request(`${API_BASE_URL}/nurses/care-tasks/${id}/complete/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      myTasks: async (nurseId) =>
        request(`${API_BASE_URL}/nurses/care-tasks/my_tasks/?nurse_id=${nurseId}`),
    },
    mar: {
      list: async (hospitalId, patientId, admissionId, isActive) => {
        const params = new URLSearchParams();
        if (hospitalId) params.set('hospital', hospitalId);
        if (patientId) params.set('patient', patientId);
        if (admissionId) params.set('admission', admissionId);
        if (isActive !== undefined) params.set('is_active', isActive);
        const query = params.toString() ? `?${params.toString()}` : '';
        return request(`${API_BASE_URL}/nurses/mar/${query}`);
      },
      get: async (id) => request(`${API_BASE_URL}/nurses/mar/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/nurses/mar/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      update: async (id, data) =>
        request(`${API_BASE_URL}/nurses/mar/${id}/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      generateSchedule: async (id, startDate) =>
        request(`${API_BASE_URL}/nurses/mar/${id}/generate_schedule/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ start_date: startDate }),
        }),
      dueMedications: async (hospitalId) =>
        request(`${API_BASE_URL}/nurses/mar/due_medications/?hospital=${hospitalId}`),
    },
    marAdministrations: {
      list: async (hospitalId, marId, status) => {
        const params = new URLSearchParams();
        if (hospitalId) params.set('hospital', hospitalId);
        if (marId) params.set('mar', marId);
        if (status) params.set('status', status);
        const query = params.toString() ? `?${params.toString()}` : '';
        return request(`${API_BASE_URL}/nurses/mar-administrations/${query}`);
      },
      get: async (id) => request(`${API_BASE_URL}/nurses/mar-administrations/${id}/`),
      administer: async (id, data) =>
        request(`${API_BASE_URL}/nurses/mar-administrations/${id}/administer/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      hold: async (id, data) =>
        request(`${API_BASE_URL}/nurses/mar-administrations/${id}/hold/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      refuse: async (id, data) =>
        request(`${API_BASE_URL}/nurses/mar-administrations/${id}/refuse/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      markMissed: async (id, data) =>
        request(`${API_BASE_URL}/nurses/mar-administrations/${id}/mark_missed/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
    },
    patientAssignments: {
      list: async (hospitalId, nurseId, patientId, shiftDate, shift, isActive) => {
        const params = new URLSearchParams();
        if (hospitalId) params.set('hospital', hospitalId);
        if (nurseId) params.set('nurse', nurseId);
        if (patientId) params.set('patient', patientId);
        if (shiftDate) params.set('shift_date', shiftDate);
        if (shift) params.set('shift', shift);
        if (isActive !== undefined) params.set('is_active', isActive);
        const query = params.toString() ? `?${params.toString()}` : '';
        return request(`${API_BASE_URL}/nurses/patient-assignments/${query}`);
      },
      get: async (id) => request(`${API_BASE_URL}/nurses/patient-assignments/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/nurses/patient-assignments/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      assignPatients: async (data) =>
        request(`${API_BASE_URL}/nurses/patient-assignments/assign_patients/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
    },
  },

  compounder: {
    list: async (hospitalId) => {
      const query = hospitalId
        ? `?hospital=${encodeURIComponent(hospitalId)}`
        : ''
      return request(`${API_BASE_URL}/compounder/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/compounder/${id}/`),
    create: async (data) =>
      request(`${API_BASE_URL}/compounder/`, {
        method: 'POST',
        ...jsonBody(data),
      }),
    update: async (id, data) =>
      request(`${API_BASE_URL}/compounder/${id}/`, {
        method: 'PUT',
        ...jsonBody(data),
      }),
    patch: async (id, data) =>
      request(`${API_BASE_URL}/compounder/${id}/`, {
        method: 'PATCH',
        ...jsonBody(data),
      }),
    delete: async (id) => {
      await request(`${API_BASE_URL}/compounder/${id}/`, { method: 'DELETE' })
      return true
    },
  },

  appointments: {
    // GET /api/appointments/booking-options/?hospital=&doctor=&date= (patients only)
    bookingOptions: async ({ hospital, doctor, date } = {}) => {
      const params = new URLSearchParams()
      if (hospital) params.set('hospital', hospital)
      if (doctor) params.set('doctor', doctor)
      if (date) params.set('date', date)
      const query = params.toString() ? `?${params.toString()}` : ''
      return request(`${API_BASE_URL}/appointments/booking-options/${query}`)
    },

    // POST /api/appointments/book/ — a patient books a slot for themselves
    book: async (data) =>
      request(`${API_BASE_URL}/appointments/book/`, {
        method: 'POST',
        ...jsonBody(data),
      }),

    // GET /api/appointments/ (scoped to the selected hospital)
    list: async (hospitalId) => {
      const query = hospitalId
        ? `?hospital=${encodeURIComponent(hospitalId)}`
        : ''

      return request(`${API_BASE_URL}/appointments/${query}`)
    },

    get: async (id) => request(`${API_BASE_URL}/appointments/${id}/`),

    // POST /api/appointments/
    create: async (data) =>
      request(`${API_BASE_URL}/appointments/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PUT /api/appointments/{id}/
    update: async (id, data) =>
      request(`${API_BASE_URL}/appointments/${id}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PATCH /api/appointments/{id}/
    patch: async (id, data) =>
      request(`${API_BASE_URL}/appointments/${id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // DELETE /api/appointments/{id}/
    delete: async (id) => {
      await request(`${API_BASE_URL}/appointments/${id}/`, {
        method: 'DELETE',
      })
      return true
    },
  },

  // Visits are the clinical encounter a queue token hangs off. The Queue
  // page mostly needs to read them / create them so a token has a parent.
  visits: {
    // GET /api/encounters/visits/ (scoped to a hospital)
    list: async (hospitalId) => {
      const query = hospitalId
        ? `?hospital=${encodeURIComponent(hospitalId)}`
        : ''

      return request(`${API_BASE_URL}/encounters/visits/${query}`)
    },

    get: async (id) =>
      request(`${API_BASE_URL}/encounters/visits/${id}/`),

    // POST /api/encounters/visits/
    create: async (data) =>
      request(`${API_BASE_URL}/encounters/visits/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PATCH /api/encounters/visits/{id}/
    patch: async (id, data) =>
      request(`${API_BASE_URL}/encounters/visits/${id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PUT /api/encounters/visits/{id}/
    update: async (id, data) =>
      request(`${API_BASE_URL}/encounters/visits/${id}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // DELETE /api/encounters/visits/{id}/
    remove: async (id) => {
      await request(`${API_BASE_URL}/encounters/visits/${id}/`, {
        method: 'DELETE',
      })
      return true
    },
  },

  // Queue tokens — the persisted queue records behind the Queue page.
  // token_number is allocated server-side by the Django serializer, so the
  // frontend never invents token numbers for API-backed records.
  queue: {
    // GET /api/encounters/queue-tokens/ (scoped to a hospital)
    list: async (hospitalId) => {
      const query = hospitalId
        ? `?hospital=${encodeURIComponent(hospitalId)}`
        : ''

      return request(`${API_BASE_URL}/encounters/queue-tokens/${query}`)
    },

    get: async (id) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/${id}/`),

    // POST /api/encounters/queue-tokens/ (token_number may be omitted;
    // the backend assigns the next number for the hospital/day)
    create: async (data) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PATCH /api/encounters/queue-tokens/{id}/
    patch: async (id, data) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/${id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // POST /api/encounters/queue-tokens/issue/
    // Appointment -> Visit -> QueueToken in one server-side transaction.
    issue: async (appointmentId, extra = {}) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/issue/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ appointment: appointmentId, ...extra }),
      }),

    // POST /api/encounters/queue-tokens/{id}/call/
    call: async (id) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/${id}/call/`, {
        method: 'POST',
      }),

    // POST /api/encounters/queue-tokens/{id}/acknowledge/
    // Patient acknowledges the call: { action: "ACKNOWLEDGE" | "NOT_READY" | "REQUEST_DELAY" | "CANCEL" }
    acknowledge: async (id, action = "ACKNOWLEDGE") =>
      request(`${API_BASE_URL}/encounters/queue-tokens/${id}/acknowledge/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ action }),
      }),

    // POST /api/encounters/queue-tokens/{id}/ready/
    ready: async (id) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/${id}/ready/`, {
        method: 'POST',
      }),

    // A called (or acknowledged / ready) patient goes in to the doctor.
    startConsultation: async (id) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/${id}/start-consultation/`, { method: 'POST' }),

    // A skipped or no-show token goes back to Waiting.
    requeue: async (id) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/${id}/requeue/`, { method: 'POST' }),

    // POST /api/encounters/queue-tokens/{id}/complete/
    complete: async (id) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/${id}/complete/`, {
        method: 'POST',
      }),

    // POST /api/encounters/queue-tokens/{id}/skip/
    skip: async (id) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/${id}/skip/`, {
        method: 'POST',
      }),

    // POST /api/encounters/queue-tokens/{id}/no-show/
    noShow: async (id) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/${id}/no-show/`, {
        method: 'POST',
      }),

    // POST /api/encounters/queue-tokens/call-next/?hospital=<id>
    callNext: async (hospitalId) => {
      const query = hospitalId
        ? `?hospital=${encodeURIComponent(hospitalId)}`
        : ''

      return request(
        `${API_BASE_URL}/encounters/queue-tokens/call-next/${query}`,
        { method: 'POST' }
      )
    },

    // GET /api/encounters/queue-tokens/estimates/?hospital=<id>
    estimates: async (hospitalId) => {
      const query = hospitalId
        ? `?hospital=${encodeURIComponent(hospitalId)}`
        : ''

      return request(`${API_BASE_URL}/encounters/queue-tokens/estimates/${query}`)
    },

    // DELETE /api/encounters/queue-tokens/{id}/
    delete: async (id) => {
      await request(`${API_BASE_URL}/encounters/queue-tokens/${id}/`, {
        method: 'DELETE',
      })
      return true
    },
  },

  // Queue estimates
  queueEstimates: {
    // GET /api/encounters/queue-tokens/estimates/?hospital=<id>
    list: async (hospitalId) => {
      const query = hospitalId
        ? `?hospital=${encodeURIComponent(hospitalId)}`
        : ''

      return request(`${API_BASE_URL}/encounters/queue-tokens/estimates/${query}`)
    },
  },

  // Clinical records — these all hang off an encounters.Visit.  Each clinical
  // screen selects a Visit first, then reads/writes the clinical models that
  // reference it.  All methods reuse the shared request() helper above.
  clinical: {
    vitals: {
      // GET /api/clinical/vitals/?visit=<id>
      list: async (visitId) => {
        const query = visitId
          ? `?visit=${encodeURIComponent(visitId)}`
          : ''

        return request(`${API_BASE_URL}/clinical/vitals/${query}`)
      },

      // POST /api/clinical/vitals/
      create: async (data) =>
        request(`${API_BASE_URL}/clinical/vitals/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        }),

      // PUT /api/clinical/vitals/{id}/
      update: async (id, data) =>
        request(`${API_BASE_URL}/clinical/vitals/${id}/`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        }),

      // DELETE /api/clinical/vitals/{id}/
      delete: async (id) => {
        await request(`${API_BASE_URL}/clinical/vitals/${id}/`, {
          method: 'DELETE',
        })
        return true
      },
    },

    notes: {
      // GET /api/clinical/clinical-notes/?visit=<id>
      list: async (visitId) => {
        const query = visitId
          ? `?visit=${encodeURIComponent(visitId)}`
          : ''

        return request(
          `${API_BASE_URL}/clinical/clinical-notes/${query}`
        )
      },

      // POST /api/clinical/clinical-notes/
      create: async (data) =>
        request(`${API_BASE_URL}/clinical/clinical-notes/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        }),

      // PUT /api/clinical/clinical-notes/{id}/
      update: async (id, data) =>
        request(`${API_BASE_URL}/clinical/clinical-notes/${id}/`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        }),

      // DELETE /api/clinical/clinical-notes/{id}/
      delete: async (id) => {
        await request(
          `${API_BASE_URL}/clinical/clinical-notes/${id}/`,
          {
            method: 'DELETE',
          }
        )
        return true
      },
    },

    diagnoses: {
      // GET /api/clinical/diagnoses/?visit=<id>
      list: async (visitId) => {
        const query = visitId
          ? `?visit=${encodeURIComponent(visitId)}`
          : ''

        return request(
          `${API_BASE_URL}/clinical/diagnoses/${query}`
        )
      },

      // POST /api/clinical/diagnoses/
      create: async (data) =>
        request(`${API_BASE_URL}/clinical/diagnoses/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        }),

      // PUT /api/clinical/diagnoses/{id}/
      update: async (id, data) =>
        request(`${API_BASE_URL}/clinical/diagnoses/${id}/`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        }),

      // DELETE /api/clinical/diagnoses/{id}/
      delete: async (id) => {
        await request(
          `${API_BASE_URL}/clinical/diagnoses/${id}/`,
          {
            method: 'DELETE',
          }
        )
        return true
      },
    },

    serviceOrders: {
      // GET /api/clinical/service-orders/?visit=<id>
      list: async (visitId) => {
        const query = visitId
          ? `?visit=${encodeURIComponent(visitId)}`
          : ''

        return request(
          `${API_BASE_URL}/clinical/service-orders/${query}`
        )
      },

      // POST /api/clinical/service-orders/
      create: async (data) =>
        request(`${API_BASE_URL}/clinical/service-orders/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        }),

      // PUT /api/clinical/service-orders/{id}/
      update: async (id, data) =>
        request(
          `${API_BASE_URL}/clinical/service-orders/${id}/`,
          {
            method: 'PUT',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
          }
        ),

      // DELETE /api/clinical/service-orders/{id}/
      delete: async (id) => {
        await request(
          `${API_BASE_URL}/clinical/service-orders/${id}/`,
          {
            method: 'DELETE',
          }
        )
        return true
      },
    },

    prescriptions: {
      // GET /api/clinical/prescriptions/?hospital=<id>&patient=<id>&visit=<id>
      list: async ({ hospitalId, patientId, visitId } = {}) => {
        const params = new URLSearchParams()

        if (hospitalId) params.set('hospital', hospitalId)
        if (patientId) params.set('patient', patientId)
        if (visitId) params.set('visit', visitId)

        const query = params.toString() ? `?${params.toString()}` : ''

        return request(`${API_BASE_URL}/clinical/prescriptions/${query}`)
      },

      // GET /api/clinical/prescriptions/{id}/
      get: async (id) =>
        request(`${API_BASE_URL}/clinical/prescriptions/${id}/`),

      // POST /api/clinical/prescriptions/
      create: async (data) =>
        request(`${API_BASE_URL}/clinical/prescriptions/`, {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        }),

      // PUT /api/clinical/prescriptions/{id}/
      update: async (id, data) =>
        request(`${API_BASE_URL}/clinical/prescriptions/${id}/`, {
          method: 'PUT',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        }),

      // PATCH /api/clinical/prescriptions/{id}/
      patch: async (id, data) =>
        request(`${API_BASE_URL}/clinical/prescriptions/${id}/`, {
          method: 'PATCH',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify(data),
        }),

      // DELETE /api/clinical/prescriptions/{id}/
      delete: async (id) => {
        await request(`${API_BASE_URL}/clinical/prescriptions/${id}/`, {
          method: 'DELETE',
        })
        return true
      },
    },

    // Signed by the requesting doctor; issued once and never edited.
    certificates: {
      // GET /api/clinical/certificates/?patient=<id>
      list: async ({ patientId } = {}) => {
        const query = patientId ? `?patient=${encodeURIComponent(patientId)}` : ''
        return request(`${API_BASE_URL}/clinical/certificates/${query}`)
      },

      // POST /api/clinical/certificates/
      create: async (data) =>
        request(`${API_BASE_URL}/clinical/certificates/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
    },

    // Only a referral's status can change after it is made.
    referrals: {
      // GET /api/clinical/referrals/?patient=<id>
      list: async ({ patientId } = {}) => {
        const query = patientId ? `?patient=${encodeURIComponent(patientId)}` : ''
        return request(`${API_BASE_URL}/clinical/referrals/${query}`)
      },

      // POST /api/clinical/referrals/
      create: async (data) =>
        request(`${API_BASE_URL}/clinical/referrals/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),

      // PATCH /api/clinical/referrals/{id}/  { status }
      setStatus: async (id, status) =>
        request(`${API_BASE_URL}/clinical/referrals/${id}/`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ status }),
        }),
    },

    // Vaccination register (D15). Doses are corrected, never deleted.
    immunizations: {
      // GET /api/clinical/immunizations/?patient=<id>
      list: async ({ patientId } = {}) => {
        const query = patientId ? `?patient=${encodeURIComponent(patientId)}` : ''
        return request(`${API_BASE_URL}/clinical/immunizations/${query}`)
      },

      // POST /api/clinical/immunizations/
      create: async (data) =>
        request(`${API_BASE_URL}/clinical/immunizations/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),

      // PATCH /api/clinical/immunizations/{id}/
      update: async (id, data) =>
        request(`${API_BASE_URL}/clinical/immunizations/${id}/`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
    },

    // =====================================
    // PHARMACY
    // =====================================
    pharmacy: {
      medicines: {
        // GET /api/pharmacy/?hospital=<id>
        list: async (hospitalId) => {
          const query = hospitalId
            ? `?hospital=${encodeURIComponent(hospitalId)}`
            : ''
          return request(`${API_BASE_URL}/pharmacy/${query}`)
        },

        // GET /api/pharmacy/{id}/
        get: async (id) =>
          request(`${API_BASE_URL}/pharmacy/${id}/`),

        // POST /api/pharmacy/
        create: async (data) =>
          request(`${API_BASE_URL}/pharmacy/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
          }),

        // PATCH /api/pharmacy/{id}/
        update: async (id, data) =>
          request(`${API_BASE_URL}/pharmacy/${id}/`, {
            method: 'PATCH',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
          }),

        // DELETE /api/pharmacy/{id}/
        remove: async (id) => {
          await request(`${API_BASE_URL}/pharmacy/${id}/`, {
            method: 'DELETE',
          })
          return true
        },
      },

      sales: {
        // GET /api/pharmacy-sales/?hospital=<id>
        list: async (hospitalId) => {
          const query = hospitalId
            ? `?hospital=${encodeURIComponent(hospitalId)}`
            : ''
          return request(`${API_BASE_URL}/pharmacy-sales/${query}`)
        },

        // POST /api/pharmacy-sales/
        create: async (data) =>
          request(`${API_BASE_URL}/pharmacy-sales/`, {
            method: 'POST',
            headers: {
              'Content-Type': 'application/json',
            },
            body: JSON.stringify(data),
          }),
      },
    },
  },

  // Blood Bank
  bloodbank: {
    inventory: {
      list: async (hospitalId) => {
        const query = hospitalId
          ? `?hospital=${encodeURIComponent(hospitalId)}`
          : ''
        return request(`${API_BASE_URL}/bloodbank/inventory/${query}`)
      },
      get: async (id) => request(`${API_BASE_URL}/bloodbank/inventory/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/bloodbank/inventory/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      update: async (id, data) =>
        request(`${API_BASE_URL}/bloodbank/inventory/${id}/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      delete: async (id) => {
        await request(`${API_BASE_URL}/bloodbank/inventory/${id}/`, { method: 'DELETE' })
        return true
      },
    },
    requests: {
      list: async (hospitalId) => {
        const query = hospitalId
          ? `?hospital=${encodeURIComponent(hospitalId)}`
          : ''
        return request(`${API_BASE_URL}/bloodbank/requests/${query}`)
      },
      get: async (id) => request(`${API_BASE_URL}/bloodbank/requests/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/bloodbank/requests/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      update: async (id, data) =>
        request(`${API_BASE_URL}/bloodbank/requests/${id}/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      patch: async (id, data) =>
        request(`${API_BASE_URL}/bloodbank/requests/${id}/`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      delete: async (id) => {
        await request(`${API_BASE_URL}/bloodbank/requests/${id}/`, { method: 'DELETE' })
        return true
      },
      // Workflow: Requested -> approve (checks stock) -> issue (deducts stock), or reject.
      approve: async (id) =>
        request(`${API_BASE_URL}/bloodbank/requests/${id}/approve/`, { method: 'POST' }),
      issue: async (id) =>
        request(`${API_BASE_URL}/bloodbank/requests/${id}/issue/`, { method: 'POST' }),
      reject: async (id) =>
        request(`${API_BASE_URL}/bloodbank/requests/${id}/reject/`, { method: 'POST' }),
    },
    transactions: {
      list: async (hospitalId) => {
        const query = hospitalId
          ? `?hospital=${encodeURIComponent(hospitalId)}`
          : ''
        return request(`${API_BASE_URL}/bloodbank/transactions/${query}`)
      },
      get: async (id) => request(`${API_BASE_URL}/bloodbank/transactions/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/bloodbank/transactions/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
    },
  },

  // IPD / Discharge
  ipd: {
    admissions: {
      list: async (hospitalId) => {
        const query = hospitalId
          ? `?hospital=${encodeURIComponent(hospitalId)}`
          : ''
        return request(`${API_BASE_URL}/ipd/admissions/${query}`)
      },
      // GET /api/ipd/admissions/?patient=<id>&status=Admitted
      currentForPatient: async (patientId) =>
        request(`${API_BASE_URL}/ipd/admissions/?patient=${encodeURIComponent(patientId)}&status=Admitted`),
      get: async (id) => request(`${API_BASE_URL}/ipd/admissions/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/ipd/admissions/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      update: async (id, data) =>
        request(`${API_BASE_URL}/ipd/admissions/${id}/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      patch: async (id, data) =>
        request(`${API_BASE_URL}/ipd/admissions/${id}/`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      allocateBed: async (id, bedId) =>
        request(`${API_BASE_URL}/ipd/admissions/${id}/allocate_bed/`, {
          method: 'POST',
          ...jsonBody({ bed_id: bedId }),
        }),
      releaseBed: async (id) =>
        request(`${API_BASE_URL}/ipd/admissions/${id}/release_bed/`, {
          method: 'POST',
        }),
      initiateDischarge: async (id) =>
        request(`${API_BASE_URL}/ipd/admissions/${id}/initiate_discharge/`, {
          method: 'POST',
        }),
      completeDischarge: async (id) =>
        request(`${API_BASE_URL}/ipd/admissions/${id}/complete_discharge/`, {
          method: 'POST',
        }),
    },
    bedAllocations: {
      list: async (hospitalId) => {
        const query = hospitalId
          ? `?hospital=${encodeURIComponent(hospitalId)}`
          : ''
        return request(`${API_BASE_URL}/ipd/bed-allocations/${query}`)
      },
      get: async (id) => request(`${API_BASE_URL}/ipd/bed-allocations/${id}/`),
      availableBeds: async (hospitalId) =>
        request(
          `${API_BASE_URL}/ipd/bed-allocations/available_beds/?hospital=${encodeURIComponent(hospitalId)}`
        ),
    },
    dischargePlans: {
      list: async (hospitalId) => {
        const query = hospitalId
          ? `?hospital=${encodeURIComponent(hospitalId)}`
          : ''
        return request(`${API_BASE_URL}/ipd/discharge-plans/${query}`)
      },
      get: async (id) => request(`${API_BASE_URL}/ipd/discharge-plans/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/ipd/discharge-plans/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      update: async (id, data) =>
        request(`${API_BASE_URL}/ipd/discharge-plans/${id}/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
    },
    dischargeSummaries: {
      list: async (hospitalId) => {
        const query = hospitalId
          ? `?hospital=${encodeURIComponent(hospitalId)}`
          : ''
        return request(`${API_BASE_URL}/ipd/discharge-summaries/${query}`)
      },
      get: async (id) => request(`${API_BASE_URL}/ipd/discharge-summaries/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/ipd/discharge-summaries/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      update: async (id, data) =>
        request(`${API_BASE_URL}/ipd/discharge-summaries/${id}/`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      // POST /api/ipd/discharge-summaries/{id}/finalize/ — linked doctor only; locks the summary
      finalize: async (id) =>
        request(`${API_BASE_URL}/ipd/discharge-summaries/${id}/finalize/`, {
          method: 'POST',
        }),
    },
    dischargeNotes: {
      list: async (hospitalId) => {
        const query = hospitalId
          ? `?hospital=${encodeURIComponent(hospitalId)}`
          : ''
        return request(`${API_BASE_URL}/ipd/discharge-notes/${query}`)
      },
      get: async (id) => request(`${API_BASE_URL}/ipd/discharge-notes/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/ipd/discharge-notes/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
},
  },
  home: {
      stats: async (hospitalId) => {
        const query = hospitalId
          ? `?hospital=${encodeURIComponent(hospitalId)}`
          : ''
        return request(`${API_BASE_URL}/home/stats/detail/${query}`)
      },
      summary: async (hospitalId) => {
        const query = hospitalId
          ? `?hospital=${encodeURIComponent(hospitalId)}`
          : ''
        return request(`${API_BASE_URL}/home/stats/${query}`)
      },
  },

  // Notifications
  notifications: {
    // GET /api/notifications/?hospital=<id>&patient=<id>
    list: async (hospitalId, patientId = null) => {
      const params = new URLSearchParams()
      params.set('hospital', hospitalId)
      if (patientId) params.set('patient', patientId)
      return request(`${API_BASE_URL}/notifications/notifications/?${params.toString()}`)
    },

    get: async (id) =>
      request(`${API_BASE_URL}/notifications/notifications/${id}/`),

    markRead: async (id) =>
      request(`${API_BASE_URL}/notifications/notifications/${id}/mark_read/`, {
        method: 'POST',
      }),

    // Deliveries
    deliveries: {
      // GET /api/notifications/deliveries/?hospital=<id>
      list: async (hospitalId) => {
        const query = hospitalId
          ? `?hospital=${encodeURIComponent(hospitalId)}`
          : ''
        return request(`${API_BASE_URL}/notifications/deliveries/${query}`)
      },
    },

    // Consent
    consent: {
      // GET /api/notifications/consents/?hospital=<id>&patient=<id>
      list: async (hospitalId, patientId = null) => {
        const params = new URLSearchParams()
        params.set('hospital', hospitalId)
        if (patientId) params.set('patient', patientId)
        return request(`${API_BASE_URL}/notifications/consents/?${params.toString()}`)
      },

      get: async (id) =>
        request(`${API_BASE_URL}/notifications/consents/${id}/`),

      // POST /api/notifications/consents/grant/
      grant: async (hospitalId, patientId, purpose) =>
        request(`${API_BASE_URL}/notifications/consents/grant/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ hospital: hospitalId, patient: patientId, purpose }),
        }),

      // POST /api/notifications/consents/revoke/
      revoke: async (hospitalId, patientId, purpose) =>
        request(`${API_BASE_URL}/notifications/consents/revoke/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ hospital: hospitalId, patient: patientId, purpose }),
        }),

      // GET /api/notifications/consents/check/?hospital=<id>&patient=<id>&purpose=<purpose>
      check: async (hospitalId, patientId, purpose) => {
        const params = new URLSearchParams()
        params.set('hospital', hospitalId)
        params.set('patient', patientId)
        params.set('purpose', purpose)
        return request(`${API_BASE_URL}/notifications/consents/check/?${params.toString()}`)
      },
    },

  },
}

function resolveUrl(url) {
  if (!url) return API_BASE_URL
  if (url.startsWith("http://") || url.startsWith("https://")) return url
  if (url.startsWith("/api")) return url
  const path = url.startsWith("/") ? url : `/${url}`
  return `${API_BASE_URL}${path}`
}

api.get = async (url, config = {}) => {
  const data = await request(resolveUrl(url), { method: "GET", ...config })
  return { data }
}
api.post = async (url, body, config = {}) => {
  const data = await request(resolveUrl(url), {
    method: "POST",
    ...jsonBody(body || {}),
    ...config,
  })
  return { data }
}
api.put = async (url, body, config = {}) => {
  const data = await request(resolveUrl(url), {
    method: "PUT",
    ...jsonBody(body || {}),
    ...config,
  })
  return { data }
}
api.patch = async (url, body, config = {}) => {
  const data = await request(resolveUrl(url), {
    method: "PATCH",
    ...jsonBody(body || {}),
    ...config,
  })
  return { data }
}
api.delete = async (url, config = {}) => {
  const data = await request(resolveUrl(url), { method: "DELETE", ...config })
  return { data }
}

// Audit trail of the selected hospital (Admin role).
api.audit = {
  logs: async (hospitalId) => {
    const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
    return request(`${API_BASE_URL}/audit/audit-logs/${query}`)
  },

  // GET /api/audit/audit-logs/?hospital=&page=&action=&model=&user=&from=&to=
  search: async (hospitalId, { page = 1, action, model, user, from, to } = {}) => {
    const params = new URLSearchParams({ hospital: hospitalId, page: String(page) })
    Object.entries({ action, model, user, from, to }).forEach(([key, value]) => {
      if (value) params.set(key, value)
    })
    return request(`${API_BASE_URL}/audit/audit-logs/?${params.toString()}`)
  },
}

// Staff administration for the selected hospital (Admin / Hospital Manager).
api.users = {
  me: async () => api.auth.getMe(),
  // -> { staff: [...] }
  list: async (params = {}) => {
    const query = new URLSearchParams(params).toString()
    return request(`${API_BASE_URL}/users/${query ? `?${query}` : ""}`)
  },
  // data: { role?, is_active?, department? }
  updateMembership: async (userId, data) =>
    request(`${API_BASE_URL}/users/${userId}/membership/`, { method: "PATCH", ...jsonBody(data) }),
  // data: { name, phone, email?, role, department? } -> staff row + invite_url when a password is still to be set
  invite: async (data) =>
    request(`${API_BASE_URL}/users/invite/`, { method: "POST", ...jsonBody(data) }),
  resendInvite: async (userId) =>
    request(`${API_BASE_URL}/users/${userId}/invite/`, { method: "POST" }),
}

// Public invitation link: who it is for (GET) and setting the first password (POST).
api.staffInvite = {
  get: async (uid, token) => request(`${API_BASE_URL}/auth/staff/invite/${uid}/${token}/`),
  accept: async (uid, token, data) =>
    request(`${API_BASE_URL}/auth/staff/invite/${uid}/${token}/`, { method: "POST", ...jsonBody(data) }),
}

// A ward with its rooms and numbered beds in one step (hospital setup).
// data: { name, ward_type, rooms: [{ room_number, beds, bed_type }] }
api.wardSetup = {
  create: async (hospitalId, data) =>
    request(`${API_BASE_URL}/hospital/wards/with-beds/?hospital=${encodeURIComponent(hospitalId)}`, { method: "POST", ...jsonBody({ ...data, hospital: hospitalId }) }),
}

// Departments / clinics of a hospital (Admin or Manager write).
api.departments = {
  list: async (hospitalId) => {
    const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
    return request(`${API_BASE_URL}/hospital/departments/${query}`)
  },
  create: async (data) =>
    request(`${API_BASE_URL}/hospital/departments/`, { method: "POST", ...jsonBody(data) }),
  update: async (id, data) =>
    request(`${API_BASE_URL}/hospital/departments/${id}/`, { method: "PATCH", ...jsonBody(data) }),
  remove: async (id) =>
    request(`${API_BASE_URL}/hospital/departments/${id}/`, { method: "DELETE" }),
}

// Wards, rooms and beds of a hospital. Only its Admin or Manager may change them.

api.wards = {
  list: async (hospitalId) => request(`${API_BASE_URL}/hospital/wards/?hospital=${encodeURIComponent(hospitalId)}`),
  create: async (hospitalId, data) =>
    request(`${API_BASE_URL}/hospital/wards/?hospital=${encodeURIComponent(hospitalId)}`, { method: "POST", ...jsonBody({ ...data, hospital: hospitalId }) }),
}

api.rooms = {
  list: async (hospitalId, wardId) =>
    request(`${API_BASE_URL}/hospital/rooms/?hospital=${encodeURIComponent(hospitalId)}&ward=${encodeURIComponent(wardId)}`),
  create: async (hospitalId, data) =>
    request(`${API_BASE_URL}/hospital/rooms/?hospital=${encodeURIComponent(hospitalId)}`, { method: "POST", ...jsonBody(data) }),
}

api.beds = {
  // Every bed of the hospital, across all result pages.
  listAll: async (hospitalId) => {
    const rows = []
    for (let page = 1; ; page += 1) {
      const data = await request(`${API_BASE_URL}/hospital/beds/?hospital=${encodeURIComponent(hospitalId)}&page=${page}`)
      rows.push(...(Array.isArray(data) ? data : data?.results || []))
      if (Array.isArray(data) || !data?.next) return rows
    }
  },
  create: async (hospitalId, data) =>
    request(`${API_BASE_URL}/hospital/beds/?hospital=${encodeURIComponent(hospitalId)}`, { method: "POST", ...jsonBody(data) }),
  update: async (hospitalId, id, data) =>
    request(`${API_BASE_URL}/hospital/beds/${id}/?hospital=${encodeURIComponent(hospitalId)}`, { method: "PATCH", ...jsonBody(data) }),
  remove: async (hospitalId, id) =>
    request(`${API_BASE_URL}/hospital/beds/${id}/?hospital=${encodeURIComponent(hospitalId)}`, { method: "DELETE" }),
}

// Nurse ward duty roster (Admin or Manager write; a Nurse sees the patients
// of the wards of today's duty).
api.nurseWardDuty = {
  list: async (hospitalId, shiftDate) => {
    const params = new URLSearchParams({ hospital: hospitalId })
    if (shiftDate) params.set("shift_date", shiftDate)
    return request(`${API_BASE_URL}/nurses/ward-assignments/?${params}`)
  },
  create: async (data) =>
    request(`${API_BASE_URL}/nurses/ward-assignments/`, { method: "POST", ...jsonBody(data) }),
  update: async (id, data) =>
    request(`${API_BASE_URL}/nurses/ward-assignments/${id}/`, { method: "PATCH", ...jsonBody(data) }),
}

// Hospital KPIs, counted on the server for the selected period.
api.reports = {
  dashboard: async (hospitalId, period = "last_30_days") =>
    request(`${API_BASE_URL}/reports/analytics/dashboard/?hospital=${encodeURIComponent(hospitalId)}&period=${encodeURIComponent(period)}`),
}

api.hospitals = {
  list: async () => request(`${API_BASE_URL}/hospital/hospitals/`),
  // Active hospitals any signed-in user (incl. patients) may choose from.
  directory: async (search = "") =>
    request(`${API_BASE_URL}/hospital/directory/${search ? `?search=${encodeURIComponent(search)}` : ""}`),
  get: async (id) => request(`${API_BASE_URL}/hospital/hospitals/${id}/`),
  // Creating/deleting is limited to platform administrators by the backend.
  create: async (data) =>
    request(`${API_BASE_URL}/hospital/hospitals/`, { method: 'POST', ...jsonBody(data) }),
  update: async (id, data) =>
    request(`${API_BASE_URL}/hospital/hospitals/${id}/`, { method: 'PATCH', ...jsonBody(data) }),
  remove: async (id) =>
    request(`${API_BASE_URL}/hospital/hospitals/${id}/`, { method: 'DELETE' }),
  myHospitals: async () => {
    try {
      const me = await api.auth.getMe()
      return me.hospitals || []
    } catch (error) {
      return []
    }
  },
}

api.pharmacy = api.clinical.pharmacy
api.prescriptions = api.clinical.prescriptions
api.nurses.nurses = api.nurses

api.laboratory = {
  tests: {
    list: async (hospitalId, patientId = null) => {
      const params = new URLSearchParams()
      if (hospitalId) params.set('hospital', hospitalId)
      if (patientId) params.set('patient', patientId)
      const query = params.toString() ? `?${params.toString()}` : ''
      return request(`${API_BASE_URL}/laboratory/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/laboratory/${id}/`),
    create: async (data) =>
      request(`${API_BASE_URL}/laboratory/`, { method: "POST", ...jsonBody(data) }),
    update: async (id, data) =>
      request(`${API_BASE_URL}/laboratory/${id}/`, { method: "PUT", ...jsonBody(data) }),
    delete: async (id) => {
      await request(`${API_BASE_URL}/laboratory/${id}/`, { method: "DELETE" })
      return true
    },
    collectSample: async (id, data) =>
      request(`${API_BASE_URL}/laboratory/${id}/collect_sample/`, {
        method: "POST",
        ...jsonBody(data),
      }),
    dispatchSample: async (id, data) =>
      request(`${API_BASE_URL}/laboratory/${id}/dispatch_sample/`, {
        method: "POST",
        ...jsonBody(data),
      }),
    receiveSample: async (id) =>
      request(`${API_BASE_URL}/laboratory/${id}/receive_sample/`, { method: "POST" }),
    startProcessing: async (id) =>
      request(`${API_BASE_URL}/laboratory/${id}/start_processing/`, { method: "POST" }),
    enterResult: async (id, data) =>
      request(`${API_BASE_URL}/laboratory/${id}/enter_result/`, {
        method: "POST",
        ...jsonBody(data),
      }),
    verifyResult: async (id, data) =>
      request(`${API_BASE_URL}/laboratory/${id}/verify_result/`, {
        method: "POST",
        ...jsonBody(data),
      }),
    releaseResult: async (id) =>
      request(`${API_BASE_URL}/laboratory/${id}/release_result/`, { method: "POST" }),
    cancel: async (id) =>
      request(`${API_BASE_URL}/laboratory/${id}/cancel/`, { method: "POST" }),
  },
  sampleCollections: {
    list: async (hospitalId) => {
      const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
      return request(`${API_BASE_URL}/laboratory/sample-collections/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/laboratory/sample-collections/${id}/`),
  },
  sampleDispatches: {
    list: async (hospitalId, status) => {
      const params = new URLSearchParams();
      if (hospitalId) params.set('hospital', hospitalId);
      if (status) params.set('status', status);
      const query = params.toString() ? `?${params.toString()}` : ""
      return request(`${API_BASE_URL}/laboratory/sample-dispatches/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/laboratory/sample-dispatches/${id}/`),
  },
  labResults: {
    list: async (hospitalId) => {
      const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
      return request(`${API_BASE_URL}/laboratory/lab-results/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/laboratory/lab-results/${id}/`),
  },
  resultVerifications: {
    list: async (hospitalId) => {
      const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
      return request(`${API_BASE_URL}/laboratory/result-verifications/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/laboratory/result-verifications/${id}/`),
  },
}

api.billing = {
  invoices: {
    list: async (hospitalId) => {
      const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
      return request(`${API_BASE_URL}/billing/invoices/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/billing/invoices/${id}/`),
    create: async (data) =>
      request(`${API_BASE_URL}/billing/invoices/`, { method: "POST", ...jsonBody(data) }),
    update: async (id, data) =>
      request(`${API_BASE_URL}/billing/invoices/${id}/`, { method: "PUT", ...jsonBody(data) }),
    delete: async (id) => {
      await request(`${API_BASE_URL}/billing/invoices/${id}/`, { method: "DELETE" })
      return true
    },
  },
  payments: {
    list: async (hospitalId) => {
      const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
      return request(`${API_BASE_URL}/billing/payments/${query}`)
    },
    create: async (data) =>
      request(`${API_BASE_URL}/billing/payments/`, { method: "POST", ...jsonBody(data) }),
    patch: async (id, data) =>
      request(`${API_BASE_URL}/billing/payments/${id}/`, { method: "PATCH", ...jsonBody(data) }),
  },
}

api.emergency = {
  visits: {
    list: async (hospitalId) => {
      const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
      return request(`${API_BASE_URL}/emergency/emergency-visits/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/emergency/emergency-visits/${id}/`),
    create: async (data) =>
      request(`${API_BASE_URL}/emergency/emergency-visits/`, { method: "POST", ...jsonBody(data) }),
    dashboard: async (hospitalId) => {
      const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
      return request(`${API_BASE_URL}/emergency/emergency-visits/dashboard/${query}`)
    },
    startTriage: async (id) =>
      request(`${API_BASE_URL}/emergency/emergency-visits/${id}/start_triage/`, { method: "POST" }),
    completeTriage: async (id, data) =>
      request(`${API_BASE_URL}/emergency/emergency-visits/${id}/complete_triage/`, {
        method: "POST",
        ...jsonBody(data),
      }),
    startConsultation: async (id, data) =>
      request(`${API_BASE_URL}/emergency/emergency-visits/${id}/start_consultation/`, {
        method: "POST",
        ...jsonBody(data || {}),
      }),
    addVitals: async (id, data) =>
      request(`${API_BASE_URL}/emergency/emergency-visits/${id}/add_vitals/`, {
        method: "POST",
        ...jsonBody(data),
      }),
    addOrder: async (id, data) =>
      request(`${API_BASE_URL}/emergency/emergency-visits/${id}/add_order/`, {
        method: "POST",
        ...jsonBody(data),
      }),
    addMedication: async (id, data) =>
      request(`${API_BASE_URL}/emergency/emergency-visits/${id}/add_medication/`, {
        method: "POST",
        ...jsonBody(data),
      }),
    discharge: async (id, data) =>
      request(`${API_BASE_URL}/emergency/emergency-visits/${id}/discharge/`, {
        method: "POST",
        ...jsonBody(data || {}),
      }),
    refer: async (id, data) =>
      request(`${API_BASE_URL}/emergency/emergency-visits/${id}/refer/`, {
        method: "POST",
        ...jsonBody(data || {}),
      }),
  },
  vitals: {
    list: async (hospitalId, visitId) => {
      const params = new URLSearchParams()
      if (hospitalId) params.set("hospital", hospitalId)
      if (visitId) params.set("visit", visitId)
      const query = params.toString() ? `?${params}` : ""
      return request(`${API_BASE_URL}/emergency/vitals/${query}`)
    },
  },
  orders: {
    list: async (hospitalId, visitId) => {
      const params = new URLSearchParams()
      if (hospitalId) params.set("hospital", hospitalId)
      if (visitId) params.set("visit", visitId)
      const query = params.toString() ? `?${params}` : ""
      return request(`${API_BASE_URL}/emergency/orders/${query}`)
    },
  },
  medications: {
    list: async (hospitalId, visitId) => {
      const params = new URLSearchParams()
      if (hospitalId) params.set("hospital", hospitalId)
      if (visitId) params.set("visit", visitId)
      const query = params.toString() ? `?${params}` : ""
      return request(`${API_BASE_URL}/emergency/medications/${query}`)
    },
  },
}

api.ipd.admissions.allocateBed = async (id, bedId) =>
  request(`${API_BASE_URL}/ipd/admissions/${id}/allocate_bed/`, {
    method: "POST",
    ...jsonBody({ bed_id: bedId }),
  })
api.ipd.admissions.releaseBed = async (id) =>
  request(`${API_BASE_URL}/ipd/admissions/${id}/release_bed/`, { method: "POST" })
api.ipd.admissions.initiateDischarge = async (id) =>
  request(`${API_BASE_URL}/ipd/admissions/${id}/initiate_discharge/`, { method: "POST" })
api.ipd.admissions.completeDischarge = async (id) =>
  request(`${API_BASE_URL}/ipd/admissions/${id}/complete_discharge/`, { method: "POST" })
api.ipd.bedAllocations.availableBeds = async (hospitalId) => {
  const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
  return request(`${API_BASE_URL}/ipd/bed-allocations/available_beds/${query}`)
}

// AI medical scribe (/api/ai/...)
api.aiScribe = {}
api.aiScribe.consultationSessions = {
  list: async (hospitalId) => {
    const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
    return request(`${API_BASE_URL}/ai/consultation-sessions/${query}`)
  },
  create: async (data) =>
    request(`${API_BASE_URL}/ai/consultation-sessions/`, { method: "POST", ...jsonBody(data) }),
  startRecording: async (id, data) =>
    request(`${API_BASE_URL}/ai/consultation-sessions/${id}/start_recording/`, {
      method: "POST",
      ...jsonBody(data || {}),
    }),
  stopRecording: async (id, data) =>
    request(`${API_BASE_URL}/ai/consultation-sessions/${id}/stop_recording/`, {
      method: "POST",
      ...jsonBody(data || {}),
    }),
  uploadAudio: async (id, audioBlob, extra = {}) => {
    const form = new FormData()
    form.append("audio_file", audioBlob)
    Object.entries(extra).forEach(([key, value]) => {
      if (value != null) form.append(key, value)
    })
    return request(`${API_BASE_URL}/ai/consultation-sessions/${id}/upload_audio/`, {
      method: "POST",
      body: form,
    })
  },
  transcribe: async (id) =>
    request(`${API_BASE_URL}/ai/consultation-sessions/${id}/transcribe/`, { method: "POST" }),
}

api.aiScribe.transcripts = {
  list: async (sessionId) => {
    const query = sessionId ? `?consultation=${encodeURIComponent(sessionId)}` : ""
    return request(`${API_BASE_URL}/ai/transcripts/${query}`)
  },
}

api.aiScribe.drafts = {
  list: async (sessionId) => {
    const query = sessionId ? `?consultation=${encodeURIComponent(sessionId)}` : ""
    return request(`${API_BASE_URL}/ai/drafts/${query}`)
  },
  generate: async (id) =>
    request(`${API_BASE_URL}/ai/drafts/${id}/generate/`, { method: "POST" }),
  regenerate: async (id) =>
    request(`${API_BASE_URL}/ai/drafts/${id}/regenerate/`, { method: "POST" }),
  review: async (id, data) =>
    request(`${API_BASE_URL}/ai/drafts/${id}/review/`, { method: "POST", ...jsonBody(data) }),
  approve: async (id) =>
    request(`${API_BASE_URL}/ai/drafts/${id}/approve/`, { method: "POST" }),
  reject: async (id, data) =>
    request(`${API_BASE_URL}/ai/drafts/${id}/reject/`, { method: "POST", ...jsonBody(data || {}) }),
}

api.aiScribe.reviews = {
  list: async (draftId) => {
    const query = draftId ? `?draft=${encodeURIComponent(draftId)}` : ""
    return request(`${API_BASE_URL}/ai/reviews/${query}`)
  },
}

api.consent = {
  forms: {
    list: async () => request(`${API_BASE_URL}/consent/forms/`),
  },
  records: {
    list: async (params = {}) => {
      const query = new URLSearchParams(params).toString()
      return request(`${API_BASE_URL}/consent/records/${query ? `?${query}` : ""}`)
    },
    // data: { form, signed_name, confirm: true, patient? (staff only) }
    sign: async (data) =>
      request(`${API_BASE_URL}/consent/records/`, { method: "POST", ...jsonBody(data) }),
    revoke: async (id) =>
      request(`${API_BASE_URL}/consent/records/${id}/revoke/`, { method: "POST" }),
  },
  shares: {
    list: async () => request(`${API_BASE_URL}/consent/shares/`),
    received: async () => request(`${API_BASE_URL}/consent/shares/received/`),
    // data: { recipient_hospital, scope: [...], purpose, expires_at, patient? }
    create: async (data) =>
      request(`${API_BASE_URL}/consent/shares/`, { method: "POST", ...jsonBody(data) }),
    revoke: async (id) =>
      request(`${API_BASE_URL}/consent/shares/${id}/revoke/`, { method: "POST" }),
    accessLog: async (id) => request(`${API_BASE_URL}/consent/shares/${id}/access-log/`),
    records: async (id) => request(`${API_BASE_URL}/consent/shares/${id}/records/`),
  },
}

api.procurement = {
  suppliers: {
    list: async (hospitalId) => {
      const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
      return request(`${API_BASE_URL}/procurement/suppliers/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/procurement/suppliers/${id}/`),
    create: async (data) =>
      request(`${API_BASE_URL}/procurement/suppliers/`, { method: "POST", ...jsonBody(data) }),
    update: async (id, data) =>
      request(`${API_BASE_URL}/procurement/suppliers/${id}/`, { method: "PUT", ...jsonBody(data) }),
    delete: async (id) => {
      await request(`${API_BASE_URL}/procurement/suppliers/${id}/`, { method: "DELETE" })
      return true
    },
  },
  purchases: {
    list: async (hospitalId) => {
      const query = hospitalId ? `?hospital=${encodeURIComponent(hospitalId)}` : ""
      return request(`${API_BASE_URL}/procurement/purchases/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/procurement/purchases/${id}/`),
    create: async (data) =>
      request(`${API_BASE_URL}/procurement/purchases/`, { method: "POST", ...jsonBody(data) }),
    update: async (id, data) =>
      request(`${API_BASE_URL}/procurement/purchases/${id}/`, { method: "PUT", ...jsonBody(data) }),
    receive: async (id, data) =>
      request(`${API_BASE_URL}/procurement/purchases/${id}/receive/`, { method: "POST", ...jsonBody(data) }),
  },
  purchaseItems: {
    list: async (hospitalId, purchaseId) => {
      const params = new URLSearchParams()
      if (hospitalId) params.set('hospital', hospitalId)
      if (purchaseId) params.set('purchase', purchaseId)
      const query = params.toString() ? `?${params.toString()}` : ""
      return request(`${API_BASE_URL}/procurement/purchase-items/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/procurement/purchase-items/${id}/`),
  },
  grns: {
    list: async (hospitalId, purchaseId) => {
      const params = new URLSearchParams()
      if (hospitalId) params.set('hospital', hospitalId)
      if (purchaseId) params.set('purchase', purchaseId)
      const query = params.toString() ? `?${params.toString()}` : ""
      return request(`${API_BASE_URL}/procurement/grns/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/procurement/grns/${id}/`),
  },
  grnItems: {
    list: async (hospitalId, grnId) => {
      const params = new URLSearchParams()
      if (hospitalId) params.set('hospital', hospitalId)
      if (grnId) params.set('goods_receipt', grnId)
      const query = params.toString() ? `?${params.toString()}` : ""
      return request(`${API_BASE_URL}/procurement/grn-items/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/procurement/grn-items/${id}/`),
  },
  stockTransactions: {
    list: async (hospitalId, medicineId) => {
      const params = new URLSearchParams()
      if (hospitalId) params.set('hospital', hospitalId)
      if (medicineId) params.set('medicine', medicineId)
      const query = params.toString() ? `?${params.toString()}` : ""
      return request(`${API_BASE_URL}/procurement/stock-transactions/${query}`)
    },
    get: async (id) => request(`${API_BASE_URL}/procurement/stock-transactions/${id}/`),
    adjust: async (data) =>
      request(`${API_BASE_URL}/procurement/stock-transactions/adjust/`, { method: "POST", ...jsonBody(data) }),
  },
}

api.patients.documents = {
  // GET /api/documents/{id}/download/ — authenticated and audited; files are
  // not served from /media/. Returns a Blob.
  download: async (docId) => {
    const response = await fetch(`${API_BASE_URL}/documents/${docId}/download/`, { headers: buildHeaders({}) })
    if (!response.ok) {
      const error = new Error(`Download failed (${response.status})`)
      error.status = response.status
      throw error
    }
    return response.blob()
  },
  list: async (patientId) =>
    request(`${API_BASE_URL}/patients/${patientId}/documents/`),
  upload: async (patientId, file, title, folder) => {
    const form = new FormData()
    form.append("file", file)
    if (title) form.append("title", title)
    if (folder) form.append("folder", folder)
    return request(`${API_BASE_URL}/patients/${patientId}/documents/`, {
      method: "POST",
      body: form,
    })
  },
  delete: async (docId) => {
    await request(`${API_BASE_URL}/patients/documents/${docId}/`, { method: "DELETE" })
    return true
  },
}

// Discharge readiness and the final bill of a stay (E7, E12, H8).
// GET /api/ipd/admissions/{id}/readiness/
api.ipd.admissions.readiness = async (id) =>
  request(`${API_BASE_URL}/ipd/admissions/${id}/readiness/`)
// GET /api/ipd/admissions/awaiting_final_bill/?hospital=<id> (billing roles)
api.ipd.admissions.awaitingFinalBill = async (hospitalId) =>
  request(`${API_BASE_URL}/ipd/admissions/awaiting_final_bill/?hospital=${encodeURIComponent(hospitalId)}`)
// POST /api/ipd/admissions/{id}/final_bill/  { daily_rate, items: [{ description, quantity, unit_price }] }
api.ipd.admissions.finalBill = async (id, data) =>
  request(`${API_BASE_URL}/ipd/admissions/${id}/final_bill/`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })
// Read-only security configuration (A14), Admin only.
// GET /api/auth/security-settings/
api.securitySettings = {
  get: async () => request(`${API_BASE_URL}/auth/security-settings/`),
}
// PATCH /api/ipd/discharge-plans/{id}/  e.g. { medications_reconciled: true }
api.ipd.dischargePlans.patch = async (id, data) =>
  request(`${API_BASE_URL}/ipd/discharge-plans/${id}/`, {
    method: "PATCH",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(data),
  })

// ER row actions (J3). Appended here so the ER and clinical blocks above stay untouched.
// POST /api/emergency/emergency-visits/{id}/add_note/  { note }
api.emergency.visits.addNote = async (id, note) =>
  request(`${API_BASE_URL}/emergency/emergency-visits/${id}/add_note/`, { method: "POST", ...jsonBody({ note }) })
// GET /api/emergency/emergency-visits/{id}/charge_slip/
api.emergency.visits.chargeSlip = async (id) =>
  request(`${API_BASE_URL}/emergency/emergency-visits/${id}/charge_slip/`)
// POST /api/emergency/emergency-visits/{id}/administer_medication/  { medication_id, administered_by? }
api.emergency.visits.administerMedication = async (id, data) =>
  request(`${API_BASE_URL}/emergency/emergency-visits/${id}/administer_medication/`, { method: "POST", ...jsonBody(data) })
// POST /api/emergency/emergency-visits/{id}/admit_to_ipd/  { bed_id }
api.emergency.visits.admitToIpd = async (id, bedId) =>
  request(`${API_BASE_URL}/emergency/emergency-visits/${id}/admit_to_ipd/`, { method: "POST", ...jsonBody({ bed_id: bedId }) })
// GET /api/clinical/allergies/?patient=<id>; POST { patient, name, reaction, severity }.
// Any allergies helpers defined above take precedence.
api.clinical.allergies = {
  list: async ({ patientId } = {}) => {
    const query = patientId ? `?patient=${encodeURIComponent(patientId)}` : ""
    return request(`${API_BASE_URL}/clinical/allergies/${query}`)
  },
  create: async (data) =>
    request(`${API_BASE_URL}/clinical/allergies/`, { method: "POST", ...jsonBody(data) }),
  ...api.clinical.allergies,
}

export default api

