import type { ChatMessage } from '../api/types'
import { MarkdownMessage } from './MarkdownMessage'
import { SpeakButton } from './SpeakButton'
import { VoiceFacePicker } from './VoiceFacePicker'

type Props = {
  message: ChatMessage
  sessionId: string
}

export function MessageBubble({ message, sessionId }: Props) {
  const isUser = message.role === 'user'

  return (
    <div
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-[min(100%,42rem)] rounded-2xl px-4 py-3 shadow-sm ${
          isUser
            ? 'bg-miit-600 text-white'
            : 'border border-slate-200 bg-white text-slate-800 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-100'
        }`}
      >
        {isUser ? (
          <p className="whitespace-pre-wrap text-sm leading-relaxed">{message.content}</p>
        ) : (
          <MarkdownMessage content={message.content} />
        )}
        {!isUser && (
          <div className="mt-3 flex flex-wrap items-center justify-end gap-2">
            <VoiceFacePicker
              compact
              readOnly
              value={message.tutor_avatar ?? 'female'}
            />
            <SpeakButton sessionId={sessionId} messageId={message.id} />
          </div>
        )}
      </div>
    </div>
  )
}
