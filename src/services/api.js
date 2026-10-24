const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

const ACCESS_TOKEN_KEY = 'access_token'
const REFRESH_TOKEN_KEY = 'refresh_token'

function getAccessToken() {
  return localStorage.getItem(ACCESS_TOKEN_KEY)
}

function getRefreshToken() {
  return localStorage.getItem(REFRESH_TOKEN_KEY)
}

function setTokens({ access, refresh } = {}) {
  if (access) localStorage.setItem(ACCESS_TOKEN_KEY, access)
  if (refresh) localStorage.setItem(REFRESH_TOKEN_KEY, refresh)
}

function clearTokens() {
  localStorage.removeItem(ACCESS_TOKEN_KEY)
  localStorage.removeItem(REFRESH_TOKEN_KEY)
}

function buildHeaders(extra = {}, body) {
  const headers = { ...extra }
  if (body && !(body instanceof FormData) && !headers['Content-Type']) {
    headers['Content-Type'] = 'application/json'
  }
  const token = getAccessToken()
  if (token && !headers.Authorization) {
    headers.Authorization = `Bearer ${token}`
  }
  return headers
}

function parseErrorDetail(body, status) {
  if (!body) return `Request failed (${status})`
  if (typeof body === 'string') return body
  return (
    body.detail ||
    body.error ||
    (typeof body === 'object' ? JSON.stringify(body) : `Request failed (${status})`)
  )
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
    '/auth/register/',
  ].some((path) => url.includes(path))
}

async function refreshAccessToken() {
  if (!refreshPromise) {
    refreshPromise = (async () => {
      const refresh = getRefreshToken()
      if (!refresh) {
        throw new Error('Session expired')
      }
      const response = await fetch(`${API_BASE_URL}/auth/token/refresh/`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ refresh }),
      })
      if (!response.ok) {
        throw new Error('Session expired')
      }
      const data = await response.json()
      setTokens({ access: data.access, refresh: data.refresh || refresh })
      return data.access
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
  window.dispatchEvent(new Event('auth:logout'))
}

// Shared request helper with consistent error handling.
async function request(url, options = {}) {
  let response
  const { headers: extraHeaders, _retried = false, ...rest } = options
  const headers = buildHeaders(extraHeaders || {}, rest.body)

  try {
    const timeoutSignal = rest.signal || AbortSignal.timeout(8000)
    response = await fetch(url, { ...rest, headers, signal: timeoutSignal })
  } catch (networkError) {
    throw new Error(
      networkError.message || 'Network error. Is the Django server running?'
    )
  }

  if (response.status === 401 && !_retried && shouldAttemptRefresh(url) && getRefreshToken()) {
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

    try {
      const body = await response.json()
      detail = parseErrorDetail(body, response.status)
    } catch (parseError) {
      // Response body was not JSON — keep the default message.
    }

    throw new Error(detail)
  }

  if (response.status === 204) {
    return null
  }

  return response.json()
}

function jsonBody(data) {
  return {
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  }
}

const api = {
  auth: {
    getTokens: () => ({
      accessToken: getAccessToken(),
      refreshToken: getRefreshToken(),
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
      const refresh = getRefreshToken()
      try {
        if (refresh) {
          await request(`${API_BASE_URL}/auth/staff/logout/`, {
            method: 'POST',
            ...jsonBody({ refresh }),
          })
        }
      } catch (error) {
        // Keep logout local even if the server call fails.
      }
      clearTokens()
      localStorage.removeItem('user')
      localStorage.removeItem('roles')
      localStorage.removeItem('hospitals')
    },
    register: async (payload) =>
      request(`${API_BASE_URL}/auth/register/`, {
        method: 'POST',
        ...jsonBody(payload),
      }),
    requestPatientOtp: async (phone) =>
      request(`${API_BASE_URL}/auth/patient/otp/request/`, {
        method: 'POST',
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
    applySession: (data) => {
      setTokens({ access: data?.access, refresh: data?.refresh })
      return data
    },
  },

  patients: {
    // GET /api/patients/ (optionally scoped to a hospital)
    list: async (hospitalId, page = 1) => {
      const params = new URLSearchParams()
      if (hospitalId) params.set('hospital', hospitalId)
      params.set('page', page)
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
    // GET /api/nurses/ (optionally scoped to a hospital)
    list: async (hospitalId) => {
      const query = hospitalId
        ? `?hospital=${encodeURIComponent(hospitalId)}`
        : ''

      return request(`${API_BASE_URL}/nurses/${query}`)
    },

    // GET /api/nurses/{id}/
    get: async (id) => request(`${API_BASE_URL}/nurses/${id}/`),

    // POST /api/nurses/
    create: async (data) =>
      request(`${API_BASE_URL}/nurses/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PUT /api/nurses/{id}/
    update: async (id, data) =>
      request(`${API_BASE_URL}/nurses/${id}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // PATCH /api/nurses/{id}/
    patch: async (id, data) =>
      request(`${API_BASE_URL}/nurses/${id}/`, {
        method: 'PATCH',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      }),

    // DELETE /api/nurses/{id}/
    delete: async (id) => {
      await request(`${API_BASE_URL}/nurses/${id}/`, {
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

    // GET /api/encounters/queue-tokens/{id}/estimate/
    estimate: async (id) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/${id}/estimate/`),

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

    // GET /api/encounters/queue-tokens/{id}/estimate/
    get: async (id) =>
      request(`${API_BASE_URL}/encounters/queue-tokens/${id}/estimate/`),
  },

  // Doctor queue dashboard
  doctorDashboard: {
    // GET /api/encounters/doctor-dashboard/?hospital=<id>&doctor=<id>
    get: async (hospitalId, doctorId = null) => {
      const params = new URLSearchParams()
      params.set('hospital', hospitalId)
      if (doctorId) params.set('doctor', doctorId)
      return request(`${API_BASE_URL}/encounters/doctor-dashboard/?${params.toString()}`)
    },
  },

  // Hospital queue overview (admin/front desk)
  hospitalQueue: {
    // GET /api/encounters/hospital-queue-overview/?hospital=<id>
    get: async (hospitalId) => {
      const query = hospitalId
        ? `?hospital=${encodeURIComponent(hospitalId)}`
        : ''
      return request(`${API_BASE_URL}/encounters/hospital-queue-overview/${query}`)
    },
  },

  // Voice fallback
  voiceFallback: {
    // POST /api/encounters/trigger-voice-fallback/
    trigger: async (queueTokenId, hospitalId) =>
      request(`${API_BASE_URL}/encounters/trigger-voice-fallback/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ queue_token: queueTokenId, hospital: hospitalId }),
      }),
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

  // AI Medical Scribe
  aiScribe: {
    // Consultations
    consultations: {
      list: async (hospitalId, params = {}) => {
        const queryParams = new URLSearchParams();
        if (hospitalId) queryParams.set('hospital', hospitalId);
        Object.entries(params).forEach(([key, value]) => {
          if (value !== undefined && value !== null) queryParams.set(key, value);
        });
        const query = queryParams.toString() ? `?${queryParams.toString()}` : '';
        return request(`${API_BASE_URL}/ai-scribe/consultations/${query}`);
      },
      get: async (id) => request(`${API_BASE_URL}/ai-scribe/consultations/${id}/`),
      create: async (data) =>
        request(`${API_BASE_URL}/ai-scribe/consultations/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      update: async (id, data) =>
        request(`${API_BASE_URL}/ai-scribe/consultations/${id}/`, {
          method: 'PUT',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      patch: async (id, data) =>
        request(`${API_BASE_URL}/ai-scribe/consultations/${id}/`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(data),
        }),
      end: async (id) =>
        request(`${API_BASE_URL}/ai-scribe/consultations/${id}/end/`, {
          method: 'POST',
        }),
    },

    // Audio Recordings
    audioRecordings: {
      list: async (hospitalId, consultationId = null) => {
        const params = new URLSearchParams();
        if (hospitalId) params.set('hospital', hospitalId);
        if (consultationId) params.set('consultation', consultationId);
        const query = params.toString() ? `?${params.toString()}` : '';
        return request(`${API_BASE_URL}/ai-scribe/audio-recordings/${query}`);
      },
      create: async (formData) =>
        request(`${API_BASE_URL}/ai-scribe/audio-recordings/`, {
          method: 'POST',
          body: formData,
        }),
    },

    // Transcripts
    transcripts: {
      list: async (hospitalId, consultationId = null) => {
        const params = new URLSearchParams();
        if (hospitalId) params.set('hospital', hospitalId);
        if (consultationId) params.set('consultation', consultationId);
        const query = params.toString() ? `?${params.toString()}` : '';
        return request(`${API_BASE_URL}/ai-scribe/transcripts/${query}`);
      },
      get: async (id) => request(`${API_BASE_URL}/ai-scribe/transcripts/${id}/`),
      transcribe: async (audioRecordingId, language) =>
        request(`${API_BASE_URL}/ai-scribe/transcripts/transcribe/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ audio_recording_id: audioRecordingId, language }),
        }),
    },

    // AI Drafts
    drafts: {
      list: async (hospitalId, consultationId = null, draftStatus = null) => {
        const params = new URLSearchParams();
        if (hospitalId) params.set('hospital', hospitalId);
        if (consultationId) params.set('consultation', consultationId);
        if (draftStatus) params.set('draft_status', draftStatus);
        const query = params.toString() ? `?${params.toString()}` : '';
        return request(`${API_BASE_URL}/ai-scribe/drafts/${query}`);
      },
      get: async (id) => request(`${API_BASE_URL}/ai-scribe/drafts/${id}/`),
      generate: async (consultationId, promptVersion = 'v1.0', regenerate = false) =>
        request(`${API_BASE_URL}/ai-scribe/drafts/generate/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ consultation_id: consultationId, prompt_version: promptVersion, regenerate }),
        }),
      approve: async (draftId, createClinicalNote = true) =>
        request(`${API_BASE_URL}/ai-scribe/drafts/${draftId}/approve/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'approve', create_clinical_note: createClinicalNote }),
        }),
      reject: async (draftId) =>
        request(`${API_BASE_URL}/ai-scribe/drafts/${draftId}/approve/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action: 'reject' }),
        }),
      review: async (draftId, action, editedStructuredData = null, editedSummaryText = null, reviewNotes = '') =>
        request(`${API_BASE_URL}/ai-scribe/drafts/${draftId}/review/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ action, edited_structured_data: editedStructuredData, edited_summary_text: editedSummaryText, review_notes: reviewNotes }),
        }),
      regenerate: async (consultationId, promptVersion = 'v1.0') =>
        request(`${API_BASE_URL}/ai-scribe/drafts/regenerate/`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ consultation_id: consultationId, prompt_version: promptVersion }),
        }),
    },

    // Reviews
    reviews: {
      list: async (aiDraftId) => {
        const params = new URLSearchParams();
        if (aiDraftId) params.set('ai_draft', aiDraftId);
        const query = params.toString() ? `?${params.toString()}` : '';
        return request(`${API_BASE_URL}/ai-scribe/reviews/${query}`);
      },
    },

    // Provider Status
    providerStatus: {
      get: async () => request(`${API_BASE_URL}/ai-scribe/provider-status/`),
    },
  },

  // Notifications
  notifications: {
    // GET /api/notifications/?hospital=<id>&patient=<id>
    list: async (hospitalId, patientId = null) => {
      const params = new URLSearchParams()
      params.set('hospital', hospitalId)
      if (patientId) params.set('patient', patientId)
      return request(`${API_BASE_URL}/notifications/?${params.toString()}`)
    },

    get: async (id) =>
      request(`${API_BASE_URL}/notifications/${id}/`),

    // POST /api/notifications/{id}/retry/
    retry: async (id) =>
      request(`${API_BASE_URL}/notifications/${id}/retry/`, {
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

    // Voice fallbacks
    voiceFallbacks: {
      // GET /api/notifications/voice-fallbacks/?hospital=<id>&queue_token=<id>
      list: async (hospitalId, queueTokenId = null) => {
        const params = new URLSearchParams()
        params.set('hospital', hospitalId)
        if (queueTokenId) params.set('queue_token', queueTokenId)
        return request(`${API_BASE_URL}/notifications/voice-fallbacks/?${params.toString()}`)
      },

      get: async (id) =>
        request(`${API_BASE_URL}/notifications/voice-fallbacks/${id}/`),
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

api.users = {
  me: async () => api.auth.getMe(),
  list: async (params = {}) => {
    const query = new URLSearchParams(params).toString()
    return request(`${API_BASE_URL}/users/${query ? `?${query}` : ""}`)
  },
}

api.hospitals = {
  list: async () => request(`${API_BASE_URL}/hospital/hospitals/`),
  get: async (id) => request(`${API_BASE_URL}/hospital/hospitals/${id}/`),
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
  return request(`${API_BASE_URL}/ipd/admissions/available_beds/${query}`)
}

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
    list: async () => request(`${API_BASE_URL}/notifications/consents/`),
  },
  records: {
    list: async (params = {}) => {
      const query = new URLSearchParams(params).toString()
      return request(`${API_BASE_URL}/notifications/consents/${query ? `?${query}` : ""}`)
    },
    sign: async (id, data) =>
      request(`${API_BASE_URL}/notifications/consents/${id}/sign/`, {
        method: "POST",
        ...jsonBody(data || {}),
      }),
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

export default api

