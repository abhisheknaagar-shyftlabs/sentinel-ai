import { motion } from 'motion/react'
import { GitPullRequest, ShieldCheck, TrendingUp } from 'lucide-react'

const outcomes = [
  {
    icon: GitPullRequest,
    title: 'Ship with certainty, not crossed fingers',
    copy: 'Every pull request gets scored for risk before it merges, so "it worked on my machine" stops being your deploy strategy.',
  },
  {
    icon: ShieldCheck,
    title: 'Sleep through the pager',
    copy: 'When something breaks in production, Sentinel already knows why — and it has usually recovered it before you even open your laptop.',
  },
  {
    icon: TrendingUp,
    title: 'Walk into planning with real numbers',
    copy: 'Turn engineering health, deployment readiness, and infrastructure spend into a story leadership actually trusts.',
  },
]

export function OutcomesSection() {
  return (
    <section id="outcomes" className="px-6 py-24">
      <div className="mx-auto flex max-w-6xl flex-col gap-12">
        <motion.div
          initial={{ opacity: 0, y: 16 }}
          whileInView={{ opacity: 1, y: 0 }}
          viewport={{ once: true, margin: '-80px' }}
          transition={{ duration: 0.5 }}
          className="mx-auto max-w-xl text-center"
        >
          <h2 className="text-3xl font-semibold tracking-tight text-foreground">
            This is what changes for your team
          </h2>
          <p className="mt-3 text-muted-foreground">
            Not another dashboard to check. A system that tells you what matters, before it becomes
            your problem.
          </p>
        </motion.div>

        <div className="grid grid-cols-1 gap-6 md:grid-cols-3">
          {outcomes.map((outcome, index) => (
            <motion.div
              key={outcome.title}
              initial={{ opacity: 0, y: 24 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-80px' }}
              transition={{ duration: 0.5, delay: index * 0.1 }}
              className="flex flex-col gap-4 rounded-xl border border-border bg-surface p-6 transition-colors hover:border-border-strong"
            >
              <div className="flex size-10 items-center justify-center rounded-lg bg-primary-muted">
                <outcome.icon className="size-5 text-primary" strokeWidth={1.75} />
              </div>
              <h3 className="text-lg font-semibold text-foreground">{outcome.title}</h3>
              <p className="text-sm text-muted-foreground">{outcome.copy}</p>
            </motion.div>
          ))}
        </div>
      </div>
    </section>
  )
}
