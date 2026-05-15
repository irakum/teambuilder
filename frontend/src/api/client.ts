import axios from 'axios'

export const apiClient = axios.create({
  baseURL: '/api',
  headers: { 'Content-Type': 'application/json' },
})

// Додає токен організатора до запитів якщо є в localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem('organizer_token')
  if (token) {
    config.headers['X-Organizer-Token'] = token
  }
  return config
})

// Витягує зрозуміле повідомлення про помилку з відповіді FastAPI
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
