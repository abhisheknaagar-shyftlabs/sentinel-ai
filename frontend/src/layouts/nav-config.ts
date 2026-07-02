import {
  GitPullRequest,
  LayoutDashboard,
  LineChart,
  Plug,
  Server,
  Settings,
  type LucideIcon,
} from 'lucide-react'
import { ROUTES } from '@/routes/paths'

export interface NavItem {
  label: string
  path: string
  icon: LucideIcon
}

export const NAV_ITEMS: NavItem[] = [
  { label: 'Dashboard', path: ROUTES.dashboard, icon: LayoutDashboard },
  { label: 'Development Intelligence', path: ROUTES.developmentIntelligence, icon: GitPullRequest },
  { label: 'Production Intelligence', path: ROUTES.productionIntelligence, icon: Server },
  { label: 'Executive Intelligence', path: ROUTES.executiveIntelligence, icon: LineChart },
  { label: 'Integrations', path: ROUTES.integrations, icon: Plug },
  { label: 'Settings', path: ROUTES.settings, icon: Settings },
]
