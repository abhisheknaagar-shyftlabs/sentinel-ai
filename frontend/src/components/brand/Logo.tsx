import { cn } from '@/utils/cn'

interface LogoProps {
  className?: string
  iconOnly?: boolean
}

export function Logo({ className, iconOnly = false }: LogoProps) {
  return (
    <div className={cn('flex items-center gap-2', className)}>
      <svg
        width="24"
        height="24"
        viewBox="0 0 32 32"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        className="shrink-0"
      >
        <defs>
          <linearGradient id="logo-gradient" x1="4" y1="2" x2="28" y2="30" gradientUnits="userSpaceOnUse">
            <stop offset="0" stopColor="#8B7BFF" />
            <stop offset="1" stopColor="#22D3EE" />
          </linearGradient>
        </defs>
        <rect width="32" height="32" rx="8" fill="var(--surface-elevated)" />
        <path
          d="M16 5L26 9V15.5C26 21.5 21.8 26.2 16 27.5C10.2 26.2 6 21.5 6 15.5V9L16 5Z"
          fill="url(#logo-gradient)"
          fillOpacity="0.18"
          stroke="url(#logo-gradient)"
          strokeWidth="1.6"
        />
        <path
          d="M11.5 16.2L14.6 19.3L20.8 12.7"
          stroke="url(#logo-gradient)"
          strokeWidth="1.8"
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      </svg>
      {!iconOnly && <span className="text-sm font-semibold tracking-tight text-foreground">Sentinel AI</span>}
    </div>
  )
}
