import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import {
  connectIntegration,
  disconnectIntegration,
  fetchIntegrations,
} from '../api/integrations.api'
import type { Integration } from '../types'

const INTEGRATIONS_KEY = ['integrations']

export function useIntegrations() {
  return useQuery({
    queryKey: INTEGRATIONS_KEY,
    queryFn: fetchIntegrations,
  })
}

/** Replaces one integration in the cached list with the server's updated copy. */
function useIntegrationMutation(action: (id: string) => Promise<Integration>) {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: action,
    onSuccess: (updated) => {
      queryClient.setQueryData<Integration[]>(INTEGRATIONS_KEY, (list) =>
        list?.map((item) => (item.id === updated.id ? updated : item)),
      )
    },
  })
}

export function useConnectIntegration() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: ({
      id,
      personalAccessToken,
      repositoryFullName,
    }: {
      id: string
      personalAccessToken?: string
      repositoryFullName?: string
    }) => connectIntegration(id, personalAccessToken, repositoryFullName),
    onSuccess: (updated) => {
      queryClient.setQueryData<Integration[]>(INTEGRATIONS_KEY, (list) =>
        list?.map((item) => (item.id === updated.id ? updated : item)),
      )
    },
  })
}

export function useDisconnectIntegration() {
  return useIntegrationMutation(disconnectIntegration)
}
