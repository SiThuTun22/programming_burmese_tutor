import type { ReactNode } from 'react'
import type { TutorAvatar } from '../api/types'

type Props = {
  value: TutorAvatar
  onChange?: (avatar: TutorAvatar) => void
  disabled?: boolean
  compact?: boolean
  readOnly?: boolean
}

/** Venus symbol (circle + cross). */
function FemaleGenderIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <circle cx="12" cy="9" r="5" />
      <path d="M12 14v7" />
      <path d="M9 18h6" />
    </svg>
  )
}

/** Mars symbol (circle + arrow). */
function MaleGenderIcon({ className }: { className?: string }) {
  return (
    <svg
      className={className}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="2"
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden
    >
      <circle cx="10" cy="14" r="5" />
      <path d="M14.5 9.5L21 3" />
      <path d="M16 3h5v5" />
    </svg>
  )
}

export function VoiceFacePicker({
  value,
  onChange,
  disabled,
  compact,
  readOnly,
}: Props) {
  const size = compact ? 'h-9 w-9' : 'h-10 w-10'
  const icon = compact ? 'h-5 w-5' : 'h-5 w-5'

  const base =
    'inline-flex items-center justify-center rounded-full border-2 transition focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-miit-600'

  const styles: Record<TutorAvatar, { selected: string; idle: string; idleReadOnly: string }> =
    {
      female: {
        selected:
          'border-pink-500 bg-pink-100 text-pink-600 shadow-sm dark:border-pink-400 dark:bg-pink-950/60 dark:text-pink-300',
        idle:
          'border-pink-200 bg-white text-pink-400 hover:border-pink-400 hover:bg-pink-50 hover:text-pink-600 dark:border-pink-900 dark:bg-slate-900 dark:text-pink-500/80',
        idleReadOnly:
          'border-pink-100 bg-pink-50/50 text-pink-200 dark:border-pink-950 dark:bg-slate-900/50 dark:text-pink-900',
      },
      male: {
        selected:
          'border-blue-500 bg-blue-100 text-blue-600 shadow-sm dark:border-blue-400 dark:bg-blue-950/60 dark:text-blue-300',
        idle:
          'border-blue-200 bg-white text-blue-400 hover:border-blue-400 hover:bg-blue-50 hover:text-blue-600 dark:border-blue-900 dark:bg-slate-900 dark:text-blue-500/80',
        idleReadOnly:
          'border-blue-100 bg-blue-50/50 text-blue-200 dark:border-blue-950 dark:bg-slate-900/50 dark:text-blue-900',
      },
    }

  const avatarClass = (avatar: TutorAvatar) => {
    const palette = styles[avatar]
    if (value === avatar) return palette.selected
    if (readOnly) return palette.idleReadOnly
    return palette.idle
  }

  const groupLabel = readOnly ? 'Voice used for this answer' : 'Tutor voice'

  const wrap = (avatar: TutorAvatar, label: string, iconEl: ReactNode) => {
    const className = `${base} ${size} ${avatarClass(avatar)} ${
      readOnly ? 'pointer-events-none cursor-default' : ''
    } ${disabled && !readOnly ? 'opacity-40' : ''}`

    if (readOnly) {
      return (
        <span title={label} aria-label={label} className={className}>
          {iconEl}
        </span>
      )
    }

    return (
      <button
        type="button"
        disabled={disabled}
        title={label}
        aria-label={label}
        aria-pressed={value === avatar}
        onClick={() => onChange?.(avatar)}
        className={className}
      >
        {iconEl}
      </button>
    )
  }

  return (
    <div
      className="inline-flex items-center gap-1.5"
      role="group"
      aria-label={groupLabel}
      title={readOnly ? groupLabel : undefined}
    >
      {wrap('female', 'Female voice', <FemaleGenderIcon className={icon} />)}
      {wrap('male', 'Male voice', <MaleGenderIcon className={icon} />)}
    </div>
  )
}
