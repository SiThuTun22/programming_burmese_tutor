import { useQuery } from '@tanstack/react-query'
import { useRef, useState } from 'react'
import { fetchSpeechBlob, fetchSpeechStatus } from '../api/messages'
import { useSharedAudioPlayer } from '../context/AudioPlayerContext'

type Props = {
  sessionId: string
  messageId: string
}

function LoadingSpinner({ className }: { className?: string }) {
  return (
    <svg
      className={`animate-spin ${className ?? 'h-4 w-4'}`}
      viewBox="0 0 24 24"
      fill="none"
      aria-hidden
    >
      <circle
        className="opacity-25"
        cx="12"
        cy="12"
        r="10"
        stroke="currentColor"
        strokeWidth="3"
      />
      <path
        className="opacity-75"
        fill="currentColor"
        d="M4 12a8 8 0 018-8v4a4 4 0 00-4 4H4z"
      />
    </svg>
  )
}

export function SpeakButton({ sessionId, messageId }: Props) {
  const { toggle, isPlaying } = useSharedAudioPlayer()
  const cache = useRef<Map<string, Blob>>(new Map())
  const [fetchingPlay, setFetchingPlay] = useState(false)

  const statusQuery = useQuery({
    queryKey: ['speech-status', sessionId, messageId],
    queryFn: () => fetchSpeechStatus(sessionId, messageId),
    refetchInterval: (query) => {
      const data = query.state.data
      if (!data) {
        return 400
      }
      if (data.ready || !data.pending) {
        return false
      }
      return 400
    },
  })

  const prefetching =
    statusQuery.data?.pending === true && statusQuery.data?.ready !== true
  const loading = prefetching || fetchingPlay

  const onClick = async () => {
    if (loading || prefetching) {
      return
    }
    setFetchingPlay(true)
    try {
      await toggle(messageId, async () => {
        const hit = cache.current.get(messageId)
        if (hit) {
          return hit
        }
        const blob = await fetchSpeechBlob(sessionId, messageId)
        cache.current.set(messageId, blob)
        return blob
      })
    } finally {
      setFetchingPlay(false)
      void statusQuery.refetch()
    }
  }

  const playing = isPlaying(messageId)

  return (
    <button
      type="button"
      onClick={() => void onClick()}
      disabled={prefetching}
      className="inline-flex items-center gap-1 rounded-full border border-slate-200 bg-white px-2.5 py-1 text-xs font-medium text-slate-600 shadow-sm transition hover:border-miit-600 hover:text-miit-700 disabled:cursor-wait disabled:opacity-80 dark:border-slate-700 dark:bg-slate-900 dark:text-slate-300 dark:hover:border-blue-400 dark:hover:text-blue-300"
      title={
        prefetching
          ? 'Preparing speech…'
          : playing
            ? 'Pause'
            : 'Speak'
      }
      aria-label={
        prefetching
          ? 'Preparing speech'
          : playing
            ? 'Pause speech'
            : 'Speak answer'
      }
      aria-busy={loading}
    >
      {loading ? (
        <LoadingSpinner />
      ) : (
        <svg
          className="h-4 w-4"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          strokeWidth="2"
          aria-hidden
        >
          {playing ? (
            <>
              <rect x="6" y="5" width="4" height="14" rx="1" />
              <rect x="14" y="5" width="4" height="14" rx="1" />
            </>
          ) : (
            <>
              <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5" />
              <path d="M15.54 8.46a5 5 0 0 1 0 7.07" />
            </>
          )}
        </svg>
      )}
      Speak
    </button>
  )
}
