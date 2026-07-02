import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Switch } from '@/components/ui/switch'
import { useUpdateSettings } from '../hooks/use-settings'
import { notificationsSchema, type NotificationsFormValues } from '../types'
import { SettingsRow, SettingsSection } from './SettingsSection'

const TOGGLES: { name: keyof NotificationsFormValues; label: string; description: string }[] = [
  { name: 'incidentAlerts', label: 'Incident alerts', description: 'Notify me when a new incident opens.' },
  { name: 'prRiskAlerts', label: 'PR risk alerts', description: 'Notify me when a high-risk PR is opened.' },
  { name: 'weeklyDigest', label: 'Weekly digest', description: 'A Monday summary of engineering health.' },
  { name: 'costAlerts', label: 'Cost alerts', description: 'Notify me when infra spend exceeds budget.' },
]

export function NotificationsForm({ defaultValues }: { defaultValues: NotificationsFormValues }) {
  const { mutateAsync, isPending } = useUpdateSettings()

  const {
    register,
    handleSubmit,
    control,
    reset,
    formState: { errors, isDirty },
  } = useForm<NotificationsFormValues>({
    resolver: zodResolver(notificationsSchema),
    defaultValues,
  })

  async function onSubmit(values: NotificationsFormValues) {
    await mutateAsync({ section: 'notifications', values })
    reset(values)
    toast.success('Notification preferences saved')
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <SettingsSection
        title="Notifications"
        description="Choose what Sentinel AI alerts you about, and where."
        footer={
          <Button type="submit" size="sm" disabled={!isDirty || isPending}>
            {isPending && <Loader2 className="size-4 animate-spin" />}
            Save changes
          </Button>
        }
      >
        <SettingsRow label="Notification email" htmlFor="notificationEmail">
          <div className="flex flex-col gap-1">
            <Input
              id="notificationEmail"
              type="email"
              className="w-full sm:w-64"
              {...register('notificationEmail')}
            />
            {errors.notificationEmail && (
              <span className="text-xs text-danger">{errors.notificationEmail.message}</span>
            )}
          </div>
        </SettingsRow>

        {TOGGLES.map((toggle) => (
          <SettingsRow key={toggle.name} label={toggle.label} description={toggle.description}>
            <Controller
              control={control}
              name={toggle.name}
              render={({ field }) => (
                <Switch
                  checked={field.value as boolean}
                  onCheckedChange={field.onChange}
                  aria-label={toggle.label}
                />
              )}
            />
          </SettingsRow>
        ))}
      </SettingsSection>
    </form>
  )
}
