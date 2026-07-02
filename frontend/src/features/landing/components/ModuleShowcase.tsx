import type { ReactNode } from 'react'
import { motion } from 'motion/react'
import { Check } from 'lucide-react'
import { cn } from '@/utils/cn'

interface ModuleShowcaseProps {
  eyebrow: string
  title: string
  description: string
  features: string[]
  visual: ReactNode
  reverse?: boolean
}

export function ModuleShowcase({
  eyebrow,
  title,
  description,
  features,
  visual,
  reverse = false,
}: ModuleShowcaseProps) {
  return (
    <div className="grid grid-cols-1 items-center gap-10 lg:grid-cols-2 lg:gap-16">
      <motion.div
        initial={{ opacity: 0, x: reverse ? 24 : -24 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, margin: '-100px' }}
        transition={{ duration: 0.6 }}
        className={cn('flex flex-col gap-4', reverse && 'lg:order-2')}
      >
        <span className="text-xs font-semibold tracking-wide text-primary uppercase">{eyebrow}</span>
        <h3 className="text-2xl font-semibold tracking-tight text-foreground sm:text-3xl">{title}</h3>
        <p className="text-muted-foreground">{description}</p>
        <ul className="mt-2 flex flex-col gap-2.5">
          {features.map((feature) => (
            <li key={feature} className="flex items-center gap-2.5 text-sm text-foreground">
              <span className="flex size-4 shrink-0 items-center justify-center rounded-full bg-success-muted">
                <Check className="size-2.5 text-success" strokeWidth={3} />
              </span>
              {feature}
            </li>
          ))}
        </ul>
      </motion.div>

      <motion.div
        initial={{ opacity: 0, x: reverse ? -24 : 24 }}
        whileInView={{ opacity: 1, x: 0 }}
        viewport={{ once: true, margin: '-100px' }}
        transition={{ duration: 0.6 }}
        className={cn(reverse && 'lg:order-1')}
      >
        {visual}
      </motion.div>
    </div>
  )
}
