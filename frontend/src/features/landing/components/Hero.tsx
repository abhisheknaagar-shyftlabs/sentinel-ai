import { motion } from 'motion/react'
import { ArrowRight, Sparkles } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ROUTES } from '@/routes/paths'
import { HeroPreview } from './HeroPreview'

export function Hero() {
  const navigate = useNavigate()

  return (
    <section className="flex flex-col items-center gap-12 px-6 pt-16 pb-24 text-center lg:pt-24">
      <motion.div
        initial={{ opacity: 0, y: 16 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="inline-flex items-center gap-1.5 rounded-full border border-border bg-surface px-3 py-1 text-xs font-medium text-muted-foreground"
      >
        <Sparkles className="size-3.5 text-primary" strokeWidth={2} />
        AI Engineering Control Center
      </motion.div>

      <motion.h1
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.05 }}
        className="max-w-3xl text-balance text-4xl font-semibold tracking-tight text-foreground sm:text-5xl lg:text-6xl"
      >
        Know what&rsquo;s breaking{' '}
        <span className="bg-gradient-to-r from-primary to-accent-cyan bg-clip-text text-transparent">
          before your customers do
        </span>
      </motion.h1>

      <motion.p
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.1 }}
        className="max-w-2xl text-balance text-lg text-muted-foreground"
      >
        Sentinel AI watches every pull request, every container, and every dollar of
        infrastructure spend — then tells your team exactly what needs attention next, before it
        turns into an incident, a missed deadline, or a budget surprise.
      </motion.p>

      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.6, delay: 0.15 }}
        className="flex flex-col items-center gap-3 sm:flex-row"
      >
        <Button size="lg" className="group gap-2 px-6" onClick={() => navigate(ROUTES.login)}>
          Get started
          <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
        </Button>
        <Button size="lg" variant="outline" className="px-6" asChild>
          <a href="#modules">Explore the platform</a>
        </Button>
      </motion.div>

      <HeroPreview />
    </section>
  )
}
