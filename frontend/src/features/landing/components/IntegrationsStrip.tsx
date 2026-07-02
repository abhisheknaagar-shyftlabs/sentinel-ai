import { motion } from 'motion/react'
import { AreaChart, Container, Flame, GitBranch } from 'lucide-react'

const integrations = [
  { name: 'GitHub', icon: GitBranch },
  { name: 'Docker', icon: Container },
  { name: 'Prometheus', icon: Flame },
  { name: 'Grafana', icon: AreaChart },
]

export function IntegrationsStrip() {
  return (
    <section id="integrations" className="border-y border-border bg-surface/50 px-6 py-12">
      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true }}
        transition={{ duration: 0.5 }}
        className="mx-auto flex max-w-5xl flex-col items-center gap-6"
      >
        <p className="text-sm text-subtle-foreground">Plugs into the tools your team already runs on</p>
        <div className="flex flex-wrap items-center justify-center gap-x-12 gap-y-6">
          {integrations.map((integration) => (
            <div key={integration.name} className="flex items-center gap-2 text-muted-foreground">
              <integration.icon className="size-5" strokeWidth={1.5} />
              <span className="text-sm font-medium">{integration.name}</span>
            </div>
          ))}
        </div>
      </motion.div>
    </section>
  )
}
