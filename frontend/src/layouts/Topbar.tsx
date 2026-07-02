import { useLocation, useNavigate } from 'react-router-dom'
import { Bell, LogOut, Menu, Settings, User } from 'lucide-react'
import { NAV_ITEMS } from './nav-config'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { useAuthStore } from '@/stores/auth-store'
import { useMobileNavStore } from '@/stores/mobile-nav-store'
import { ThemeToggle } from '@/components/shared'
import { ROUTES } from '@/routes/paths'

function getInitials(name: string) {
  return name
    .split(' ')
    .map((part) => part[0])
    .join('')
    .slice(0, 2)
    .toUpperCase()
}

export function Topbar() {
  const location = useLocation()
  const navigate = useNavigate()
  const user = useAuthStore((state) => state.user)
  const logout = useAuthStore((state) => state.logout)
  const toggleMobileNav = useMobileNavStore((state) => state.toggle)

  const currentNavItem = NAV_ITEMS.find((item) => location.pathname.startsWith(item.path))

  function handleLogout() {
    logout()
    navigate(ROUTES.login)
  }

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center justify-between border-b border-border bg-background/80 px-6 backdrop-blur-sm">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="lg:hidden"
          onClick={toggleMobileNav}
          aria-label="Toggle navigation"
        >
          <Menu className="size-4" />
        </Button>
        <span className="text-sm font-medium text-foreground">
          {currentNavItem?.label ?? 'Sentinel AI'}
        </span>
      </div>

      <div className="flex items-center gap-2">
        <ThemeToggle />
        <Button variant="ghost" size="icon" className="relative">
          <Bell className="size-4" />
          <span className="absolute top-1.5 right-1.5 size-1.5 rounded-full bg-primary" />
        </Button>

        <DropdownMenu>
          <DropdownMenuTrigger asChild>
            <button type="button" className="ml-1 rounded-full outline-none ring-primary focus-visible:ring-2">
              <Avatar className="size-8">
                <AvatarFallback className="bg-surface-elevated text-xs font-medium text-foreground">
                  {user ? getInitials(user.name) : 'SA'}
                </AvatarFallback>
              </Avatar>
            </button>
          </DropdownMenuTrigger>
          <DropdownMenuContent align="end" className="w-56">
            <DropdownMenuLabel className="flex flex-col gap-0.5">
              <span className="text-sm font-medium">{user?.name ?? 'Guest'}</span>
              <span className="text-xs font-normal text-muted-foreground">{user?.email}</span>
            </DropdownMenuLabel>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={() => navigate(ROUTES.settings)}>
              <User className="size-4" />
              Profile
            </DropdownMenuItem>
            <DropdownMenuItem onClick={() => navigate(ROUTES.settings)}>
              <Settings className="size-4" />
              Settings
            </DropdownMenuItem>
            <DropdownMenuSeparator />
            <DropdownMenuItem onClick={handleLogout} variant="destructive">
              <LogOut className="size-4" />
              Log out
            </DropdownMenuItem>
          </DropdownMenuContent>
        </DropdownMenu>
      </div>
    </header>
  )
}
