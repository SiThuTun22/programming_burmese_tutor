export type TutorAvatar = 'male' | 'female'
export type TutorTone = 'socratic' | 'strict_academic'
export type MessageRole = 'user' | 'assistant'

export interface UserMe {
  id: string
  email: string
  display_name: string
  is_active: boolean
}

export interface TokenResponse {
  access_token: string
  token_type: string
}

export interface ChatSession {
  id: string
  title: string
  tutor_tone: TutorTone
  tutor_avatar: TutorAvatar
  status: string
  owner_id: string
  created_at: string
  last_user_message_at: string | null
}

export interface ChatMessage {
  id: string
  chat_session_id: string
  role: MessageRole
  content: string
  tutor_avatar: TutorAvatar | null
  document_id: string | null
  document_filename: string | null
}

export interface MessageExchange {
  user_message: ChatMessage
  assistant_message: ChatMessage
  session: ChatSession
}

export interface MessageSpeechStatus {
  ready: boolean
  pending: boolean
}
