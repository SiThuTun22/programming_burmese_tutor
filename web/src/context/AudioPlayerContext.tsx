import { createContext, useContext } from 'react'
import { useAudioPlayer } from '../hooks/useAudioPlayer'

type Player = ReturnType<typeof useAudioPlayer>

const AudioPlayerContext = createContext<Player | null>(null)

export function AudioPlayerProvider({ children }: { children: React.ReactNode }) {
  const player = useAudioPlayer()
  return (
    <AudioPlayerContext.Provider value={player}>
      {children}
    </AudioPlayerContext.Provider>
  )
}

export function useSharedAudioPlayer(): Player {
  const ctx = useContext(AudioPlayerContext)
  if (!ctx) {
    throw new Error('useSharedAudioPlayer outside AudioPlayerProvider')
  }
  return ctx
}
