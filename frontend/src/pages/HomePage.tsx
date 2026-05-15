import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useMutation } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import { Users, Plus } from 'lucide-react'
import Layout from '../components/ui/Layout'
import { sessionsApi } from '../api/sessions'
import { getErrorMessage } from '../api/client'

export default function HomePage() {
  const navigate = useNavigate()
  const [name, setName] = useState('')
  const [teamCount, setTeamCount] = useState(3)
  const [minSize, setMinSize] = useState(1)
  const [maxSize, setMaxSize] = useState(10)

  const createMutation = useMutation({
    mutationFn: sessionsApi.create,
    onSuccess: (session) => {
      // Зберігаємо токен в localStorage для поточного сеансу
      if (session.organizer_token) {
        localStorage.setItem('organizer_token', session.organizer_token)
        localStorage.setItem(`token_${session.id}`, session.organizer_token)
      }
      toast.success('Сесію створено!')
      navigate(`/session/${session.id}`)
    },
    onError: (err) => toast.error(getErrorMessage(err)),
  })

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!name.trim()) return toast.error('Введіть назву події')
    createMutation.mutate({ name: name.trim(), team_count: teamCount, min_team_size: minSize, max_team_size: maxSize })
  }

  return (
    <Layout>
      <div className="max-w-md mx-auto">
        <div className="text-center mb-8">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-2xl mb-4">
            <Users className="h-8 w-8 text-primary-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">TeamBuilder</h1>
          <p className="text-gray-500 mt-2">Рівномірний розподіл учасників у команди</p>
        </div>

        <div className="card p-6">
          <h2 className="text-lg font-semibold mb-4">Нова сесія</h2>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label className="label">Назва події</label>
              <input
                className="input"
                placeholder="Наприклад: Хакатон 2026"
                value={name}
                onChange={e => setName(e.target.value)}
              />
            </div>

            <div>
              <label className="label">Кількість команд</label>
              <input
                type="number" min={2} max={20}
                className="input"
                value={teamCount}
                onChange={e => setTeamCount(Number(e.target.value))}
              />
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <label className="label">Мін. розмір команди</label>
                <input
                  type="number" min={1}
                  className="input"
                  value={minSize}
                  onChange={e => setMinSize(Number(e.target.value))}
                />
              </div>
              <div>
                <label className="label">Макс. розмір команди</label>
                <input
                  type="number" min={1}
                  className="input"
                  value={maxSize}
                  onChange={e => setMaxSize(Number(e.target.value))}
                />
              </div>
            </div>

            <button
              type="submit"
              className="btn-primary w-full justify-center"
              disabled={createMutation.isPending}
            >
              <Plus className="h-4 w-4" />
              {createMutation.isPending ? 'Створення...' : 'Створити сесію'}
            </button>
          </form>
        </div>

        <p className="text-center text-sm text-gray-400 mt-6">
          Після створення отримаєш посилання для учасників та токен організатора
        </p>
      </div>
    </Layout>
  )
}
