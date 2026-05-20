import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Download, RefreshCw, ArrowLeft, MoveRight } from 'lucide-react'
import Layout from '../components/ui/Layout'
import Spinner from '../components/ui/Spinner'
import SkillBadge from '../components/ui/SkillBadge'
import { sessionsApi, distributionApi } from '../api/sessions'
import { apiClient, getErrorMessage } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import type { ParticipantOut, TeamOut } from '../types'

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url; a.download = filename; a.click()
  URL.revokeObjectURL(url)
}

export default function ResultsPage() {
  const { id: sessionId } = useParams<{ id: string }>()!
  const navigate = useNavigate()
  const qc = useQueryClient()

  const { user } = useAuth()
  const [movingParticipant, setMovingParticipant] = useState<ParticipantOut | null>(null)

  const { data: session, isLoading, isFetching } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionsApi.get(sessionId!),
    enabled: !!sessionId,
    // Повторюємо запит поки статус не стане distributed
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data || data.status !== 'distributed' || data.teams.length === 0) {
        return 1500
      }
      return false
    },
  })

  const { data: myParticipant } = useQuery({
    queryKey: ['session-me', sessionId],
    queryFn: () => apiClient.get(`/sessions/${sessionId}/participants/me`).then(r => r.data),
    enabled: !!user && !!sessionId,
    retry: false,
  })

  const redistributeMutation = useMutation({
    mutationFn: () => distributionApi.distribute(sessionId!, { use_compatibility: true }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['session', sessionId] })
      toast.success('Розподіл оновлено')
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const moveMutation = useMutation({
    mutationFn: (targetTeamId: string) =>
      distributionApi.moveParticipant(sessionId!, {
        participant_id: movingParticipant!.id,
        target_team_id: targetTeamId,
      }),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['session', sessionId] })
      toast.success('Учасника переміщено')
      setMovingParticipant(null)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const exportCsv = async () => {
    try {
      const blob = await distributionApi.exportCsv(sessionId!)
      downloadBlob(blob, `session_${sessionId}.csv`)
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  const exportPdf = async () => {
    try {
      const blob = await distributionApi.exportPdf(sessionId!)
      downloadBlob(blob, `session_${sessionId}.pdf`)
    } catch (err) {
      toast.error(getErrorMessage(err))
    }
  }

  // Показуємо спінер поки дані не завантажились або поки немає команд
  const isReady = session && session.status === 'distributed' && session.teams.length > 0

  if (isLoading || !session || !isReady) {
    return (
      <Layout>
        <div className="flex flex-col items-center justify-center pt-32 gap-4">
          <Spinner size="lg" />
          <p className="text-gray-500 text-sm">
            {isFetching ? 'Завантаження результатів...' : 'Очікуємо результати розподілу...'}
          </p>
        </div>
      </Layout>
    )
  }

  const scores = session.teams.map(t => t.total_score)
  const maxScore = Math.max(...scores)

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4 flex-wrap">
          <div>
            <button
              className="text-sm text-gray-400 hover:text-gray-600 flex items-center gap-1 mb-2"
              onClick={() => navigate(`/session/${sessionId}`)}
            >
              <ArrowLeft className="h-3.5 w-3.5" /> Учасники
            </button>
            <h1 className="text-2xl font-bold text-gray-900">Результати: {session.name}</h1>
            <p className="text-gray-500 mt-1">
              {session.participants.length} учасників · {session.teams.length} команди
            </p>
          </div>
          <div className="flex gap-2 flex-wrap">
            <button className="btn-secondary" onClick={exportCsv}>
              <Download className="h-4 w-4" /> CSV
            </button>
            <button className="btn-secondary" onClick={exportPdf}>
              <Download className="h-4 w-4" /> PDF
            </button>
            <button
              className="btn-secondary"
              onClick={() => redistributeMutation.mutate()}
              disabled={redistributeMutation.isPending}
            >
              <RefreshCw className="h-4 w-4" />
              {redistributeMutation.isPending ? 'Розподіл...' : 'Повторити'}
            </button>
          </div>
        </div>

        {/* Balance bar */}
        <div className="card p-4">
          <p className="text-sm font-medium text-gray-600 mb-3">Баланс рейтингів команд</p>
          <div className="space-y-2">
            {session.teams.map(team => (
              <div key={team.id} className="flex items-center gap-3">
                <span className="text-sm text-gray-600 w-24 flex-shrink-0 truncate">{team.name}</span>
                <div className="flex-1 bg-gray-100 rounded-full h-2">
                  <div
                    className="bg-primary-500 h-2 rounded-full transition-all"
                    style={{ width: maxScore > 0 ? `${(team.total_score / maxScore) * 100}%` : '0%' }}
                  />
                </div>
                <span className="text-sm font-medium text-gray-700 w-12 text-right flex-shrink-0">
                  {team.total_score.toFixed(1)}
                </span>
              </div>
            ))}
          </div>
        </div>

        {/* Move mode hint */}
        {movingParticipant && (
          <div className="bg-yellow-50 border border-yellow-200 rounded-lg px-4 py-3 flex items-center justify-between">
            <span className="text-sm text-yellow-800">
              Переміщення: <strong>{movingParticipant.name}</strong> — оберіть цільову команду
            </span>
            <button className="text-sm text-yellow-600 hover:underline" onClick={() => setMovingParticipant(null)}>
              Скасувати
            </button>
          </div>
        )}

        {/* Teams grid */}
        <div className="grid gap-4 md:grid-cols-2">
          {session.teams.map((team: TeamOut) => {
            const isMyTeam = myParticipant && team.participants.some(p => p.id === myParticipant.id)
            return (
            <div
              key={team.id}
              className={`card overflow-hidden transition-all ${
                movingParticipant && movingParticipant.team_id !== team.id
                  ? 'ring-2 ring-primary-400 cursor-pointer hover:shadow-md'
                  : isMyTeam ? 'ring-2 ring-primary-300 shadow-md'
                  : ''
              }`}
              onClick={() => {
                if (movingParticipant && movingParticipant.team_id !== team.id) {
                  moveMutation.mutate(team.id)
                }
              }}
            >
              <div className={`px-4 py-3 border-b border-gray-100 flex justify-between items-center ${isMyTeam ? 'bg-primary-50' : 'bg-gray-50'}`}>
                <span className="font-semibold text-gray-800 flex items-center gap-2">
                  {team.name}
                  {isMyTeam && <span className="text-xs text-primary-600 font-normal">(моя команда)</span>}
                </span>
                <span className="text-xs text-gray-400">
                  {team.participants.length} учасників · score {team.total_score.toFixed(1)}
                </span>
              </div>
              <ul className="divide-y divide-gray-50">
                {team.participants.map(p => {
                  const isMe = myParticipant && p.id === myParticipant.id
                  return (
                  <li key={p.id} className={`px-4 py-2.5 flex items-start gap-2 ${isMe ? 'bg-primary-50/50' : ''}`}>
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1.5">
                        <span className={`text-sm font-medium ${isMe ? 'text-primary-700' : 'text-gray-900'}`}>
                          {p.name}{isMe ? ' (ви)' : ''}
                        </span>
                        <span className="text-xs text-gray-400">{p.total_score.toFixed(1)}</span>
                      </div>
                      {p.skills.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {p.skills.map(sk => <SkillBadge key={sk.name} skill={sk} />)}
                        </div>
                      )}
                      {p.compatibility_tags.length > 0 && (
                        <div className="flex flex-wrap gap-1 mt-1">
                          {p.compatibility_tags.map(t => (
                            <span key={t} className="badge bg-purple-50 text-purple-700">{t}</span>
                          ))}
                        </div>
                      )}
                    </div>
                    {!movingParticipant && session.status === 'distributed' && (
                      <button
                        title="Перемістити до іншої команди"
                        onClick={(e) => { e.stopPropagation(); setMovingParticipant(p) }}
                        className="text-gray-300 hover:text-primary-500 transition-colors mt-0.5 flex-shrink-0"
                      >
                        <MoveRight className="h-4 w-4" />
                      </button>
                    )}
                  </li>
                  )
                })}
              </ul>
            </div>
            )
          })}
        </div>
      </div>
    </Layout>
  )
}
