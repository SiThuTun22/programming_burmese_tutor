import { useCallback, useEffect, useRef, useState } from 'react'

type ActiveClip = {
  messageId: string
  url: string
}

export function useAudioPlayer() {
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const activeRef = useRef<ActiveClip | null>(null)
  const [playingId, setPlayingId] = useState<string | null>(null)

  useEffect(() => {
    const audio = new Audio()
    audioRef.current = audio
    const onPlay = () => setPlayingId(activeRef.current?.messageId ?? null)
    const onPause = () => setPlayingId(null)
    const onEnded = () => setPlayingId(null)
    audio.addEventListener('play', onPlay)
    audio.addEventListener('pause', onPause)
    audio.addEventListener('ended', onEnded)
    return () => {
      audio.pause()
      audio.removeEventListener('play', onPlay)
      audio.removeEventListener('pause', onPause)
      audio.removeEventListener('ended', onEnded)
      if (activeRef.current?.url) {
        URL.revokeObjectURL(activeRef.current.url)
      }
    }
  }, [])

  const loadClip = useCallback((messageId: string, blob: Blob) => {
    const audio = audioRef.current
    if (!audio) return
    if (activeRef.current?.messageId === messageId && activeRef.current.url) {
      return activeRef.current.url
    }
    if (activeRef.current?.url) {
      URL.revokeObjectURL(activeRef.current.url)
    }
    const url = URL.createObjectURL(blob)
    activeRef.current = { messageId, url }
    audio.src = url
    return url
  }, [])

  const toggle = useCallback(
    async (messageId: string, blobLoader: () => Promise<Blob>) => {
      const audio = audioRef.current
      if (!audio) return

      if (activeRef.current?.messageId === messageId) {
        if (!audio.paused && !audio.ended) {
          audio.pause()
          return
        }
        if (audio.paused && !audio.ended) {
          await audio.play()
          return
        }
        if (audio.ended) {
          audio.currentTime = 0
          await audio.play()
          return
        }
      }

      const blob = await blobLoader()
      loadClip(messageId, blob)
      audio.currentTime = 0
      await audio.play()
    },
    [loadClip],
  )

  const isPlaying = useCallback(
    (messageId: string) => playingId === messageId,
    [playingId],
  )

  return {
    toggle,
    isPlaying,
    activeMessageId: activeRef.current?.messageId ?? null,
  }
}
