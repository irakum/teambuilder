import { useState, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { UserPlus, Upload, Trash2, Play, ArrowRight, X } from 'lucide-react'
import Layout from '../components/ui/Layout'
import Spinner from '../components/ui/Spinner'
import SkillBadge from '../components/ui/SkillBadge'
import { sessionsApi, participantsApi, distributionApi } from '../api/sessions'
import { getErrorMessage } from '../api/client'
import type { SkillIn } from '../types'

export default function SessionPage() {
  const { id: sessionId } = useParams<{ id: string }>()!
  const navigate = useNavigate()
  const qc = useQueryClient()

  // ── Форма учасника ──────────────────────────────────────────────────────────
  const [name, setName] = useState('')
  const [skills, setSkills] = useState<SkillIn[]>([{ name: '', level: 3 }])
  const [tags, setTags] = useState('')
  const [showForm, setShowForm] = useState(false)
  const fileRef = useRef<HTMLInputElement>(null)

  const { data: session, isLoading } = useQuery({
    queryKey: ['session', sessionId],
    queryFn: () => sessionsApi.get(sessionId!),
    enabled: !!sessionId,
    refetchInterval: false,
  })

  const addSkillRow = () => setSkills(s => [...s, { name: '', level: 3 }])
  const removeSkillRow = (i: number) => setSkills(s => s.filter((_, idx) => idx !== i))
  const updateSkill = (i: number, field: keyof SkillIn, value: string | number) =>
    setSkills(s => s.map((sk, idx) => idx === i ? { ...sk, [field]: value } : sk))

  const addMutation = useMutation({
    mutationFn: (data: Parameters<typeof participantsApi.add>[1]) =>
      participantsApi.add(sessionId!, data),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['session', sessionId] })
      toast.success('Учасника додано')
      setName(''); setSkills([{ name: '', level: 3 }]); setTags(''); setShowForm(false)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const deleteMutation = useMutation({
    mutationFn: (pid: string) => participantsApi.delete(sessionId!, pid),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['session', sessionId] })
      toast.success('Учасника видалено')
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const importMutation = useMutation({
    mutationFn: (file: File) => participantsApi.importCsv(sessionId!, file),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ['session', sessionId] })
      toast.success(res.message)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const distributeMutation = useMutation({
    mutationFn: () => distributionApi.distribute(sessionId!, { use_compatibility: true }),
    onSuccess: () => {
      // Інвалідуємо кеш — ResultsPage зробить свіжий запит і покаже спінер поки чекає
      qc.removeQueries({ queryKey: ['session', sessionId] })
      toast.success('Розподіл виконано!')
      navigate(`/session/${sessionId}/results`)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const handleAddParticipant = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return toast.error("Введіть ім'я учасника")
    const validSkills = skills.filter(s => s.name.trim())
    const tagList = tags.split(',').map(t => t.trim()).filter(Boolean)
    addMutation.mutate({ name: name.trim(), skills: validSkills, compatibility_tags: tagList })
  }

  if (isLoading) return (
    <Layout>
      <div className="flex justify-center pt-20"><Spinner size="lg" /></div>
    </Layout>
  )

  if (!session) return (
    <Layout>
      <div className="text-center pt-20 text-gray-500">Сесію не знайдено</div>
    </Layout>
  )

  const isPending = session.status === 'pending'

  return (
    <Layout>
      <div className="space-y-6">
        {/* Header */}
        <div className="flex items-start justify-between gap-4">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{session.name}</h1>
            <p className="text-gray-500 mt-1">
              {session.participants.length} учасників · {session.team_count} команди
            </p>
          </div>
          <div className="flex gap-2 flex-shrink-0">
            {session.status === 'distributed' && (
              <button
                className="btn-secondary"
                onClick={() => navigate(`/session/${sessionId}/results`)}
              >
                <ArrowRight className="h-4 w-4" />
                Результати
              </button>
            )}
            {isPending && (
              <button
                className="btn-primary"
                onClick={() => distributeMutation.mutate()}
                disabled={distributeMutation.isPending || session.participants.length < session.team_count}
              >
                <Play className="h-4 w-4" />
                {distributeMutation.isPending ? 'Розподіл...' : 'Розподілити'}
              </button>
            )}
          </div>
        </div>

        {/* Add participant controls */}
        {isPending && (
          <div className="flex gap-2">
            <button className="btn-secondary" onClick={() => setShowForm(f => !f)}>
              <UserPlus className="h-4 w-4" />
              Додати учасника
            </button>
            <button className="btn-secondary" onClick={() => fileRef.current?.click()}>
              <Upload className="h-4 w-4" />
              {importMutation.isPending ? 'Імпорт...' : 'Імпорт CSV'}
            </button>
            <input
              ref={fileRef} type="file" accept=".csv" className="hidden"
              onChange={e => { const f = e.target.files?.[0]; if (f) importMutation.mutate(f) }}
            />
          </div>
        )}

        {/* Add participant form */}
        {showForm && isPending && (
          <div className="card p-5">
            <div className="flex justify-between items-center mb-4">
              <h3 className="font-semibold">Новий учасник</h3>
              <button onClick={() => setShowForm(false)}>
                <X className="h-4 w-4 text-gray-400 hover:text-gray-600" />
              </button>
            </div>
            <form onSubmit={handleAddParticipant} className="space-y-4">
              <div>
                <label className="label">Ім'я</label>
                <input className="input" placeholder="Іван Петренко"
                  value={name} onChange={e => setName(e.target.value)} />
              </div>

              <div>
                <div className="flex justify-between items-center mb-2">
                  <label className="label mb-0">Навички</label>
                  <button type="button" className="text-sm text-primary-600 hover:underline" onClick={addSkillRow}>
                    + додати
                  </button>
                </div>
                <div className="space-y-2">
                  {skills.map((sk, i) => (
                    <div key={i} className="flex gap-2 items-center">
                      <input className="input" placeholder="Python" value={sk.name}
                        onChange={e => updateSkill(i, 'name', e.target.value)} />
                      <select className="input w-24 flex-shrink-0" value={sk.level}
                        onChange={e => updateSkill(i, 'level', Number(e.target.value))}>
                        {[1,2,3,4,5].map(l => <option key={l} value={l}>{l}</option>)}
                      </select>
                      {skills.length > 1 && (
                        <button type="button" onClick={() => removeSkillRow(i)}>
                          <X className="h-4 w-4 text-gray-400 hover:text-red-500" />
                        </button>
                      )}
                    </div>
                  ))}
                </div>
              </div>

              <div>
                <label className="label">Теги сумісності <span className="text-gray-400 font-normal">(через кому)</span></label>
                <input className="input" placeholder="leader, backend"
                  value={tags} onChange={e => setTags(e.target.value)} />
              </div>

              <div className="flex gap-2">
                <button type="submit" className="btn-primary" disabled={addMutation.isPending}>
                  {addMutation.isPending ? 'Збереження...' : 'Додати'}
                </button>
                <button type="button" className="btn-secondary" onClick={() => setShowForm(false)}>
                  Скасувати
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Participants list */}
        <div className="card overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 bg-gray-50">
            <span className="text-sm font-medium text-gray-600">
              Учасники ({session.participants.length})
            </span>
          </div>
          {session.participants.length === 0 ? (
            <div className="text-center py-12 text-gray-400">
              <UserPlus className="h-8 w-8 mx-auto mb-2 opacity-40" />
              <p>Учасників ще немає</p>
            </div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {session.participants.map(p => (
                <li key={p.id} className="px-5 py-3 flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2">
                      <span className="font-medium text-gray-900">{p.name}</span>
                      <span className="text-xs text-gray-400">score: {p.total_score.toFixed(1)}</span>
                    </div>
                    {p.skills.length > 0 && (
                      <div className="flex flex-wrap gap-1 mt-1">
                        {p.skills.map(sk => <SkillBadge key={sk.name} skill={sk} />)}
                      </div>
                    )}
                    {p.compatibility_tags.length > 0 && (
                      <div className="flex gap-1 mt-1">
                        {p.compatibility_tags.map(t => (
                          <span key={t} className="badge bg-purple-50 text-purple-700">{t}</span>
                        ))}
                      </div>
                    )}
                  </div>
                  {isPending && (
                    <button
                      onClick={() => deleteMutation.mutate(p.id)}
                      className="text-gray-300 hover:text-red-500 transition-colors flex-shrink-0"
                    >
                      <Trash2 className="h-4 w-4" />
                    </button>
                  )}
                </li>
              ))}
            </ul>
          )}
        </div>

        {/* CSV hint */}
        {isPending && (
          <p className="text-xs text-gray-400 text-center">
            Формат CSV: <code>name,skills,tags</code> · Приклад рядка: <code>Іван,"Python:4,Design:3","leader"</code>
          </p>
        )}
      </div>
    </Layout>
  )
}
