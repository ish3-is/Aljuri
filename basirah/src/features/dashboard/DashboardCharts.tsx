import { useState } from 'react'
import { motion } from 'motion/react'
import {
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from 'recharts'
import { Panel } from '../../components/ui/primitives'
import { StateBadge } from '../../components/ui/StateBadge'
import {
  activeCapabilities,
  plannedCapabilities,
} from '../../data/capabilities'
import { usePrefersReducedMotion } from '../../hooks/useEnvironment'
import { useI18n } from '../../i18n/useI18n'
import type { ModuleState } from '../../data/detectionCategories'
import type { TranslationKey } from '../../i18n/translations'
import type { HistoryEntry } from '../analysis/historyStore'

/* ============================================================
   DASHBOARD CHARTS — THE HONESTY CONTRACT

   This is the only place in the product that draws a chart, so it
   carries the strictest rule in the codebase:

     ONLY REAL DATA IS PLOTTED. There are no invented percentages,
     no "95% confidence", no usage totals, no trend lines for a
     period in which nothing was measured. Three sources are
     permitted and no others:

       1. MODULE READINESS — a categorical count of the modules that
          actually exist in `src/data/capabilities.ts`, grouped by
          the real ModuleState each one carries. This is a census of
          the codebase, which is a fact.

       2. LOCAL ANALYSIS HISTORY — the reader's own completed runs,
          read from localStorage. Every point is a real analysis on
          this device. Never uploaded, never a mock.

       3. NOTHING ELSE.

   A chart with no data shows the honest empty state instead of a
   placeholder. The module-readiness chart still renders, because it
   is real regardless of whether the reader has run anything.

   ACCESSIBILITY: no chart conveys information by colour alone. Every
   chart ships (a) a text alternative, (b) a real <table> of the same
   data, and (c) written labels beside each value. Colour is
   decoration on top of an already-complete text presentation.
   ============================================================ */

/** The states the readiness census reports, in a fixed order. */
const READINESS_STATES: ModuleState[] = [
  'active',
  'researchGrade',
  'advisory',
  'inDevelopment',
  'planned',
]

/** Fixed palette per state, from the product's own vocabulary. */
const STATE_COLOR: Record<string, string> = {
  active: 'var(--bas-trusted)',
  researchGrade: 'var(--bas-accent-cyan)',
  advisory: 'var(--bas-caution)',
  inDevelopment: 'var(--bas-accent-violet)',
  planned: 'var(--bas-text-dim)',
}

/* ------------------------------------------------------------------ */
/* Shared chart chrome                                                  */
/* ------------------------------------------------------------------ */

/**
 * Recharts types its formatter callbacks against a loose
 * `ValueType`, so the concrete value arrives as possibly-undefined.
 * Both callbacks below narrow it rather than casting, and fall back
 * to a dash instead of printing "undefined" into a tooltip.
 */
function asNumber(value: unknown): number | null {
  return typeof value === 'number' ? value : null
}

/** Recharts paints SVG text with its own font stack, so the axis
    colours are read from the live CSS variables rather than
    hardcoded — that is what makes the charts follow the theme. */
const AXIS_COLOR = 'var(--bas-text-dim)'
const GRID_COLOR = 'var(--bas-border)'

interface ChartFrameProps {
  title: string
  subtitle: string
  source: string
  children: React.ReactNode
  /** Text alternative, read by assistive technology. */
  alt: string
  /** The same data as a real table, so no value is colour-only. */
  table: { columns: string[]; rows: Array<Array<string | number>> }
  className?: string
}

/**
 * Wraps a chart with everything it needs to be readable without
 * sight of colour: a heading, a subtitle, a provenance line saying
 * where the data came from, an aria description, and the equivalent
 * table.
 */
function ChartFrame({
  title,
  subtitle,
  source,
  children,
  alt,
  table,
  className,
}: ChartFrameProps) {
  const { t } = useI18n()
  const [showTable, setShowTable] = useState(false)

  return (
    <Panel className={className}>
      <div className="p-5 pb-0">
        <h3 className="font-arabic-display text-[0.9rem] text-text">{title}</h3>
        <p className="font-arabic-body mt-1.5 text-[0.72rem] leading-relaxed text-text-dim">
          {subtitle}
        </p>
      </div>

      <motion.div
        initial={{ opacity: 0 }}
        whileInView={{ opacity: 1 }}
        viewport={{ once: true, margin: '-40px' }}
        transition={{ duration: 0.5 }}
        className="px-5 pt-4"
      >
        <figure>
          {/* The SVG is aria-hidden: a chart's accessibility story is
              the table below it, which conveys every value as text. */}
          <div
            aria-hidden
            className="h-[220px] w-full"
            role="presentation"
          >
            {children}
          </div>
          <figcaption className="sr-only">{alt}</figcaption>
        </figure>
      </motion.div>

      <div className="px-5 pb-5">
        {/* ---- the same data as text, always available ---- */}
        <button
          type="button"
          onClick={() => setShowTable((value) => !value)}
          aria-expanded={showTable}
          className="text-[0.7rem] text-text-dim underline decoration-line-bright underline-offset-4 transition-colors hover:text-text"
        >
          {t('charts.dataTableLabel')}
        </button>

        {showTable && (
          <div className="mt-3 overflow-x-auto">
            <table className="w-full border-collapse text-start">
              <caption className="sr-only">{title}</caption>
              <thead>
                <tr>
                  {table.columns.map((column) => (
                    <th
                      key={column}
                      scope="col"
                      className="border-b border-line/60 pb-1.5 pe-4 text-start text-[0.68rem] text-text-dim"
                    >
                      {column}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody>
                {table.rows.map((row, index) => (
                  <tr key={index}>
                    {row.map((cell, cellIndex) => (
                      <td
                        key={cellIndex}
                        className="border-b border-line/30 py-1.5 pe-4 text-[0.72rem] text-text-muted"
                      >
                        {cell}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}

        <p className="mono-label mt-3 text-text-dim/80">{source}</p>
      </div>
    </Panel>
  )
}

/* ------------------------------------------------------------------ */
/* Readiness census                                                     */
/* ------------------------------------------------------------------ */

/**
 * Count the modules that really exist, by the state each one
 * declares. Derived from the capability registry at render time, so
 * it cannot drift from the rest of the product: if a module is added
 * or reclassified in `capabilities.ts`, this chart follows.
 */
function useReadiness() {
  const { t } = useI18n()

  const all = [...activeCapabilities, ...plannedCapabilities]

  return READINESS_STATES.map((state) => {
    const members = all.filter((capability) => capability.state === state)
    return {
      state,
      key: `state.${state}` as TranslationKey,
      // The state name is written out, so the value is legible even
      // in a chart with no colour at all.
      name: t(`state.${state}`),
      count: members.length,
      members: members.map((capability) => t(capability.nameKey)),
    }
  }).filter((row) => row.count > 0)
}

/* ------------------------------------------------------------------ */
/* The section                                                          */
/* ------------------------------------------------------------------ */

export function DashboardCharts({
  history,
}: {
  history: HistoryEntry[]
  /** Accepted for cache-busting when a new analysis lands. */
  revision?: number
}) {
  const { t } = useI18n()
  const reduced = usePrefersReducedMotion()
  const readiness = useReadiness()

  // Entrance animation duration: reduced motion collapses it to a
  // plain fade, so the chart still appears without anything sweeping.
  const entrance = reduced ? { duration: 0 } : { duration: 0.6 }

  const hasHistory = history.length > 0

  /* ---- categorical counts derived from the local record ---- */

  /**
   * All four real intake modalities.
   *
   * Zero-count rows are filtered out rather than rendered as empty
   * bars: a modality with no analyses should be absent from the
   * chart, because a zero-height bar next to "Count: 0" reads as a
   * failed measurement rather than an absence of data.
   */
  const modalityData = (
    [
      { key: 'image', labelKey: 'charts.modalityImage' },
      { key: 'screenshot', labelKey: 'charts.modalityScreenshot' },
      { key: 'file', labelKey: 'charts.modalityFile' },
      { key: 'url', labelKey: 'charts.modalityUrl' },
    ] as const
  )
    .map((modality) => ({
      key: modality.key,
      name: t(modality.labelKey),
      count: history.filter((entry) => entry.modality === modality.key).length,
    }))
    .filter((row) => row.count > 0)

  /**
   * Assessment outcomes, in the pipeline's OWN five-state vocabulary.
   *
   * The old chart collapsed "no strong synthetic indicators" into a
   * bar labelled "Likely authentic", which is not what the pipeline
   * said and reads as an authenticity claim it never made. Each
   * state now appears under its own label, including the two
   * provenance states, so the chart reports the same distinctions the
   * result page does.
   */
  const outcomeData = (
    [
      { key: 'likely_synthetic', labelKey: 'charts.outcomeSynthetic' },
      { key: 'uncertain', labelKey: 'charts.outcomeUncertain' },
      { key: 'no_strong_synthetic_indicators', labelKey: 'charts.outcomeNoStrong' },
      { key: 'provenance_verified', labelKey: 'charts.outcomeProvenanceVerified' },
      { key: 'provenance_unavailable', labelKey: 'charts.outcomeProvenanceUnavailable' },
    ] as const
  )
    .map((outcome) => ({
      key: outcome.key,
      name: t(outcome.labelKey),
      count: history.filter((entry) => entry.assessment === outcome.key).length,
    }))
    .filter((row) => row.count > 0)

  const riskData = (['trusted', 'caution', 'high_risk'] as const)
    .map((risk) => ({
      key: risk,
      name: t(
        risk === 'trusted'
          ? 'score.trusted'
          : risk === 'caution'
            ? 'score.caution'
            : 'score.highRisk',
      ),
      count: history.filter((entry) => entry.riskLevel === risk).length,
    }))
    .filter((row) => row.count > 0)

  const trustSeries = history.map((entry, index) => ({
    index: index + 1,
    trust: entry.trust,
    // The point carries its own label, so the line is readable
    // without hovering.
    label: `#${index + 1}`,
  }))

  return (
    <div className="space-y-5">
      {/* ============================================================
          1. Module readiness — REAL CONFIGURATION DATA
          ============================================================ */}
      <div className="grid gap-5 lg:grid-cols-2">
        <ChartFrame
          title={t('charts.readinessTitle')}
          subtitle={t('charts.readinessSubtitle')}
          source={`${t('charts.sourceConfig')} · ${t('charts.labelCount')}`}
          alt={t('charts.readinessAlt')
            .replace('{active}', String(readiness.find((r) => r.state === 'active')?.count ?? 0))
            .replace('{research}', String(readiness.find((r) => r.state === 'researchGrade')?.count ?? 0))
            .replace('{advisory}', String(readiness.find((r) => r.state === 'advisory')?.count ?? 0))
            .replace('{planned}', String(readiness.find((r) => r.state === 'planned')?.count ?? 0))}
          table={{
            columns: [t('reports.dnaSummary'), t('charts.labelCount')],
            rows: readiness.map((row) => [row.name, row.count]),
          }}
          className="lg:col-span-1"
        >
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={readiness} margin={{ top: 8, right: 8, bottom: 0, left: -18 }}>
              <CartesianGrid strokeDasharray="2 4" stroke={GRID_COLOR} vertical={false} />
              <XAxis
                dataKey="name"
                tick={{ fill: AXIS_COLOR, fontSize: 10 }}
                axisLine={{ stroke: GRID_COLOR }}
                tickLine={false}
              />
              <YAxis
                allowDecimals={false}
                tick={{ fill: AXIS_COLOR, fontSize: 10 }}
                axisLine={false}
                tickLine={false}
              />
              <Tooltip
                cursor={{ fill: 'var(--bas-border)' }}
                contentStyle={{
                  background: 'var(--bas-surface)',
                  border: '1px solid var(--bas-border)',
                  borderRadius: 6,
                  fontSize: 11,
                  color: 'var(--bas-text-primary)',
                }}
                formatter={(value, _name, entry) => {
                  const count = asNumber(value)
                  const members =
                    entry && 'payload' in entry && entry.payload
                      ? ((entry.payload as { members?: string[] }).members ?? [])
                      : []
                  return [
                    count === null
                      ? '—'
                      : `${count}${members.length > 0 ? ` · ${members.join(', ')}` : ''}`,
                    t('charts.labelCount'),
                  ]
                }}
              />
              <Bar dataKey="count" radius={[3, 3, 0, 0]} animationDuration={entrance.duration}>
                {readiness.map((row) => (
                  <Cell key={row.state} fill={STATE_COLOR[row.state]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </ChartFrame>

        {/* The written form of the same census: a reader who cannot
            use the chart at all still gets every state and count. */}
        <Panel className="p-5">
          <h3 className="font-arabic-display text-[0.9rem] text-text">
            {t('charts.readinessTitle')}
          </h3>
          <ul className="mt-3 space-y-2.5">
            {readiness.map((row) => (
              <li
                key={row.state}
                className="flex flex-wrap items-center justify-between gap-x-4 gap-y-1.5 border-b border-line/40 pb-2.5 last:border-b-0"
              >
                <span className="font-arabic-body flex items-center gap-2 text-[0.78rem] text-text-muted">
                  <StateBadge state={row.state} still />
                  {row.name}
                </span>
                <span className="ltr-embed text-[0.78rem] text-text">
                  {row.count}
                </span>
              </li>
            ))}
          </ul>
        </Panel>
      </div>

      {/* ============================================================
          2. Local history — REAL ANALYSES, OR AN HONEST EMPTY STATE
          ============================================================ */}
      {!hasHistory ? (
        <Panel className="border-dashed p-8 text-center">
          <p className="font-arabic-emph text-[0.9rem] text-text">
            {t('charts.historyEmpty')}
          </p>
          <p className="font-arabic-body mx-auto mt-2 max-w-lg text-[0.76rem] leading-relaxed text-text-dim">
            {t('charts.historyEmptyHint')}
          </p>
          <p className="mono-label mt-4 text-text-dim/80">
            {t('charts.sourceLocal')}
          </p>
        </Panel>
      ) : (
        <>
          <div className="grid gap-5 lg:grid-cols-2">
            {/* ---- modality mix ---- */}
            <ChartFrame
              title={t('charts.modalityTitle')}
              subtitle={t('charts.modalitySubtitle')}
              source={`${t('charts.sourceLocal')} · ${t('charts.labelCount')}`}
              alt={modalityData.map((row) => `${row.name}: ${row.count}`).join(', ')}
              table={{
                columns: [t('charts.labelModality'), t('charts.labelCount')],
                rows: modalityData.map((row) => [row.name, row.count]),
              }}
            >
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={modalityData}
                    dataKey="count"
                    nameKey="name"
                    innerRadius="52%"
                    outerRadius="82%"
                    paddingAngle={3}
                    stroke="none"
                    animationDuration={entrance.duration}
                  >
                    {modalityData.map((row, index) => (
                      <Cell
                        key={row.key}
                        fill={
                          index === 0
                            ? 'var(--bas-accent-cyan)'
                            : 'var(--bas-accent-violet)'
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bas-surface)',
                      border: '1px solid var(--bas-border)',
                      borderRadius: 6,
                      fontSize: 11,
                      color: 'var(--bas-text-primary)',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </ChartFrame>

            {/* ---- assessment outcomes ---- */}
            <ChartFrame
              title={t('charts.outcomeTitle')}
              subtitle={t('charts.outcomeSubtitle')}
              source={`${t('charts.sourceLocal')} · ${t('charts.labelCount')}`}
              alt={outcomeData.map((row) => `${row.name}: ${row.count}`).join(', ')}
              table={{
                columns: [t('charts.labelAssessment'), t('charts.labelCount')],
                rows: outcomeData.map((row) => [row.name, row.count]),
              }}
            >
              <ResponsiveContainer width="100%" height="100%">
                <BarChart
                  data={outcomeData}
                  layout="vertical"
                  margin={{ top: 4, right: 16, bottom: 0, left: 8 }}
                >
                  <CartesianGrid strokeDasharray="2 4" stroke={GRID_COLOR} horizontal={false} />
                  <XAxis
                    type="number"
                    allowDecimals={false}
                    tick={{ fill: AXIS_COLOR, fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <YAxis
                    type="category"
                    dataKey="name"
                    width={104}
                    tick={{ fill: AXIS_COLOR, fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    cursor={{ fill: 'var(--bas-border)' }}
                    contentStyle={{
                      background: 'var(--bas-surface)',
                      border: '1px solid var(--bas-border)',
                      borderRadius: 6,
                      fontSize: 11,
                      color: 'var(--bas-text-primary)',
                    }}
                  />
                  <Bar dataKey="count" radius={[0, 3, 3, 0]} animationDuration={entrance.duration}>
                    {outcomeData.map((row) => (
                      <Cell
                        key={row.key}
                        fill={
                          row.key === 'likely_synthetic'
                            ? 'var(--bas-danger)'
                            : row.key === 'uncertain'
                              ? 'var(--bas-caution)'
                              : 'var(--bas-trusted)'
                        }
                      />
                    ))}
                  </Bar>
                </BarChart>
              </ResponsiveContainer>
            </ChartFrame>

            {/* ---- risk bands ---- */}
            <ChartFrame
              title={t('charts.riskTitle')}
              subtitle={t('charts.riskSubtitle')}
              source={`${t('charts.sourceLocal')} · ${t('charts.labelCount')}`}
              alt={riskData.map((row) => `${row.name}: ${row.count}`).join(', ')}
              table={{
                columns: [t('charts.labelRisk'), t('charts.labelCount')],
                rows: riskData.map((row) => [row.name, row.count]),
              }}
            >
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={riskData}
                    dataKey="count"
                    nameKey="name"
                    innerRadius="52%"
                    outerRadius="82%"
                    paddingAngle={3}
                    stroke="none"
                    animationDuration={entrance.duration}
                  >
                    {riskData.map((row) => (
                      <Cell
                        key={row.key}
                        fill={
                          row.key === 'trusted'
                            ? 'var(--bas-trusted)'
                            : row.key === 'caution'
                              ? 'var(--bas-caution)'
                              : 'var(--bas-danger)'
                        }
                      />
                    ))}
                  </Pie>
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bas-surface)',
                      border: '1px solid var(--bas-border)',
                      borderRadius: 6,
                      fontSize: 11,
                      color: 'var(--bas-text-primary)',
                    }}
                  />
                </PieChart>
              </ResponsiveContainer>
            </ChartFrame>

            {/* ---- trust over time ---- */}
            <ChartFrame
              title={t('charts.trustHistoryTitle')}
              subtitle={t('charts.trustHistorySubtitle')}
              source={`${t('charts.sourceLocal')} · ${t('charts.labelTrust')}`}
              alt={trustSeries.map((point) => `${point.label}: ${point.trust}`).join(', ')}
              table={{
                columns: [t('charts.labelWhen'), t('charts.labelTrust')],
                rows: history.map((entry, index) => [
                  `#${index + 1} · ${new Date(entry.at).toLocaleString()}`,
                  entry.trust,
                ]),
              }}
            >
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={trustSeries} margin={{ top: 8, right: 12, bottom: 0, left: -22 }}>
                  <CartesianGrid strokeDasharray="2 4" stroke={GRID_COLOR} vertical={false} />
                  <XAxis
                    dataKey="label"
                    tick={{ fill: AXIS_COLOR, fontSize: 10 }}
                    axisLine={{ stroke: GRID_COLOR }}
                    tickLine={false}
                    interval="preserveStartEnd"
                  />
                  <YAxis
                    domain={[0, 100]}
                    tick={{ fill: AXIS_COLOR, fontSize: 10 }}
                    axisLine={false}
                    tickLine={false}
                  />
                  <Tooltip
                    contentStyle={{
                      background: 'var(--bas-surface)',
                      border: '1px solid var(--bas-border)',
                      borderRadius: 6,
                      fontSize: 11,
                      color: 'var(--bas-text-primary)',
                    }}
                    labelFormatter={(label) => `${t('charts.labelWhen')} ${String(label)}`}
                  />
                  <Line
                    type="monotone"
                    dataKey="trust"
                    stroke="var(--bas-accent-cyan)"
                    strokeWidth={1.6}
                    dot={{ r: 2.6, fill: 'var(--bas-accent-cyan)' }}
                    activeDot={{ r: 4 }}
                    animationDuration={entrance.duration}
                    isAnimationActive={!reduced}
                  />
                </LineChart>
              </ResponsiveContainer>
            </ChartFrame>
          </div>
        </>
      )}
    </div>
  )
}