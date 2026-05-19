import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Додає токени до запитів
apiClient.interceptors.request.use((config) => {
  // Organizer token для управління сесією
  const organizerToken = localStorage.getItem('organizer_token')
  if (organizerToken) {
    config.headers['X-Organizer-Token'] = organizerToken
  }

  // JWT для авторизованих запитів
  const jwtToken = localStorage.getItem('jwt_token')
  if (jwtToken) {
    config.headers['Authorization'] = `Bearer ${jwtToken}`
  }

  return config
})

export function getErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const detail = error.response?.data?.detail
    if (typeof detail === 'string') return detail
    if (Array.isArray(detail)) {
      return detail.map((e: { msg: string }) => e.msg).join(', ')
    }
  }
  return 'Невідома помилка'
}
