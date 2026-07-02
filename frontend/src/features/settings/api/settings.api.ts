import { httpClient } from '@/services/http-client'
import type { SettingsData } from '../types'

export async function fetchSettings(): Promise<SettingsData> {
  return httpClient.get<SettingsData>('/settings')
}

export async function updateSettings(
  section: keyof SettingsData,
  values: SettingsData[keyof SettingsData],
): Promise<void> {
  await httpClient.patch(`/settings/${section}`, values)
}
