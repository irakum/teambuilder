import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { Users, LogIn, Trophy, User } from 'lucide-react'
import { useAuth } from '../contexts/AuthContext'
import { apiClient } from '../api/client'
import Layout from '../components/ui/Layout'
import Spinner from '../components/ui/Spinner'
import SkillBadge from '../components/ui/SkillBadge'
import type { SessionOut } from '../types'

export default function JoinPage() {
  const { code } = useParams<{ code: string }>()!
  const { user, isLoading: authLoading } = useAuth()

  const { data: session, isLoading: sessionLoading, error } = useQuery({
    queryKey: ['invite', code],
    queryFn: () => apiClient.get<SessionOut>(`/invite/${code}`).then(r => r.data),
    enabled: !!code,
    retry: false,
  })

  const { data: myParticipant, error: meError } = useQuery({
    queryKey: ['invite-me', code],
    queryFn: () => apiClient.get(`/invite/${code}/me`).then(r => r.data),
    enabled: !!user && !!session,
    retry: false,
  })

  const handleGoogleLogin = () => {
    sessionStorage.setItem('join_invite_code', code!)
    const width = 500, height = 600
    const left = window.screenX + (window.outerWidth - width) / 2
    const top = window.screenY + (window.outerHeight - height) / 2
    window.open('/api/auth/google', 'google-auth', `width=${width},height=${height},left=${left},top=${top}`)
  }

  useEffect(() => {
    const pending = sessionStorage.getItem('join_invite_code')
    if (pending && user && pending === code) {
      sessionStorage.removeItem('join_invite_code')
    }
  }, [user])

  if (authLoading || sessionLoading) return (
    <div className="min-h-screen flex items-center justify-center">
      <Spinner size="lg" />
    </div>
  )

  if (error || !session) return (
    <Layout>
      <div className="text-center pt-20">
        <h1 className="text-2xl font-bold text-gray-900 mb-2">Посилання недійсне</h1>
        <p className="text-gray-500">Запрошення не знайдено або застаріло</p>
      </div>
    </Layout>
  )

  const myTeam = myParticipant && session.status === 'distributed'
    ? session.teams?.find(t => t.participants.some(p => p.id === myParticipant.id))
    : null

  return (
    <Layout>
      <div className="max-w-2xl mx-auto space-y-6">

        {/* Header */}
        <div className="text-center">
          <div className="inline-flex items-center justify-center w-16 h-16 bg-primary-100 rounded-2xl mb-4">
            <Users className="h-8 w-8 text-primary-600" />
          </div>
          <h1 className="text-2xl font-bold text-gray-900">{session.name}</h1>
          <p className="text-gray-500 mt-1">
            {session.participants.length} учасників · {session.team_count} команди
          </p>
        </div>

        {/* Авторизація / статус */}
        {!user ? (
          <div className="card p-6 text-center space-y-4">
            <p className="text-gray-600">Увійди через Google щоб побачити свою команду</p>
            <button
              onClick={handleGoogleLogin}
              className="w-full flex items-center justify-center gap-3 px-4 py-2.5 border border-gray-300 rounded-lg bg-white hover:bg-gray-50 transition-colors font-medium text-gray-700"
            >
              <svg className="h-5 w-5" viewBox="0 0 24 24">
                <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
                <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
                <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
                <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.47 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
              </svg>
              <LogIn className="h-4 w-4" />
              Увійти через Google
            </button>
          </div>
        ) : meError ? (
          <div className="card p-6 text-center text-red-600 font-medium">
            Ви не є учасником цього хакатону
          </div>
        ) : !myParticipant ? (
          <div className="card p-6 flex justify-center"><Spinner size="lg" /></div>
        ) : null}

        {/* Моя команда */}
        {myTeam && (
          <div className="card p-5 border-2 border-primary-200 bg-primary-50/30">
            <h2 className="text-lg font-semibold text-gray-900 mb-3 flex items-center gap-2">
              <Trophy className="h-5 w-5 text-yellow-500" />
              Моя команда — {myTeam.name}
            </h2>
            <ul className="divide-y divide-gray-100">
              {myTeam.participants.map(p => {
                const isMe = p.id === myParticipant!.id
                return (
                  <li key={p.id} className="py-2 flex items-center gap-2">
                    <User className={`h-4 w-4 flex-shrink-0 ${isMe ? 'text-primary-500' : 'text-gray-400'}`} />
                    <span className={`font-medium ${isMe ? 'text-primary-700' : 'text-gray-900'}`}>
                      {p.name}{isMe ? ' (ви)' : ''}
                    </span>
                    <div className="flex flex-wrap gap-1 ml-1">
                      {p.skills.map(sk => <SkillBadge key={sk.name} skill={sk} />)}
                    </div>
                  </li>
                )
              })}
            </ul>
          </div>
        )}

        {/* Всі учасники */}
        <div className="card overflow-hidden">
          <div className="px-5 py-3 border-b border-gray-100 bg-gray-50">
            <span className="text-sm font-medium text-gray-600">
              Всі учасники ({session.participants.length})
            </span>
          </div>
          {session.participants.length === 0 ? (
            <div className="text-center py-8 text-gray-400">Учасників ще немає</div>
          ) : (
            <ul className="divide-y divide-gray-100">
              {session.participants.map(p => {
                const isMe = myParticipant && p.id === myParticipant.id
                return (
                  <li key={p.id} className={`px-5 py-3 flex items-center gap-3 ${isMe ? 'bg-primary-50' : ''}`}>
                    <User className={`h-4 w-4 flex-shrink-0 ${isMe ? 'text-primary-500' : 'text-gray-400'}`} />
                    <div className="flex-1 min-w-0">
                      <span className={`font-medium ${isMe ? 'text-primary-700' : 'text-gray-900'}`}>
                        {p.name}{isMe ? ' (ви)' : ''}
                      </span>
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
                  </li>
                )
              })}
            </ul>
          )}
        </div>

      </div>
    </Layout>
  )
}
