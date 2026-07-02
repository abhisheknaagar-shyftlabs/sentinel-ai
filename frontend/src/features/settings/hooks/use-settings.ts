import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { fetchSettings, updateSettings } from '../api/settings.api'
import type { SettingsData } from '../types'

export function useSettings() {
  return useQuery({
    queryKey: ['settings'],
    queryFn: fetchSettings,
  })
}

export function useUpdateSettings() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      section,
      values,
    }: {
      section: keyof SettingsData
      values: SettingsData[keyof SettingsData]
    }) => updateSettings(section, values),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['settings'] })
    },
  })
}
