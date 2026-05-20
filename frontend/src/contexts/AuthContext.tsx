import { createContext, useContext, useState, useEffect, useCallback } from 'react'
import type { UserOut } from '../api/auth'
import { getStoredUser, setStoredUser, setJwtToken, clearAuth } from '../api/auth'

interface AuthContextValue {
  user: UserOut | null
  isLoading: boolean
  login: (token: string, user: UserOut) => void
  logout: () => void
}

const AuthContext = createContext<AuthContextValue>({
  user: null,
  isLoading: true,
  login: () => {},
  logout: () => {},
})

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserOut | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    // Відновлюємо сесію з localStorage
    const stored = getStoredUser()
    if (stored) setUser(stored)
    setIsLoading(false)
  }, [])

  // Слухаємо postMessage від OAuth popup
  useEffect(() => {
    const handler = (event: MessageEvent) => {
      if (event.origin !== window.location.origin) return
      if (event.data?.type === 'AUTH_SUCCESS') {
        const { token, user } = event.data
        setJwtToken(token)
        setStoredUser(user)
        setUser(user)
      }
    }
    window.addEventListener('message', handler)
    return () => window.removeEventListener('message', handler)
  }, [])

  const login = useCallback((token: string, user: UserOut) => {
    setJwtToken(token)
    setStoredUser(user)
    setUser(user)
  }, [])

  const logout = useCallback(() => {
    clearAuth()
    setUser(null)
  }, [])

  return (
    <AuthContext.Provider value={{ user, isLoading, login, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  return useContext(AuthContext)
}
