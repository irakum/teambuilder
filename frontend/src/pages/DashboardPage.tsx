import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import { Users, Trophy, LogOut, Plus, Eye, Trash2 } from 'lucide-react'
import toast from 'react-hot-toast'
import Layout from '../components/ui/Layout'
import Spinner from '../components/ui/Spinner'
import { useAuth } from '../contexts/AuthContext'
import { authApi } from '../api/auth'
import { sessionsApi } from '../api/sessions'
import type { SessionSummary } from '../api/auth'

const STATUS_LABEL: Record<string, string> = {
  pending: 'Очікує',
  distributed: 'Розподілено',
  closed: 'Закрито',
}

const STATUS_COLOR: Record<string, string> = {
  pending: 'bg-yellow-50 text-yellow-700',
  distributed: 'bg-green-50 text-green-700',
  closed: 'bg-gray-100 text-gray-500',
}

const ROLE_LABEL: Record<string, string> = {
  owner: '👑 Власник',
  'co-organizer': '⚙ Організатор',
  participant: '👤 Учасник',
}

const ROLE_COLOR: Record<string, string> = {
  owner: 'bg-amber-50 text-amber-700',
  'co-organizer': 'bg-blue-50 text-blue-700',
  participant: 'bg-purple-50 text-purple-700',
}

function SessionCard({ session, onOpen, onDelete }: { session: SessionSummary; onOpen: () => void; onDelete?: () => void }) {
  const isOrganizer = session.role === 'owner' || session.role === 'co-organizer'
  const isOwner = session.role === 'owner'
  return (
    <div className="card p-4 hover:shadow-md transition-shadow">
      <div className="flex items-start justify-between gap-3">
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2 flex-wrap">
            <span className="font-semibold text-gray-900 truncate">{session.name}</span>
            <span className={`badge ${STATUS_COLOR[session.status] ?? 'bg-gray-100 text-gray-500'}`}>
              {STATUS_LABEL[session.status] ?? session.status}
            </span>
            <span className={`badge ${ROLE_COLOR[session.role] ?? 'bg-gray-100 text-gray-500'}`}>
              {ROLE_LABEL[session.role] ?? session.role}
            </span>
          </div>
          <p className="text-sm text-gray-500 mt-1">
            {session.team_count} команди · {session.participant_count} учасників
          </p>
        </div>
        <div className="flex gap-2 flex-shrink-0">
          <button className="btn-secondary" onClick={onOpen}>
            {isOrganizer ? (
              <><Users className="h-4 w-4" /> Управляти</>
            ) : (
              <><Eye className="h-4 w-4" /> Переглянути</>
            )}
          </button>
          {isOwner && onDelete && (
            <button className="btn-secondary text-red-500 hover:text-red-700 hover:border-red-300" onClick={onDelete}>
              <Trash2 className="h-4 w-4" />
            </button>
          )}
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { user, logout, isLoading: authLoading } = useAuth()
  const navigate = useNavigate()
  const queryClient = useQueryClient()
  const [confirmDelete, setConfirmDelete] = useState<SessionSummary | null>(null)

  useEffect(() => {
    if (!authLoading && !user) navigate('/login')
  }, [user, authLoading, navigate])

  const deleteMutation = useMutation({
    mutationFn: (session: SessionSummary) => {
      // підставляємо токен саме цієї сесії
      const token = localStorage.getItem(`token_${session.id}`) || session.organizer_token || ''
      localStorage.setItem('organizer_token', token)
      return sessionsApi.delete(session.id)
    },
    onSuccess: (_, session) => {
      queryClient.setQueryData(['my-sessions'], (old: SessionSummary[] | undefined) =>
        old ? old.filter(s => s.id !== session.id) : []
      )
      toast.success('Хакатон видалено')
      setConfirmDelete(null)
    },
    onError: () => {
      toast.error('Не вдалося видалити хакатон')
      setConfirmDelete(null)
    },
  })

  const { data: sessions, isLoading } = useQuery({
    queryKey: ['my-sessions'],
    queryFn: authApi.getMySessions,
    enabled: !!user,
  })

  const handleOpen = (session: SessionSummary) => {
    if (session.role !== 'participant' && session.organizer_token) {
      localStorage.setItem('organizer_token', session.organizer_token)
    }
    if (session.status === 'distributed') {
      navigate(`/session/${session.id}/results`)
    } else {
      navigate(`/session/${session.id}`)
    }
  }

  if (authLoading) return (
    <div className="min-h-screen flex items-center justify-center">
      <Spinner size="lg" />
    </div>
  )

  const organizer = sessions?.filter(s => s.role === 'owner' || s.role === 'co-organizer') ?? []
  const participant = sessions?.filter(s => s.role === 'participant') ?? []

  return (
    <Layout>
      {/* Діалог підтвердження видалення */}
      {confirmDelete && (
        <div className="fixed inset-0 bg-black/40 flex items-center justify-center z-50">
          <div className="card p-6 max-w-sm w-full mx-4 shadow-xl">
            <h3 className="text-lg font-semibold text-gray-900 mb-2">Видалити хакатон?</h3>
            <p className="text-gray-500 text-sm mb-5">
              «{confirmDelete.name}» та всі його учасники будуть видалені назавжди.
            </p>
            <div className="flex gap-3 justify-end">
              <button className="btn-secondary" onClick={() => setConfirmDelete(null)}>
                Скасувати
              </button>
              <button
                className="btn-primary bg-red-600 hover:bg-red-700 border-red-600"
                disabled={deleteMutation.isPending}
                onClick={() => deleteMutation.mutate(confirmDelete)}
              >
                {deleteMutation.isPending ? 'Видалення...' : 'Видалити'}
              </button>
            </div>
          </div>
        </div>
      )}
      <div className="space-y-8">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-3">
            {user?.avatar_url && (
              <img src={user.avatar_url} alt={user.name} className="w-10 h-10 rounded-full" />
            )}
            <div>
              <h1 className="text-xl font-bold text-gray-900">{user?.name}</h1>
              <p className="text-sm text-gray-500">{user?.email}</p>
            </div>
          </div>
          <div className="flex gap-2">
            <button className="btn-primary" onClick={() => navigate('/create')}>
              <Plus className="h-4 w-4" /> Новий хакатон
            </button>
            <button className="btn-secondary" onClick={logout}>
              <LogOut className="h-4 w-4" /> Вийти
            </button>
          </div>
        </div>

        {isLoading ? (
          <div className="flex justify-center pt-10"><Spinner size="lg" /></div>
        ) : (
          <>
            <section>
              <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Users className="h-5 w-5 text-blue-500" />
                Мої хакатони ({organizer.length})
              </h2>
              {organizer.length === 0 ? (
                <div className="card p-8 text-center text-gray-400">
                  <p>Ти ще не створила жодного хакатону</p>
                  <button className="btn-primary mt-3" onClick={() => navigate('/create')}>
                    <Plus className="h-4 w-4" /> Створити
                  </button>
                </div>
              ) : (
                <div className="space-y-3">
                  {organizer.map(s => (
                    <SessionCard key={s.id} session={s} onOpen={() => handleOpen(s)} onDelete={() => setConfirmDelete(s)} />
                  ))}
                </div>
              )}
            </section>

            <section>
              <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
                <Trophy className="h-5 w-5 text-purple-500" />
                Я учасник ({participant.length})
              </h2>
              {participant.length === 0 ? (
                <div className="card p-8 text-center text-gray-400">
                  <p>Ти ще не брала участь у жодному хакатоні</p>
                </div>
              ) : (
                <div className="space-y-3">
                  {participant.map(s => (
                    <SessionCard key={s.id} session={s} onOpen={() => handleOpen(s)} />
                  ))}
                </div>
              )}
            </section>
          </>
        )}
      </div>
    </Layout>
  )
}