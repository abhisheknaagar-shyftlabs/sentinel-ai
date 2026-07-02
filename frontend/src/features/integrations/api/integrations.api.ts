import { httpClient } from '@/services/http-client'
import type { Integration } from '../types'

export async function fetchIntegrations(): Promise<Integration[]> {
  return httpClient.get<Integration[]>('/integrations')
}

export async function connectIntegration(
  id: string,
  personalAccessToken?: string,
  repositoryFullName?: string,
): Promise<Integration> {
  return httpClient.post<Integration>(`/integrations/${id}/connect`, {
    personalAccessToken,
    repositoryFullName,
  })
}

export async function disconnectIntegration(id: string): Promise<Integration> {
  return httpClient.post<Integration>(`/integrations/${id}/disconnect`)
}
