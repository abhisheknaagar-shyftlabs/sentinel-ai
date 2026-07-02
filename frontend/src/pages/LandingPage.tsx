import { LandingNav } from '@/features/landing/components/LandingNav'
import { Hero } from '@/features/landing/components/Hero'
import { IntegrationsStrip } from '@/features/landing/components/IntegrationsStrip'
import { OutcomesSection } from '@/features/landing/components/OutcomesSection'
import { ModulesSection } from '@/features/landing/components/ModulesSection'
import { FinalCta } from '@/features/landing/components/FinalCta'
import { LandingFooter } from '@/features/landing/components/LandingFooter'

export default function LandingPage() {
  return (
    <div className="min-h-svh bg-background">
      <LandingNav />
      <Hero />
      <IntegrationsStrip />
      <OutcomesSection />
      <ModulesSection />
      <FinalCta />
      <LandingFooter />
    </div>
  )
}
