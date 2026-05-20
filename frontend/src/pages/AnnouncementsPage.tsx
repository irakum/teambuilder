import { useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { ArrowLeft, Megaphone, Send, Users, User, Shield } from 'lucide-react'
import Layout from '../components/ui/Layout'
import Spinner from '../components/ui/Spinner'
import { apiClient, getErrorMessage } from '../api/client'
import { useAuth } from '../contexts/AuthContext'
import { sessionsApi } from '../api/sessions'

interface AnnouncementOut {
  id: string
  content: string
  audience: 'all' | 'team' | 'participant'
  audience_label: string
  sender_name: string
  sender_avatar?: string
  created_at: string
  is_mine: boolean
}

interface TeamOption { id: string; name: string }
interface ParticipantOption { id: string; name: string }

const AUDIENCE_ICON = {
  all: <Users className="h-3.5 w-3.5" />,
  team: <Shield className="h-3.5 w-3.5" />,
  participant: <User className="h-3.5 w-3.5" />,
}

const AUDIENCE_COLOR = {
  all: 'bg-blue-50 text-blue-700',
  team: 'bg-green-50 text-green-700',
  participant: 'bg-purple-50 text-purple-700',
}

export default function AnnouncementsPage() {
  const { id: sessionId } = useParams<{ id: string }>()!
  const navigate = useNavigate()
  const { user } = useAuth()
  const qc = useQueryClient()

  const [content, setContent] = useState('')
  const [audience, setAudience] = useState<'all' | 'team' | 'participant'>('all')
  const [selectedTeam, setSelectedTeam] = useState<string>('')
  const [selectedParticipant, setSelectedParticipant] = useState<string>('')

  const { data: session, isLoading: sessionLoading } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionsApi.get(sessionId!),
    enabled: !!sessionId,
  })

  const { data: announcements, isLoading: annLoading } = useQuery({
    queryKey: ['announcements', sessionId],
    queryFn: () => apiClient.get<AnnouncementOut[]>(`/sessions/${sessionId}/announcements`).then(r => r.data),
    enabled: !!sessionId,
    refetchInterval: 15000,
  })

  const { data: organizers } = useQuery({
    queryKey: ['organizers', sessionId],
    queryFn: () => apiClient.get<any[]>(`/sessions/${sessionId}/organizers`).then(r => r.data),
    enabled: !!sessionId,
  })

  const isOrganizer = organizers?.some(o => o.user_id === user?.id) ?? false

  // Опції для вибору команди/учасника
  const teamOptions: TeamOption[] = session?.teams?.map(t => ({ id: t.id, name: t.name })) ?? []
  const participantOptions: ParticipantOption[] = session?.participants?.map(p => ({ id: p.id, name: p.name })) ?? []

  const sendMutation = useMutation({
    mutationFn: () => apiClient.post(`/sessions/${sessionId}/announcements`, {
      content,
      audience,
      team_id: audience === 'team' ? selectedTeam : null,
      participant_id: audience === 'participant' ? selectedParticipant : null,
    }).then(r => r.data),
    onSuccess: () => {
      toast.success('Оголошення надіслано')
      setContent('')
      qc.invalidateQueries({ queryKey: ['announcements', sessionId] })
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const handleSend = () => {
    if (!content.trim()) return toast.error('Введіть текст оголошення')
    if (audience === 'team' && !selectedTeam) return toast.error('Оберіть команду')
    if (audience === 'participant' && !selectedParticipant) return toast.error('Оберіть учасника')
    sendMutation.mutate()
  }

  const formatDate = (iso: string) => {
    const d = new Date(iso)
    return d.toLocaleDateString('uk-UA', { day: 'numeric', month: 'long' }) + ' ' +
      d.toLocaleTimeString('uk-UA', { hour: '2-digit', minute: '2-digit' })
  }

  if (sessionLoading) return (
    <Layout><div className="flex justify-center pt-20"><Spinner size="lg" /></div></Layout>
  )

  return (
    <Layout>
      <div className="max-w-2xl mx-auto space-y-6">

        {/* Header */}
        <div>
          <button
            className="text-sm text-gray-400 hover:text-gray-600 flex items-center gap-1 mb-2"
            onClick={() => navigate(`/session/${sessionId}`)}
          >
            <ArrowLeft className="h-3.5 w-3.5" /> Назад
          </button>
          <h1 className="text-2xl font-bold text-gray-900 flex items-center gap-2">
            <Megaphone className="h-6 w-6 text-primary-500" />
            Оголошення — {session?.name}
          </h1>
        </div>

        {/* Форма для організатора */}
        {isOrganizer && (
          <div className="card p-5 space-y-4">
            <h2 className="font-semibold text-gray-900">Нове оголошення</h2>

            {/* Аудиторія */}
            <div>
              <label className="label">Кому</label>
              <div className="flex gap-2">
                {(['all', 'team', 'participant'] as const).map(a => (
                  <button
                    key={a}
                    onClick={() => { setAudience(a); setSelectedTeam(''); setSelectedParticipant('') }}
                    className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium border transition-colors ${
                      audience === a
                        ? 'bg-primary-500 text-white border-primary-500'
                        : 'bg-white text-gray-600 border-gray-200 hover:border-primary-300'
                    }`}
                  >
                    {AUDIENCE_ICON[a]}
                    {a === 'all' ? 'Всі' : a === 'team' ? 'Команда' : 'Учасник'}
                  </button>
                ))}
              </div>
            </div>

            {/* Вибір команди */}
            {audience === 'team' && (
              <div>
                <label className="label">Оберіть команду</label>
                <select
                  className="input"
                  value={selectedTeam}
                  onChange={e => setSelectedTeam(e.target.value)}
                >
                  <option value="">— оберіть —</option>
                  {teamOptions.map(t => (
                    <option key={t.id} value={t.id}>{t.name}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Вибір учасника */}
            {audience === 'participant' && (
              <div>
                <label className="label">Оберіть учасника</label>
                <select
                  className="input"
                  value={selectedParticipant}
                  onChange={e => setSelectedParticipant(e.target.value)}
                >
                  <option value="">— оберіть —</option>
                  {participantOptions.map(p => (
                    <option key={p.id} value={p.id}>{p.name}</option>
                  ))}
                </select>
              </div>
            )}

            {/* Текст */}
            <div>
              <label className="label">Текст оголошення</label>
              <textarea
                className="input resize-none"
                rows={4}
                placeholder="Введіть текст оголошення..."
                value={content}
                onChange={e => setContent(e.target.value)}
              />
            </div>

            <button
              className="btn-primary w-full justify-center"
              onClick={handleSend}
              disabled={sendMutation.isPending || !content.trim()}
            >
              <Send className="h-4 w-4" />
              {sendMutation.isPending ? 'Надсилання...' : 'Надіслати'}
            </button>
          </div>
        )}

        {/* Список оголошень */}
        <div className="space-y-3">
          {annLoading ? (
            <div className="flex justify-center pt-8"><Spinner size="lg" /></div>
          ) : !announcements?.length ? (
            <div className="card p-10 text-center text-gray-400">
              <Megaphone className="h-10 w-10 mx-auto mb-3 opacity-30" />
              <p>Оголошень ще немає</p>
            </div>
          ) : (
            announcements.map(ann => (
              <div key={ann.id} className="card p-4">
                <div className="flex items-start gap-3">
                  {ann.sender_avatar ? (
                    <img src={ann.sender_avatar} alt={ann.sender_name}
                      className="w-8 h-8 rounded-full flex-shrink-0 mt-0.5" />
                  ) : (
                    <div className="w-8 h-8 rounded-full bg-gray-200 flex-shrink-0 mt-0.5 flex items-center justify-center text-xs text-gray-500">
                      {ann.sender_name[0]}
                    </div>
                  )}
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 flex-wrap mb-1">
                      <span className="text-sm font-semibold text-gray-900">{ann.sender_name}</span>
                      <span className={`inline-flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium ${AUDIENCE_COLOR[ann.audience]}`}>
                        {AUDIENCE_ICON[ann.audience]}
                        {ann.audience_label}
                      </span>
                      <span className="text-xs text-gray-400">{formatDate(ann.created_at)}</span>
                    </div>
                    <p className="text-sm text-gray-800 whitespace-pre-wrap">{ann.content}</p>
                  </div>
                </div>
              </div>
            ))
          )}
        </div>

      </div>
    </Layout>
  )
}
