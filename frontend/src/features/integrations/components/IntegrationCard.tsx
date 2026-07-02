import { useState } from 'react'
import { AreaChart, Container, Flame, GitBranch, Loader2, type LucideIcon } from 'lucide-react'
import { toast } from 'sonner'
import { StatusBadge } from '@/components/shared'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { useConnectIntegration, useDisconnectIntegration } from '../hooks/use-integrations'
import type { Integration } from '../types'

const iconMap: Record<string, LucideIcon> = {
  github: GitBranch,
  docker: Container,
  prometheus: Flame,
  grafana: AreaChart,
}

// Only GitHub is backed by a stored credential - Docker is monitored live
// off the local daemon, so there's nothing for a user to manually connect.
const REQUIRES_TOKEN = new Set(['github'])

interface IntegrationCardProps {
  integration: Integration
}

export function IntegrationCard({ integration }: IntegrationCardProps) {
  const Icon = iconMap[integration.id] ?? GitBranch
  const isConnected = integration.status === 'connected'
  const hasError = integration.status === 'error'

  const [tokenDialogOpen, setTokenDialogOpen] = useState(false)
  const [token, setToken] = useState('')
  const [repoFullName, setRepoFullName] = useState('')

  const connect = useConnectIntegration()
  const disconnect = useDisconnectIntegration()
  const isPending = connect.isPending || disconnect.isPending

  function handleAction() {
    if (isConnected) {
      disconnect.mutate(integration.id, {
        onSuccess: () => toast.success(`${integration.name} disconnected`),
        onError: () => toast.error(`Couldn't disconnect ${integration.name}`),
      })
      return
    }

    if (REQUIRES_TOKEN.has(integration.id)) {
      setTokenDialogOpen(true)
      return
    }

    connect.mutate(
      { id: integration.id },
      {
        onSuccess: () => toast.success(`${integration.name} connected`),
        onError: () => toast.error(`Couldn't connect ${integration.name}`),
      },
    )
  }

  function handleTokenSubmit() {
    connect.mutate(
      { id: integration.id, personalAccessToken: token, repositoryFullName: repoFullName.trim() || undefined },
      {
        onSuccess: (updated) => {
          if (updated.repositoryError) {
            toast.success(`${integration.name} connected`)
            toast.error(`Connected, but couldn't track ${repoFullName}`, {
              description: updated.repositoryError,
            })
          } else if (updated.repositoryTracked) {
            toast.success(`${integration.name} connected and tracking ${updated.repositoryTracked}`)
          } else {
            toast.success(`${integration.name} connected`)
          }
          setTokenDialogOpen(false)
          setToken('')
          setRepoFullName('')
        },
        onError: () =>
          toast.error(`Couldn't connect ${integration.name}`, {
            description: 'Check that the token is valid and has repo access.',
          }),
      },
    )
  }

  return (
    <div className="flex flex-col gap-4 rounded-lg border border-border bg-card p-5">
      <div className="flex items-start justify-between gap-3">
        <div className="flex items-center gap-3">
          <span className="flex size-10 items-center justify-center rounded-lg border border-border bg-surface">
            <Icon className="size-5 text-foreground" strokeWidth={1.5} />
          </span>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-foreground">{integration.name}</span>
            {integration.connectedAccount && (
              <span className="font-mono-tabular text-xs text-subtle-foreground">
                {integration.connectedAccount}
              </span>
            )}
          </div>
        </div>
        <StatusBadge status={integration.status} />
      </div>

      <p className="text-sm text-muted-foreground">{integration.description}</p>

      <div className="mt-auto flex items-center justify-between gap-2 border-t border-border pt-4">
        <span className="text-xs text-subtle-foreground">
          {integration.lastSyncedAt ? `Last synced ${integration.lastSyncedAt}` : 'Not connected'}
        </span>
        <Button
          variant={isConnected ? 'outline' : 'default'}
          size="sm"
          onClick={handleAction}
          disabled={isPending}
        >
          {isPending && <Loader2 className="size-4 animate-spin" />}
          {isConnected ? 'Disconnect' : hasError ? 'Reconnect' : 'Connect'}
        </Button>
      </div>

      {REQUIRES_TOKEN.has(integration.id) && (
        <Dialog open={tokenDialogOpen} onOpenChange={setTokenDialogOpen}>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>Connect {integration.name}</DialogTitle>
              <DialogDescription>
                Paste a personal access token with repo access. It's encrypted at rest and never
                shown again after this.
              </DialogDescription>
            </DialogHeader>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor={`${integration.id}-pat`}>Personal access token</Label>
              <Input
                id={`${integration.id}-pat`}
                type="password"
                placeholder="ghp_..."
                autoComplete="off"
                value={token}
                onChange={(event) => setToken(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && token.trim()) handleTokenSubmit()
                }}
              />
            </div>

            <div className="flex flex-col gap-1.5">
              <Label htmlFor={`${integration.id}-repo`}>Repository to track (optional)</Label>
              <Input
                id={`${integration.id}-repo`}
                placeholder="owner/repo — e.g. expressjs/express"
                autoComplete="off"
                value={repoFullName}
                onChange={(event) => setRepoFullName(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === 'Enter' && token.trim()) handleTokenSubmit()
                }}
              />
              <p className="text-xs text-subtle-foreground">
                Any public repo works, not just your own. You can track more repos later.
              </p>
            </div>

            <DialogFooter>
              <Button variant="outline" onClick={() => setTokenDialogOpen(false)} disabled={connect.isPending}>
                Cancel
              </Button>
              <Button onClick={handleTokenSubmit} disabled={!token.trim() || connect.isPending}>
                {connect.isPending && <Loader2 className="size-4 animate-spin" />}
                Connect
              </Button>
            </DialogFooter>
          </DialogContent>
        </Dialog>
      )}
    </div>
  )
}
