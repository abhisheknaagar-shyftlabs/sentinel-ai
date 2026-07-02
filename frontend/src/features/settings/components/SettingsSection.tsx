import type { ReactNode } from 'react'

interface SettingsSectionProps {
  title: string
  description: string
  children: ReactNode
  footer?: ReactNode
}

export function SettingsSection({ title, description, children, footer }: SettingsSectionProps) {
  return (
    <section className="overflow-hidden rounded-lg border border-border bg-card">
      <div className="flex flex-col gap-1 border-b border-border p-5">
        <h2 className="text-base font-semibold text-foreground">{title}</h2>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="flex flex-col gap-5 p-5">{children}</div>
      {footer && (
        <div className="flex items-center justify-end gap-2 border-t border-border bg-surface px-5 py-3">
          {footer}
        </div>
      )}
    </section>
  )
}

interface SettingsRowProps {
  label: string
  description?: string
  htmlFor?: string
  children: ReactNode
}

export function SettingsRow({ label, description, htmlFor, children }: SettingsRowProps) {
  return (
    <div className="flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
      <div className="flex flex-col gap-0.5">
        <label htmlFor={htmlFor} className="text-sm font-medium text-foreground">
          {label}
        </label>
        {description && <p className="text-sm text-muted-foreground">{description}</p>}
      </div>
      <div className="shrink-0">{children}</div>
    </div>
  )
}
