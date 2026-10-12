import { useAuth } from '../context/AuthContext'
import { useTheme } from '../hooks/useTheme'

type Props = {
  children: React.ReactNode
  sidebar?: React.ReactNode
}

export function AppShell({ children, sidebar }: Props) {
  const { user, logout } = useAuth()
  const { dark, toggle } = useTheme()

  return (
    <div className="flex h-full min-h-0 flex-col">
      <header className="flex shrink-0 items-center justify-between gap-4 border-b border-slate-200 bg-white/80 px-4 py-3 backdrop-blur dark:border-slate-800 dark:bg-slate-950/80">
        <div className="flex items-center gap-3">
          <img
            src="/miit-logo.png"
            alt="MIIT"
            className="h-10 w-10 rounded-lg object-contain"
          />
          <div>
            <h1 className="text-lg font-semibold tracking-tight text-miit-900 dark:text-blue-100">
              Computer Engineering Tutor
            </h1>
            <p className="text-xs text-slate-500 dark:text-slate-400">
              MIIT · Burmese programming &amp; campus help
            </p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <button
            type="button"
            onClick={toggle}
            className="rounded-lg border border-slate-200 px-3 py-1.5 text-xs font-medium dark:border-slate-700"
          >
            {dark ? 'Light' : 'Dark'}
          </button>
          {user && (
            <>
              <span className="hidden text-sm text-slate-600 sm:inline dark:text-slate-400">
                {user.display_name}
              </span>
              <button
                type="button"
                onClick={logout}
                className="rounded-lg bg-slate-100 px-3 py-1.5 text-xs font-medium dark:bg-slate-800"
              >
                Log out
              </button>
            </>
          )}
        </div>
      </header>
      <div className="flex min-h-0 flex-1">
        {sidebar}
        <main className="flex min-h-0 min-w-0 flex-1 flex-col">{children}</main>
      </div>
    </div>
  )
}
