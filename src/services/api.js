const API_BASE_URL = 'http://localhost:8000/api'

const api = {
  patients: {
    list: async () => {
      const response = await fetch(`${API_BASE_URL}/patients/`)
      return response.json()
    },

    create: async (data) => {
      const response = await fetch(`${API_BASE_URL}/patients/`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      return response.json()
    },

    update: async (id, data) => {
      const response = await fetch(`${API_BASE_URL}/patients/${id}/`, {
        method: 'PUT',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(data),
      })
      return response.json()
    },

    delete: async (id) => {
      const response = await fetch(`${API_BASE_URL}/patients/${id}/`, {
        method: 'DELETE',
      })
      return response.status === 204
    },
  },
}

export default api
