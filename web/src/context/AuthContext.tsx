import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
} from 'react'
import { ApiError } from '../api/client'
import { getToken } from '../api/client'
import * as authApi from '../api/auth'
import type { UserMe } from '../api/types'

type AuthState = {
  user: UserMe | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (email: string, name: string, password: string) => Promise<void>
  logout: () => void
  refresh: () => Promise<void>
}

const AuthContext = createContext<AuthState | null>(null)

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<UserMe | null>(null)
  const [loading, setLoading] = useState(true)

  const refresh = useCallback(async () => {
    if (!getToken()) {
      setUser(null)
      return
    }
    try {
      const me = await authApi.fetchMe()
      setUser(me)
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        authApi.logout()
      }
      setUser(null)
    }
  }, [])

  useEffect(() => {
    refresh().finally(() => setLoading(false))
  }, [refresh])

  const login = useCallback(
    async (email: string, password: string) => {
      await authApi.login(email, password)
      await refresh()
    },
    [refresh],
  )

  const register = useCallback(
    async (email: string, name: string, password: string) => {
      try {
        await authApi.register(email, name, password)
      } catch (err) {
        if (!(err instanceof ApiError && err.status === 409)) {
          throw err
        }
      }
      await authApi.login(email, password)
      await refresh()
    },
    [refresh],
  )

  const logout = useCallback(() => {
    authApi.logout()
    setUser(null)
  }, [])

  const value = useMemo(
    () => ({ user, loading, login, register, logout, refresh }),
    [user, loading, login, register, logout, refresh],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthState {
  const ctx = useContext(AuthContext)
  if (!ctx) {
    throw new Error('useAuth outside AuthProvider')
  }
  return ctx
}
