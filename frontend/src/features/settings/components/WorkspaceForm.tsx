import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useUpdateSettings } from '../hooks/use-settings'
import { workspaceSchema, type WorkspaceFormValues } from '../types'
import { SettingsRow, SettingsSection } from './SettingsSection'

const TIMEZONES = [
  'America/New_York',
  'America/Los_Angeles',
  'Europe/London',
  'Europe/Berlin',
  'Asia/Kolkata',
  'Asia/Singapore',
]

export function WorkspaceForm({ defaultValues }: { defaultValues: WorkspaceFormValues }) {
  const { mutateAsync, isPending } = useUpdateSettings()

  const {
    register,
    handleSubmit,
    reset,
    watch,
    setValue,
    formState: { errors, isDirty },
  } = useForm<WorkspaceFormValues>({
    resolver: zodResolver(workspaceSchema),
    defaultValues,
  })

  const timezone = watch('timezone')

  async function onSubmit(values: WorkspaceFormValues) {
    await mutateAsync({ section: 'workspace', values })
    reset(values)
    toast.success('Workspace settings saved')
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <SettingsSection
        title="Workspace"
        description="General settings for your Sentinel AI workspace."
        footer={
          <Button type="submit" size="sm" disabled={!isDirty || isPending}>
            {isPending && <Loader2 className="size-4 animate-spin" />}
            Save changes
          </Button>
        }
      >
        <SettingsRow label="Workspace name" htmlFor="workspaceName">
          <div className="flex flex-col gap-1">
            <Input id="workspaceName" className="w-full sm:w-64" {...register('workspaceName')} />
            {errors.workspaceName && (
              <span className="text-xs text-danger">{errors.workspaceName.message}</span>
            )}
          </div>
        </SettingsRow>

        <SettingsRow label="Timezone" description="Used for reports and digests.">
          <Select value={timezone} onValueChange={(v) => setValue('timezone', v, { shouldDirty: true })}>
            <SelectTrigger className="w-full sm:w-64">
              <SelectValue placeholder="Select timezone" />
            </SelectTrigger>
            <SelectContent>
              {TIMEZONES.map((tz) => (
                <SelectItem key={tz} value={tz}>
                  {tz}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </SettingsRow>

        <SettingsRow label="Default branch" description="Branch treated as production.">
          <div className="flex flex-col gap-1">
            <Input id="defaultBranch" className="w-full sm:w-64" {...register('defaultBranch')} />
            {errors.defaultBranch && (
              <span className="text-xs text-danger">{errors.defaultBranch.message}</span>
            )}
          </div>
        </SettingsRow>
      </SettingsSection>
    </form>
  )
}
