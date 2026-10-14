import { Suspense, lazy, useEffect } from 'react'
import { useI18n } from './i18n/useI18n'
import { AmbientBackground } from './components/motion/AmbientBackground'
import { BrandReveal } from './components/brand/BrandReveal'
import { IntelligenceTicker } from './components/motion/IntelligenceTicker'
import { BasirahFooter } from './components/layout/BasirahFooter'
import { BasirahHeader } from './components/layout/BasirahHeader'
import { AppModeProvider } from './hooks/AppModeProvider'
import { I18nProvider } from './i18n/I18nProvider'
import { useSection } from './hooks/useSection'
import { AnalyzePage } from './pages/AnalyzePage'
import { OverviewPage } from './pages/OverviewPage'

/**
 * CODE SPLITTING
 *
 * Overview and Analyze stay in the initial chunk: Overview is the
 * landing view and Analyze is mounted on first paint (kept mounted so
 * an investigation survives navigation), so deferring either would
 * only add a loading step to the first thing every reader sees.
 *
 * Everything else — the five secondary sections and the Reports
 * Center — loads on first navigation. Together they account for
 * roughly 40kB of the initial bundle, which is paid by nobody who
 * does not open them.
 */
const CategoriesPage = lazy(() =>
  import('./pages/CategoriesPage').then((module) => ({
    default: module.CategoriesPage,
  })),
)

/**
 * The Challenge section is a reviewer surface, so it loads on first
 * navigation like the other secondary sections rather than sitting in
 * the initial chunk.
 */
const ChallengePage = lazy(() =>
  import('./pages/ChallengePage').then((module) => ({
    default: module.ChallengePage,
  })),
)

const CapabilitiesPage = lazy(() =>
  import('./pages/CapabilitiesPage').then((module) => ({
    default: module.CapabilitiesPage,
  })),
)

const DashboardPage = lazy(() =>
  import('./pages/DashboardPage').then((module) => ({
    default: module.DashboardPage,
  })),
)

const TeamPage = lazy(() =>
  import('./pages/TeamPage').then((module) => ({
    default: module.TeamPage,
  })),
)

const AboutPageLazy = lazy(() =>
  import('./pages/AboutPage').then((module) => ({ default: module.AboutPage })),
)

/**
 * The Reports Center is split out of the initial bundle. It pulls in
 * the report document, the store and the export controls — none of
 * which a first-time reader needs before they have run an analysis —
 * so it loads on first navigation to the section rather than on
 * first paint of the app.
 */
const ReportsPage = lazy(() =>
  import('./pages/ReportsPage').then((module) => ({
    default: module.ReportsPage,
  })),
)

/**
 * BASIRAH — application shell.
 *
 * The shell is intentionally thin. I18nProvider owns language and the
 * document direction; useSection owns the active section via the URL
 * hash; everything else is a section component.
 *
 * The Analyze section is deliberately the ONE exception to
 * render-only-when-active: it stays mounted and is hidden with the
 * `hidden` attribute when another section is showing. A submitted
 * image takes seconds to analyse, and losing that result because the
 * reader stepped over to the Team section and back would be a real
 * defect — the upload cannot be replayed without re-picking the file.
 * Hiding rather than unmounting preserves the investigation, the
 * object URL and the result panels. Every other section is cheap and
 * stateless, so those render only when active.
 */
export default function App() {
  return (
    <AppModeProvider>
      <I18nProvider>
        <AmbientBackground />
        <BasirahApp />
      </I18nProvider>
    </AppModeProvider>
  )
}

/** Split out so `useSection` sits inside the I18nProvider. */
function BasirahApp() {
  const { section, setSection } = useSection()
  const { t } = useI18n()

  // A section is a page, not a scroll position: on a section change
  // the reader must land at the top. This also covers a Back/Forward
  // step that changes the hash without going through setSection.
  useEffect(() => {
    window.scrollTo({ top: 0 })
  }, [section])

  return (
    <>
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:fixed focus:top-4 focus:start-4 focus:z-[70] focus:rounded-md focus:border focus:border-signal/40 focus:bg-surface focus:px-4 focus:py-2 focus:text-sm focus:text-signal"
      >
        {t('a11y.skipToContent')}
      </a>

      <BrandReveal />

      <BasirahHeader section={section} onNavigate={setSection} />

      <main id="main" className="relative">
        {section === 'overview' && <OverviewPage onNavigate={setSection} />}

        {/* Every deferred section shares one Suspense boundary, so the
            fallback is defined once and behaves identically
            everywhere. */}
        <Suspense fallback={<SectionFallback />}>
          {section === 'categories' && <CategoriesPage />}
          {section === 'challenge' && <ChallengePage />}
          {section === 'capabilities' && <CapabilitiesPage />}
          {section === 'dashboard' && <DashboardPage />}
          {section === 'reports' && <ReportsPage />}
          {section === 'team' && <TeamPage />}
          {section === 'about' && <AboutPageLazy />}
        </Suspense>

        {/* Kept mounted across section changes: see the note above. */}
        <div hidden={section !== 'analyze'}>
          <AnalyzePage />
        </div>
      </main>

      <IntelligenceTicker />

      <BasirahFooter section={section} onNavigate={setSection} />
    </>
  )
}

/** Placeholder for a lazily-loaded section, sized so nothing jumps. */
function SectionFallback() {
  return (
    <div className="px-5 pt-28 pb-10 sm:px-8 sm:pt-32" aria-hidden>
      <div className="mx-auto h-64 max-w-[1400px] animate-breathe rounded-lg border border-line/40 bg-surface/25" />
    </div>
  )
}
