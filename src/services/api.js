const API_BASE_URL = 'http://localhost:8000/api'

// Shared request helper with consistent error handling.
async function request(url, options = {}) {
  let response

  try {
    response = await fetch(url, options)
  } catch (networkError) {
    throw new Error(
      networkError.message || 'Network error. Is the Django server running?'
    )
  }

  if (!response.ok) {
    let detail = `Request failed (${response.status})`

    try {
      const body = await response.json()
      detail =
        body.detail ||
        (typeof body === 'string' ? body : JSON.stringify(body))
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

const api = {
  patients: {
    // GET /api/patients/ (optionally scoped to a hospital)
    list: async (hospitalId) => {
      const query = hospitalId
        ? `?hospital=${encodeURIComponent(hospitalId)}`
        : ''

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

    // DELETE /api/encounters/queue-tokens/{id}/
    delete: async (id) => {
      await request(`${API_BASE_URL}/encounters/queue-tokens/${id}/`, {
        method: 'DELETE',
      })
      return true
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
}

export default api
