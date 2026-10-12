import {
  useMutation,
  useQuery,
  useQueryClient,
  type QueryClient,
} from '@tanstack/react-query'
import { useEffect, useMemo, useRef, useState, type FormEvent } from 'react'
import { Navigate } from 'react-router-dom'
import * as messagesApi from '../api/messages'
import * as sessionsApi from '../api/sessions'
import type { ChatMessage, ChatSession, TutorAvatar } from '../api/types'
import { MessageBubble } from '../components/MessageBubble'
import { TrashButton } from '../components/TrashButton'
import { VoiceFacePicker } from '../components/VoiceFacePicker'
import { AudioPlayerProvider } from '../context/AudioPlayerContext'
import { useAuth } from '../context/AuthContext'
import { AppShell } from '../layout/AppShell'

function sessionActivityTime(session: ChatSession): number {
  const raw = session.last_user_message_at ?? session.created_at
  return new Date(raw).getTime()
}

function sortSessionsByRecent(sessions: ChatSession[]): ChatSession[] {
  return [...sessions].sort(
    (a, b) => sessionActivityTime(b) - sessionActivityTime(a),
  )
}

function upsertSessionInCache(
  queryClient: QueryClient,
  session: ChatSession,
): void {
  queryClient.setQueryData<ChatSession[]>(['sessions'], (old) => {
    const prev = old ?? []
    const idx = prev.findIndex((s) => s.id === session.id)
    if (idx >= 0) {
      const next = [...prev]
      next[idx] = { ...next[idx], ...session }
      return next
    }
    return [session, ...prev]
  })
}

function sidebarLabel(session: ChatSession): string {
  const title = session.title?.trim()
  if (!title || title === 'New chat') {
    return 'New chat'
  }
  return title
}

export function ChatPage() {
  const { user, loading } = useAuth()
  const queryClient = useQueryClient()
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [draft, setDraft] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const awaitingNewSessionRef = useRef(false)

  const sessionsQuery = useQuery({
    queryKey: ['sessions'],
    queryFn: sessionsApi.listSessions,
    enabled: !!user,
  })

  const messagesQuery = useQuery({
    queryKey: ['messages', sessionId],
    queryFn: () => messagesApi.listMessages(sessionId!),
    enabled: !!sessionId,
  })

  const createSession = useMutation({
    mutationFn: () => sessionsApi.createSession(),
    onSuccess: (session) => {
      awaitingNewSessionRef.current = false
      upsertSessionInCache(queryClient, session)
      setSessionId(session.id)
      void queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })

  const sortedSessions = useMemo(() => {
    const fromApi = sortSessionsByRecent(sessionsQuery.data ?? [])
    if (!sessionId || fromApi.some((s) => s.id === sessionId)) {
      return fromApi
    }
    const fromCreate =
      createSession.data?.id === sessionId ? createSession.data : null
    const stub: ChatSession = fromCreate ?? {
      id: sessionId,
      title: 'New chat',
      tutor_tone: 'socratic',
      tutor_avatar: 'female',
      status: 'active',
      owner_id: '',
      created_at: new Date().toISOString(),
      last_user_message_at: null,
    }
    return sortSessionsByRecent([stub, ...fromApi])
  }, [sessionsQuery.data, sessionId, createSession.data])

  const activeSession = sortedSessions.find((s) => s.id === sessionId)

  useEffect(() => {
    if (awaitingNewSessionRef.current || createSession.isPending) {
      return
    }
    if (!sessionId && sortedSessions.length) {
      setSessionId(sortedSessions[0].id)
    }
  }, [sessionId, sortedSessions, createSession.isPending])

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messagesQuery.data])

  useEffect(() => {
    if (
      sessionsQuery.isSuccess &&
      sessionsQuery.data?.length === 0 &&
      !createSession.isPending &&
      !createSession.isSuccess
    ) {
      createSession.mutate()
    }
  }, [
    sessionsQuery.isSuccess,
    sessionsQuery.data,
    createSession.isPending,
    createSession.isSuccess,
    createSession,
  ])

  const deleteSession = useMutation({
    mutationFn: (id: string) => sessionsApi.deleteSession(id),
    onSuccess: async (_data, deletedId) => {
      const wasOpen = deletedId === sessionId
      queryClient.removeQueries({ queryKey: ['messages', deletedId] })
      await queryClient.invalidateQueries({ queryKey: ['sessions'] })
      if (!wasOpen) {
        return
      }
      awaitingNewSessionRef.current = true
      setSessionId(null)
      setDraft('')
      createSession.mutate()
    },
  })

  const sendMessage = useMutation({
    mutationFn: (content: string) =>
      messagesApi.sendMessage(sessionId!, content),
    onSuccess: (exchange) => {
      queryClient.setQueryData(['messages', sessionId], (old: unknown) => {
        const prev = (old as ChatMessage[] | undefined) ?? []
        return [...prev, exchange.user_message, exchange.assistant_message]
      })
      upsertSessionInCache(queryClient, {
        ...exchange.session,
        last_user_message_at:
          exchange.session.last_user_message_at ?? new Date().toISOString(),
      })
      void queryClient.invalidateQueries({ queryKey: ['sessions'] })
      setDraft('')
    },
  })

  const setVoice = useMutation({
    mutationFn: (avatar: TutorAvatar) =>
      sessionsApi.updateSessionAvatar(sessionId!, avatar),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sessions'] })
    },
  })

  if (!loading && !user) {
    return <Navigate to="/login" replace />
  }

  const sessionVoice: TutorAvatar = activeSession?.tutor_avatar ?? 'female'
  const canPickVoice =
    !!sessionId && !sendMessage.isPending && !setVoice.isPending

  const onVoiceChange = (avatar: TutorAvatar) => {
    if (!canPickVoice || sessionVoice === avatar) return
    setVoice.mutate(avatar)
  }

  const onSubmit = (e: FormEvent) => {
    e.preventDefault()
    const text = draft.trim()
    if (!text || !sessionId || sendMessage.isPending) return
    sendMessage.mutate(text)
  }

  const sidebar = (
    <aside
      className="flex w-64 shrink-0 flex-col border-r border-slate-200 bg-white dark:border-slate-800 dark:bg-slate-900"
    >
      <div className="p-3">
        <button
          type="button"
          onClick={() => createSession.mutate()}
          className="w-full rounded-lg bg-miit-600 py-2 text-sm font-semibold text-white hover:bg-miit-700"
        >
          New chat
        </button>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 pb-4">
        {sortedSessions.map((session) => (
          <div
            key={session.id}
            className={`mb-1 flex items-center gap-1 rounded-lg ${
              session.id === sessionId ? 'bg-blue-50 dark:bg-slate-800' : ''
            }`}
          >
            <button
              type="button"
              onClick={() => setSessionId(session.id)}
              className="min-w-0 flex-1 truncate px-3 py-2 text-left text-sm"
            >
              {sidebarLabel(session)}
            </button>
            <TrashButton
              onClick={() => {
                if (confirm('Delete this chat?')) {
                  deleteSession.mutate(session.id)
                }
              }}
            />
          </div>
        ))}
      </nav>
    </aside>
  )

  return (
    <AudioPlayerProvider>
      <AppShell sidebar={sidebar}>
        <div className="flex min-h-0 flex-1 flex-col bg-slate-50/50 dark:bg-slate-950">
          <div className="flex-1 overflow-y-auto px-4 py-6">
            {!sessionId && (
              <p className="text-center text-slate-500">
                Create a chat to get started.
              </p>
            )}
            <div className="mx-auto flex max-w-3xl flex-col gap-4">
              {(messagesQuery.data ?? []).map((msg) => (
                <MessageBubble
                  key={msg.id}
                  message={msg}
                  sessionId={sessionId!}
                />
              ))}
              {sendMessage.isPending && (
                <p className="text-sm text-slate-500">Generating answer…</p>
              )}
              <div ref={bottomRef} />
            </div>
          </div>
          <form
            onSubmit={onSubmit}
            className="border-t border-slate-200 bg-white p-4 dark:border-slate-800 dark:bg-slate-900"
          >
            <div className="mx-auto flex max-w-3xl flex-col gap-2">
              <div className="flex gap-2">
                {canPickVoice && (
                  <div className="flex shrink-0 flex-col items-center justify-end gap-1 pb-1">
                    <VoiceFacePicker
                      value={sessionVoice}
                      onChange={onVoiceChange}
                    />
                  </div>
                )}
                <textarea
                  value={draft}
                  onChange={(e) => setDraft(e.target.value)}
                  rows={2}
                  disabled={!sessionId || sendMessage.isPending}
                  placeholder="Message MIIT… MIIT ဆိုတာ ဘာလဲ။"
                  className="flex-1 resize-none rounded-xl border border-slate-300 px-3 py-2 text-sm dark:border-slate-600 dark:bg-slate-800"
                />
                <button
                  type="submit"
                  disabled={!sessionId || sendMessage.isPending || !draft.trim()}
                  className="self-end rounded-xl bg-miit-600 px-5 py-2 text-sm font-semibold text-white hover:bg-miit-700 disabled:opacity-50"
                >
                  Ask
                </button>
              </div>
            </div>
          </form>
        </div>
      </AppShell>
    </AudioPlayerProvider>
  )
}
