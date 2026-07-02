import { StatCard } from '@/components/shared'
import { DollarSign, ShieldCheck, TrendingDown } from 'lucide-react'

export function ExecIntelligenceVisual() {
  return (
    <div className="grid grid-cols-1 gap-3 rounded-xl border border-border bg-surface p-2 shadow-xl shadow-black/30 sm:grid-cols-2">
      <div className="p-2">
        <StatCard
          label="Engineering health score"
          value="87/100"
          icon={ShieldCheck}
          trend={{ direction: 'up', changePercent: 4, isPositive: true }}
        />
      </div>
      <div className="p-2">
        <StatCard
          label="Infra cost this month"
          value="$18.2k"
          icon={DollarSign}
          trend={{ direction: 'down', changePercent: 12, isPositive: true }}
        />
      </div>
      <div className="col-span-full p-2 pt-0">
        <StatCard
          label="Cost saved via optimization"
          value="$4,900"
          icon={TrendingDown}
          helpText="Identified across 6 idle resources this quarter"
        />
      </div>
    </div>
  )
}
