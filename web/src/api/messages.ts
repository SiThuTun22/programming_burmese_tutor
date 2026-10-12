import { apiBlob, apiFetch } from './client'
import type { ChatMessage, MessageExchange, MessageSpeechStatus } from './types'

export async function listMessages(sessionId: string): Promise<ChatMessage[]> {
  return apiFetch<ChatMessage[]>(
    `/api/chat-sessions/${sessionId}/messages`,
  )
}

export async function sendMessage(
  sessionId: string,
  content: string,
): Promise<MessageExchange> {
  return apiFetch<MessageExchange>(
    `/api/chat-sessions/${sessionId}/messages`,
    {
      method: 'POST',
      body: JSON.stringify({ content }),
    },
  )
}

export async function fetchSpeechStatus(
  sessionId: string,
  messageId: string,
): Promise<MessageSpeechStatus> {
  return apiFetch<MessageSpeechStatus>(
    `/api/chat-sessions/${sessionId}/messages/${messageId}/speech/status`,
  )
}

export async function fetchSpeechBlob(
  sessionId: string,
  messageId: string,
): Promise<Blob> {
  return apiBlob(
    `/api/chat-sessions/${sessionId}/messages/${messageId}/speech`,
  )
}
