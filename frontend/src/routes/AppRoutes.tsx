import { lazy, Suspense } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { AppShell } from '@/layouts/AppShell'
import { RouteFallback } from '@/layouts/RouteFallback'
import { ProtectedRoute } from './ProtectedRoute'
import { ROUTES } from './paths'

const LandingPage = lazy(() => import('@/pages/LandingPage'))
const LoginPage = lazy(() => import('@/pages/LoginPage'))
const DashboardPage = lazy(() => import('@/pages/DashboardPage'))
const DevelopmentIntelligencePage = lazy(() => import('@/pages/DevelopmentIntelligencePage'))
const ProductionIntelligencePage = lazy(() => import('@/pages/ProductionIntelligencePage'))
const ExecutiveIntelligencePage = lazy(() => import('@/pages/ExecutiveIntelligencePage'))
const IntegrationsPage = lazy(() => import('@/pages/IntegrationsPage'))
const SettingsPage = lazy(() => import('@/pages/SettingsPage'))

export function AppRoutes() {
  return (
    <Suspense fallback={<RouteFallback />}>
      <Routes>
        <Route path={ROUTES.landing} element={<LandingPage />} />
        <Route path={ROUTES.login} element={<LoginPage />} />

        <Route
          element={
            <ProtectedRoute>
              <AppShell />
            </ProtectedRoute>
          }
        >
          <Route path={ROUTES.dashboard} element={<DashboardPage />} />
          <Route path={ROUTES.developmentIntelligence} element={<DevelopmentIntelligencePage />} />
          <Route path={ROUTES.productionIntelligence} element={<ProductionIntelligencePage />} />
          <Route path={ROUTES.executiveIntelligence} element={<ExecutiveIntelligencePage />} />
          <Route path={ROUTES.integrations} element={<IntegrationsPage />} />
          <Route path={ROUTES.settings} element={<SettingsPage />} />
        </Route>

        <Route path="*" element={<Navigate to={ROUTES.landing} replace />} />
      </Routes>
    </Suspense>
  )
}
