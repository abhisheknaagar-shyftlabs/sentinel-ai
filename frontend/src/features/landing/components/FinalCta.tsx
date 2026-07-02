import { motion } from 'motion/react'
import { ArrowRight } from 'lucide-react'
import { useNavigate } from 'react-router-dom'
import { Button } from '@/components/ui/button'
import { ROUTES } from '@/routes/paths'

export function FinalCta() {
  const navigate = useNavigate()

  return (
    <section className="px-6 py-24">
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        whileInView={{ opacity: 1, y: 0 }}
        viewport={{ once: true, margin: '-80px' }}
        transition={{ duration: 0.6 }}
        className="mx-auto flex max-w-3xl flex-col items-center gap-6 rounded-2xl border border-border bg-surface px-8 py-16 text-center"
      >
        <h2 className="text-balance text-3xl font-semibold tracking-tight text-foreground sm:text-4xl">
          Your infrastructure already knows something&rsquo;s wrong.
          <br />
          Now you will too.
        </h2>
        <p className="max-w-xl text-muted-foreground">
          Set up Sentinel AI in minutes and get your first risk report before your next standup.
        </p>
        <Button size="lg" className="group gap-2 px-6" onClick={() => navigate(ROUTES.login)}>
          Get started
          <ArrowRight className="size-4 transition-transform group-hover:translate-x-0.5" />
        </Button>
      </motion.div>
    </section>
  )
}
