import { ModuleShowcase } from './ModuleShowcase'
import { DevIntelligenceVisual } from './visuals/DevIntelligenceVisual'
import { ProdIntelligenceVisual } from './visuals/ProdIntelligenceVisual'
import { ExecIntelligenceVisual } from './visuals/ExecIntelligenceVisual'

export function ModulesSection() {
  return (
    <section id="modules" className="flex flex-col gap-24 border-t border-border px-6 py-24 lg:gap-32">
      <div className="mx-auto flex max-w-6xl w-full flex-col gap-24 lg:gap-32">
        <ModuleShowcase
          eyebrow="Development Intelligence"
          title="Every PR reviewed like your best senior engineer already looked at it"
          description="Sentinel reads the diff, weighs the blast radius, and tells you whether this is safe to ship — before it's your problem in production."
          features={[
            'GitHub PR review, automatically on every push',
            'Risk analysis scored against your own incident history',
            'Technical debt tracked as it accrues, not discovered later',
            'Deployment confidence score before you hit merge',
            'AI-generated fixes for the issues it finds',
          ]}
          visual={<DevIntelligenceVisual />}
        />

        <ModuleShowcase
          eyebrow="Production Intelligence"
          title="Know why it broke before your customers do"
          description="Sentinel watches every container in real time, and when something fails, it already has the root cause and, often, the fix."
          features={[
            'Docker monitoring across every service',
            'Container health checked continuously',
            'Logs correlated automatically, no more grepping',
            'Root cause analysis in seconds, not stand-ups',
            'Auto recovery for the incidents that don’t need a human',
            'Full incident timeline for every postmortem',
          ]}
          visual={<ProdIntelligenceVisual />}
          reverse
        />

        <ModuleShowcase
          eyebrow="Executive Intelligence"
          title="Turn engineering health into a number leadership trusts"
          description="Stop translating engineering work into slides the night before a review. Sentinel keeps the story ready, all the time."
          features={[
            'Engineering health scored across the whole org',
            'Deployment readiness, tracked release over release',
            'Infrastructure cost broken down by service',
            'Cost optimization opportunities surfaced automatically',
            'Incident analytics that show the trend, not just the fire',
          ]}
          visual={<ExecIntelligenceVisual />}
        />
      </div>
    </section>
  )
}
