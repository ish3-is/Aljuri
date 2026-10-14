import { lazy, Suspense } from 'react'
import { SectionLabel } from '../components/ui/primitives'
import { useI18n } from '../i18n/useI18n'
import type { HistoryEntry } from '../features/analysis/historyStore'

/* ============================================================
   DASHBOARD CHARTS

   Recharts is ~150kB of JavaScript. Importing it eagerly would put
   the entire charting library in the initial bundle for a section
   most readers never open, so it is split out and loaded only when
   the Dashboard mounts. The fallback below is a real skeleton with
   the same footprint, so the section does not jump when the charts
   arrive.
   ============================================================ */

const DashboardCharts = lazy(() =>
  import('../features/dashboard/DashboardCharts').then((module) => ({
    default: module.DashboardCharts,
  })),
)

function ChartsSkeleton() {
  return (
    <div className="grid gap-5 lg:grid-cols-2" aria-hidden>
      {[0, 1, 2, 3].map((index) => (
        <div
          key={index}
          className="h-[240px] animate-breathe rounded-lg border border-line/50 bg-surface/25"
        />
      ))}
    </div>
  )
}

export interface DashboardChartsSectionProps {
  history: HistoryEntry[]
  /** Bumped by the parent to force a re-read after a new analysis. */
  revision: number
}

export function DashboardChartsSection({
  history,
  revision,
}: DashboardChartsSectionProps) {
  const { t } = useI18n()

  return (
    <section className="mt-5">
      <SectionLabel
        index="02"
        title={t('charts.title')}
        subtitle={t('charts.subtitle')}
        className="mb-6"
      />

      <Suspense fallback={<ChartsSkeleton />}>
        <DashboardCharts history={history} revision={revision} />
      </Suspense>
    </section>
  )
}