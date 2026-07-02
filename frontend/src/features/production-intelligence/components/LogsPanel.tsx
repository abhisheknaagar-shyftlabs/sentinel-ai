import { useMemo, useState } from 'react'
import { Terminal } from 'lucide-react'
import { EmptyState, FilterBar, SearchInput } from '@/components/shared'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import { cn } from '@/utils/cn'
import type { LogEntry, LogLevel } from '../types'

interface LogsPanelProps {
  logs: LogEntry[]
}

const LEVEL_OPTIONS: (LogLevel | 'all')[] = ['all', 'error', 'warn', 'info', 'debug']

const levelStyles: Record<LogLevel, string> = {
  error: 'text-danger',
  warn: 'text-warning',
  info: 'text-info',
  debug: 'text-subtle-foreground',
}

export function LogsPanel({ logs }: LogsPanelProps) {
  const [search, setSearch] = useState('')
  const [level, setLevel] = useState<LogLevel | 'all'>('all')

  const filtered = useMemo(() => {
    return logs.filter((log) => {
      const matchesSearch =
        log.message.toLowerCase().includes(search.toLowerCase()) ||
        log.service.toLowerCase().includes(search.toLowerCase())
      const matchesLevel = level === 'all' || log.level === level
      return matchesSearch && matchesLevel
    })
  }, [logs, search, level])

  return (
    <div className="flex flex-col gap-4">
      <FilterBar>
        <SearchInput
          value={search}
          onChange={setSearch}
          placeholder="Search logs..."
          className="w-full sm:w-64"
        />
        <Select value={level} onValueChange={(v) => setLevel(v as LogLevel | 'all')}>
          <SelectTrigger className="w-36">
            <SelectValue placeholder="Level" />
          </SelectTrigger>
          <SelectContent>
            {LEVEL_OPTIONS.map((option) => (
              <SelectItem key={option} value={option} className="capitalize">
                {option === 'all' ? 'All levels' : option}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </FilterBar>

      {filtered.length === 0 ? (
        <EmptyState
          icon={Terminal}
          title="No log lines match your filters"
          description="Try a different search term or level."
        />
      ) : (
        <div className="overflow-x-auto rounded-lg border border-border bg-surface p-4 font-mono text-xs">
          {filtered.map((log) => (
            <div key={log.id} className="flex gap-3 py-1 whitespace-nowrap">
              <span className="shrink-0 text-subtle-foreground">{log.timestamp}</span>
              <span className={cn('w-12 shrink-0 font-semibold uppercase', levelStyles[log.level])}>
                {log.level}
              </span>
              <span className="shrink-0 text-primary">{log.service}</span>
              <span className="text-muted-foreground">{log.message}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
