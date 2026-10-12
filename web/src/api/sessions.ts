import { apiFetch } from './client'
import type { ChatSession, TutorAvatar } from './types'

export async function listSessions(): Promise<ChatSession[]> {
  return apiFetch<ChatSession[]>('/api/chat-sessions/')
}

export async function createSession(title = 'New chat'): Promise<ChatSession> {
  return apiFetch<ChatSession>('/api/chat-sessions/', {
    method: 'POST',
    body: JSON.stringify({ title }),
  })
}

export async function deleteSession(sessionId: string): Promise<void> {
  await apiFetch<void>(`/api/chat-sessions/${sessionId}`, {
    method: 'DELETE',
  })
}

export async function updateSessionAvatar(
  sessionId: string,
  tutor_avatar: TutorAvatar,
): Promise<ChatSession> {
  return apiFetch<ChatSession>(`/api/chat-sessions/${sessionId}`, {
    method: 'PATCH',
    body: JSON.stringify({ tutor_avatar }),
  })
}
