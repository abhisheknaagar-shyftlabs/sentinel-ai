import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import type { IncidentAnalyticsPoint } from '../types'

interface IncidentAnalyticsChartProps {
  data: IncidentAnalyticsPoint[]
}

export function IncidentAnalyticsChart({ data }: IncidentAnalyticsChartProps) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <BarChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="var(--border)" vertical={false} />
        <XAxis
          dataKey="label"
          stroke="var(--subtle-foreground)"
          fontSize={12}
          tickLine={false}
          axisLine={false}
        />
        <YAxis
          stroke="var(--subtle-foreground)"
          fontSize={12}
          tickLine={false}
          axisLine={false}
          width={40}
          allowDecimals={false}
        />
        <Tooltip
          cursor={{ fill: 'var(--surface-hover)' }}
          contentStyle={{
            background: 'var(--popover)',
            border: '1px solid var(--border)',
            borderRadius: 8,
            fontSize: 12,
            color: 'var(--foreground)',
          }}
          labelStyle={{ color: 'var(--muted-foreground)' }}
        />
        <Bar dataKey="value" fill="var(--primary)" radius={[4, 4, 0, 0]} maxBarSize={36} />
      </BarChart>
    </ResponsiveContainer>
  )
}
