import { apiClient } from './client'

export interface UserOut {
  id: string
  email: string
  name: string
  avatar_url: string | null
}

export interface SessionSummary {
  id: string
  name: string
  status: string
  team_count: number
  participant_count: number
  role: 'organizer' | 'participant'
  organizer_token: string | null
}

export const authApi = {
  getMe: () =>
    apiClient.get<UserOut>('/auth/me').then(r => r.data),

  getMySessions: () =>
    apiClient.get<SessionSummary[]>('/dashboard/sessions').then(r => r.data),

  joinSession: (sessionId: string) =>
    apiClient.post(`/dashboard/sessions/${sessionId}/join`).then(r => r.data),

  googleLoginUrl: () => '/api/auth/google',
}

// ── Зберігання токена ────────────────────────────────────────

export function getJwtToken(): string | null {
  return localStorage.getItem('jwt_token')
}

export function setJwtToken(token: string): void {
  localStorage.setItem('jwt_token', token)
}

export function getStoredUser(): UserOut | null {
  const raw = localStorage.getItem('user')
  if (!raw) return null
  try { return JSON.parse(raw) } catch { return null }
}

export function setStoredUser(user: UserOut): void {
  localStorage.setItem('user', JSON.stringify(user))
}

export function clearAuth(): void {
  localStorage.removeItem('jwt_token')
  localStorage.removeItem('user')
}
