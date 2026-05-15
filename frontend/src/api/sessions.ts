import { apiClient } from './client'
import type {
  SessionIn, SessionOut,
  ParticipantIn, ParticipantUpdate, ParticipantOut,
  DistributeIn, MoveParticipantIn,
  ImportResultOut, MessageOut,
} from '../types'

// ── Sessions ──────────────────────────────────────────────────────────────────

export const sessionsApi = {
  create: (data: SessionIn) =>
    apiClient.post<SessionOut>('/sessions', data).then(r => r.data),

  get: (id: string) =>
    apiClient.get<SessionOut>(`/sessions/${id}`).then(r => r.data),

  delete: (id: string) =>
    apiClient.delete<MessageOut>(`/sessions/${id}`).then(r => r.data),

  close: (id: string) =>
    apiClient.patch<SessionOut>(`/sessions/${id}/close`).then(r => r.data),
}

// ── Participants ──────────────────────────────────────────────────────────────

export const participantsApi = {
  list: (sessionId: string) =>
    apiClient.get<ParticipantOut[]>(`/sessions/${sessionId}/participants`).then(r => r.data),

  add: (sessionId: string, data: ParticipantIn) =>
    apiClient.post<ParticipantOut>(`/sessions/${sessionId}/participants`, data).then(r => r.data),

  update: (sessionId: string, participantId: string, data: ParticipantUpdate) =>
    apiClient.patch<ParticipantOut>(
      `/sessions/${sessionId}/participants/${participantId}`, data
    ).then(r => r.data),

  delete: (sessionId: string, participantId: string) =>
    apiClient.delete<MessageOut>(
      `/sessions/${sessionId}/participants/${participantId}`
    ).then(r => r.data),

  importCsv: (sessionId: string, file: File) => {
    const form = new FormData()
    form.append('file', file)
    return apiClient.post<ImportResultOut>(
      `/sessions/${sessionId}/participants/import`,
      form,
      { headers: { 'Content-Type': 'multipart/form-data' } }
    ).then(r => r.data)
  },
}

// ── Distribution ──────────────────────────────────────────────────────────────

export const distributionApi = {
  distribute: (sessionId: string, data: DistributeIn = {}) =>
    apiClient.post<SessionOut>(`/sessions/${sessionId}/distribute`, data).then(r => r.data),

  moveParticipant: (sessionId: string, data: MoveParticipantIn) =>
    apiClient.patch<SessionOut>(`/sessions/${sessionId}/move-participant`, data).then(r => r.data),

  exportCsv: (sessionId: string) =>
    apiClient.get(`/sessions/${sessionId}/export/csv`, { responseType: 'blob' }).then(r => r.data),

  exportPdf: (sessionId: string) =>
    apiClient.get(`/sessions/${sessionId}/export/pdf`, { responseType: 'blob' }).then(r => r.data),
}
