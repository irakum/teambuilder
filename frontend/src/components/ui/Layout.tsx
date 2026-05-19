import { Users } from 'lucide-react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../../contexts/AuthContext'

export default function Layout({ children }: { children: React.ReactNode }) {
  const { user } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen flex flex-col">
      <header className="bg-white border-b border-gray-200 sticky top-0 z-10">
        <div className="max-w-5xl mx-auto px-4 h-14 flex items-center justify-between gap-3">
          <Link to={user ? '/dashboard' : '/'} className="flex items-center gap-2 font-semibold text-gray-900 hover:text-primary-600">
            <Users className="h-5 w-5 text-primary-600" />
            TeamBuilder
          </Link>
          <div className="flex items-center gap-2">
            {user ? (
              <button
                onClick={() => navigate('/dashboard')}
                className="flex items-center gap-2 text-sm text-gray-600 hover:text-gray-900"
              >
                {user.avatar_url && (
                  <img src={user.avatar_url} alt={user.name} className="w-7 h-7 rounded-full" />
                )}
                <span className="hidden sm:block">{user.name}</span>
              </button>
            ) : (
              <Link to="/login" className="btn-secondary text-sm py-1.5">
                Увійти
              </Link>
            )}
          </div>
        </div>
      </header>
      <main className="flex-1 max-w-5xl mx-auto px-4 py-8 w-full">
        {children}
      </main>
    </div>
  )
}
