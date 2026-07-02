import { Controller, useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { Loader2 } from 'lucide-react'
import { toast } from 'sonner'
import { Button } from '@/components/ui/button'
import { Switch } from '@/components/ui/switch'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { useUpdateSettings } from '../hooks/use-settings'
import { aiPreferencesSchema, type AiPreferencesFormValues } from '../types'
import { SettingsRow, SettingsSection } from './SettingsSection'

const SENSITIVITY_OPTIONS: { value: AiPreferencesFormValues['riskSensitivity']; label: string }[] = [
  { value: 'conservative', label: 'Conservative — flag only high-confidence risks' },
  { value: 'balanced', label: 'Balanced — recommended for most teams' },
  { value: 'aggressive', label: 'Aggressive — surface every potential risk' },
]

export function AiPreferencesForm({ defaultValues }: { defaultValues: AiPreferencesFormValues }) {
  const { mutateAsync, isPending } = useUpdateSettings()

  const {
    handleSubmit,
    control,
    reset,
    watch,
    setValue,
    formState: { isDirty },
  } = useForm<AiPreferencesFormValues>({
    resolver: zodResolver(aiPreferencesSchema),
    defaultValues,
  })

  const sensitivity = watch('riskSensitivity')
  const threshold = watch('minConfidenceThreshold')

  async function onSubmit(values: AiPreferencesFormValues) {
    await mutateAsync({ section: 'aiPreferences', values })
    reset(values)
    toast.success('AI preferences saved')
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <SettingsSection
        title="AI preferences"
        description="Control how Sentinel AI reviews, fixes, and recovers on your behalf."
        footer={
          <Button type="submit" size="sm" disabled={!isDirty || isPending}>
            {isPending && <Loader2 className="size-4 animate-spin" />}
            Save changes
          </Button>
        }
      >
        <SettingsRow
          label="Automatic fixes"
          description="Let Sentinel open PRs with suggested fixes automatically."
        >
          <Controller
            control={control}
            name="autoFixEnabled"
            render={({ field }) => (
              <Switch checked={field.value} onCheckedChange={field.onChange} aria-label="Automatic fixes" />
            )}
          />
        </SettingsRow>

        <SettingsRow
          label="Auto recovery"
          description="Let Sentinel restart or roll back unhealthy containers without approval."
        >
          <Controller
            control={control}
            name="autoRecoveryEnabled"
            render={({ field }) => (
              <Switch checked={field.value} onCheckedChange={field.onChange} aria-label="Auto recovery" />
            )}
          />
        </SettingsRow>

        <SettingsRow label="Risk sensitivity" description="How aggressively to flag risk.">
          <Select
            value={sensitivity}
            onValueChange={(v) =>
              setValue('riskSensitivity', v as AiPreferencesFormValues['riskSensitivity'], {
                shouldDirty: true,
              })
            }
          >
            <SelectTrigger className="w-full sm:w-80">
              <SelectValue placeholder="Select sensitivity" />
            </SelectTrigger>
            <SelectContent>
              {SENSITIVITY_OPTIONS.map((option) => (
                <SelectItem key={option.value} value={option.value}>
                  {option.label}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </SettingsRow>

        <SettingsRow
          label="Minimum confidence threshold"
          description="Only auto-apply fixes above this confidence level."
        >
          <div className="flex w-full items-center gap-3 sm:w-64">
            <input
              type="range"
              min={0}
              max={100}
              step={5}
              value={threshold}
              onChange={(e) =>
                setValue('minConfidenceThreshold', Number(e.target.value), { shouldDirty: true })
              }
              className="h-1.5 flex-1 cursor-pointer appearance-none rounded-full bg-surface-elevated accent-primary"
              aria-label="Minimum confidence threshold"
            />
            <span className="w-10 text-right font-mono-tabular text-sm text-foreground">
              {threshold}%
            </span>
          </div>
        </SettingsRow>
      </SettingsSection>
    </form>
  )
}
