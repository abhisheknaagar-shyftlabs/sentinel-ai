import { NavLink } from 'react-router-dom'
import { ChevronsLeft, ChevronsRight, X } from 'lucide-react'
import { Logo } from '@/components/brand/Logo'
import { NAV_ITEMS } from './nav-config'
import { useUiStore } from '@/stores/ui-store'
import { useMobileNavStore } from '@/stores/mobile-nav-store'
import { cn } from '@/utils/cn'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

export function Sidebar() {
  const collapsed = useUiStore((state) => state.sidebarCollapsed)
  const toggleSidebar = useUiStore((state) => state.toggleSidebar)
  const mobileNavOpen = useMobileNavStore((state) => state.isOpen)
  const closeMobileNav = useMobileNavStore((state) => state.close)
  const showIconOnlyLogo = collapsed && !mobileNavOpen

  return (
    <>
      {mobileNavOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/60 lg:hidden"
          onClick={closeMobileNav}
          aria-hidden="true"
        />
      )}

      <aside
        className={cn(
          'fixed inset-y-0 left-0 z-50 flex h-svh w-64 shrink-0 -translate-x-full flex-col border-r border-border bg-surface transition-transform duration-200',
          mobileNavOpen && 'translate-x-0',
          'lg:sticky lg:top-0 lg:z-auto lg:translate-x-0 lg:transition-[width]',
          !mobileNavOpen && (collapsed ? 'lg:w-16' : 'lg:w-64'),
        )}
      >
        <div
          className={cn(
            'flex h-14 items-center justify-between border-b border-border px-4',
            collapsed && 'lg:justify-center lg:px-0',
          )}
        >
          <Logo iconOnly={showIconOnlyLogo} />
          <button
            type="button"
            onClick={closeMobileNav}
            className="text-muted-foreground hover:text-foreground lg:hidden"
          >
            <X className="size-5" />
          </button>
        </div>

        <nav className="flex flex-1 flex-col gap-1 overflow-y-auto p-3">
          {NAV_ITEMS.map((item) => {
            const link = (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={closeMobileNav}
                className={({ isActive }) =>
                  cn(
                    'group flex items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-surface-hover hover:text-foreground',
                    collapsed && 'lg:justify-center lg:px-0',
                    isActive &&
                      'bg-primary-muted text-primary hover:bg-primary-muted hover:text-primary',
                  )
                }
                end
              >
                <item.icon className="size-4 shrink-0" strokeWidth={1.75} />
                <span className={cn('truncate', collapsed && 'lg:hidden')}>{item.label}</span>
              </NavLink>
            )

            if (!collapsed) return link

            return (
              <Tooltip key={item.path}>
                <TooltipTrigger asChild>{link}</TooltipTrigger>
                <TooltipContent side="right" className="hidden lg:block">
                  {item.label}
                </TooltipContent>
              </Tooltip>
            )
          })}
        </nav>

        <div className="border-t border-border p-3">
          <button
            type="button"
            onClick={toggleSidebar}
            className={cn(
              'hidden w-full items-center gap-3 rounded-md px-3 py-2 text-sm font-medium text-muted-foreground transition-colors hover:bg-surface-hover hover:text-foreground lg:flex',
              collapsed && 'lg:justify-center lg:px-0',
            )}
          >
            {collapsed ? <ChevronsRight className="size-4" /> : <ChevronsLeft className="size-4" />}
            {!collapsed && <span>Collapse</span>}
          </button>
        </div>
      </aside>
    </>
  )
}
