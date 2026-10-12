import { ApiError, apiFetch, getToken, setToken } from './client'
import type { TokenResponse, UserMe } from './types'

export async function register(
  email: string,
  displayName: string,
  password: string,
): Promise<UserMe> {
  return apiFetch<UserMe>('/api/auth/register', {
    method: 'POST',
    auth: false,
    body: JSON.stringify({
      email,
      display_name: displayName,
      password,
    }),
  })
}

export async function login(email: string, password: string): Promise<void> {
  const data = await apiFetch<TokenResponse>('/api/auth/login', {
    method: 'POST',
    auth: false,
    body: JSON.stringify({ email, password }),
  })
  setToken(data.access_token)
}

export async function fetchMe(): Promise<UserMe> {
  if (!getToken()) {
    throw new ApiError(401, 'Not authenticated')
  }
  return apiFetch<UserMe>('/api/auth/me')
}

export function logout(): void {
  setToken(null)
}
