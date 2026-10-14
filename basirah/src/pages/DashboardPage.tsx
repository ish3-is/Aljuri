import { useEffect, useState } from 'react'
import { motion } from 'motion/react'
import { Info } from 'lucide-react'
import { Panel, SectionLabel } from '../components/ui/primitives'
import { StateBadge } from '../components/ui/StateBadge'
import { DashboardChartsSection } from './DashboardChartsSection'
import {
  activeCapabilities,
  limitedCapabilities,
  plannedCapabilities,
  platformStatus,
} from '../data/capabilities'
import {
  HISTORY_CHANGED_EVENT,
  loadHistory,
  type HistoryEntry,
} from '../features/analysis/historyStore'
import { useI18n } from '../i18n/useI18n'

/* ============================================================
   DASHBOARD / PLATFORM SUMMARY

   This is a status board, not an analytics dashboard. There is
   deliberately no chart, counter, percentage or sparkline here,
   because none of those numbers have been measured. The section
   says so explicitly rather than leaving the absence to be
   interpreted — a status page that silently omits metrics reads as
   an oversight, and the one thing this product must not do is let a
   reader assume a claim that was never made.

   What it does report: which modules exist, what state each is in,
   and which principles hold independently of module state.
   ============================================================ */

function ModuleList({
  titleKey,
  capabilities,
  startIndex,
}: {
  titleKey:
    | 'dashboard.activeModulesTitle'
    | 'dashboard.limitedModulesTitle'
    | 'dashboard.plannedModulesTitle'
  capabilities: typeof activeCapabilities
  startIndex: number
}) {
  const { t } = useI18n()

  return (
    <Panel className="p-6">
      <h3 className="text-sm text-text">{t(titleKey)}</h3>
      <span aria-hidden className="hairline mt-4 mb-1 block h-px" />
      <ul>
        {capabilities.map((capability, index) => (
          <motion.li
            key={capability.id}
            initial={{ opacity: 0, x: 8 }}
            whileInView={{ opacity: 1, x: 0 }}
            viewport={{ once: true, margin: '-30px' }}
            transition={{ delay: (startIndex + index) * 0.04, duration: 0.45 }}
            className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2 border-b border-line/40 py-3.5 last:border-b-0"
          >
            <div className="min-w-0">
              <p
                className={
                  capability.primary
                    ? 'text-[0.85rem] text-signal'
                    : 'text-[0.85rem] text-text'
                }
              >
                {t(capability.nameKey)}
              </p>
              <p className="mt-1 text-[0.7rem] leading-relaxed text-text-dim">
                {t(capability.bodyKey)}
              </p>
            </div>
            <StateBadge state={capability.state} still className="shrink-0" />
          </motion.li>
        ))}
      </ul>
    </Panel>
  )
}

export function DashboardPage() {
  const { t } = useI18n()

  /**
   * The reader's own local analysis record.
   *
   * `recordAnalysis` runs in the Analyze section — a different part
   * of the tree — and announces itself through a same-document
   * CustomEvent, which is what this subscribes to. The native
   * `storage` event is also handled because it is what fires when a
   * SECOND tab completes an analysis; neither alone is sufficient.
   */
  const [history, setHistory] = useState<HistoryEntry[]>(() => loadHistory())
  const [revision, setRevision] = useState(0)

  useEffect(() => {
    const refresh = () => {
      setHistory(loadHistory())
      setRevision((value) => value + 1)
    }
    window.addEventListener(HISTORY_CHANGED_EVENT, refresh)
    window.addEventListener('storage', refresh)
    return () => {
      window.removeEventListener(HISTORY_CHANGED_EVENT, refresh)
      window.removeEventListener('storage', refresh)
    }
  }, [])

  return (
    <div className="px-5 pt-28 pb-10 sm:px-8 sm:pt-32">
      <div className="mx-auto max-w-[1400px]">
        <motion.div
          initial={{ opacity: 0, y: 14 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        >
          <SectionLabel
            index="01"
            title={t('dashboard.title')}
            subtitle={t('dashboard.subtitle')}
            className="mb-10"
          />
        </motion.div>

        {/* Three groups, not two.
            PARTIAL support is structurally its own column: folding
            C2PA into the active list would let a limited module read
            as fully supported at a glance, and folding it into the
            planned list would understate it. */}
        <div className="grid gap-5 lg:grid-cols-2">
          <ModuleList
            titleKey="dashboard.activeModulesTitle"
            capabilities={activeCapabilities}
            startIndex={0}
          />
          <ModuleList
            titleKey="dashboard.limitedModulesTitle"
            capabilities={limitedCapabilities}
            startIndex={1}
          />
        </div>

        <div className="mt-5">
          <ModuleList
            titleKey="dashboard.plannedModulesTitle"
            capabilities={plannedCapabilities}
            startIndex={2}
          />
        </div>

        <DashboardChartsSection history={history} revision={revision} />

        {/* ---- Platform status table ---- */}
        <section className="mt-5">
          <Panel accent className="p-6 sm:p-8">
            <SectionLabel
              index="03"
              title={t('dashboard.statusTitle')}
              className="mb-6"
            />
            <ul className="divide-y divide-line/50 border-y border-line/50">
              {platformStatus.map((row, index) => (
                <motion.li
                  key={row.nameKey}
                  initial={{ opacity: 0 }}
                  whileInView={{ opacity: 1 }}
                  viewport={{ once: true, margin: '-30px' }}
                  transition={{ delay: index * 0.05, duration: 0.4 }}
                  className="flex items-center justify-between gap-4 py-3.5"
                >
                  <span className="text-[0.85rem] text-text-muted">
                    {t(row.nameKey)}
                  </span>
                  <StateBadge state={row.state} still />
                </motion.li>
              ))}
            </ul>
          </Panel>
        </section>

        {/* ---- Trust framework ---- */}
        <section className="mt-5">
          <Panel className="p-6 sm:p-8">
            <SectionLabel
              index="04"
              title={t('dashboard.trustFrameworkTitle')}
              subtitle={t('dashboard.trustFrameworkSub')}
              className="mb-6"
            />
            <div className="grid gap-5 md:grid-cols-3">
              {(
                [
                  ['dashboard.evidenceCorrelation', 'dashboard.trustCorrelationBody'],
                  ['dashboard.probabilistic', 'dashboard.trustProbabilisticBody'],
                  ['dashboard.advisoryOnly', 'dashboard.trustAdvisoryBody'],
                ] as const
              ).map(([titleKey, bodyKey]) => (
                <div key={titleKey}>
                  <p className="text-[0.88rem] text-text">{t(titleKey)}</p>
                  <p className="mt-2 text-[0.78rem] leading-relaxed text-text-dim">
                    {t(bodyKey)}
                  </p>
                </div>
              ))}
            </div>
          </Panel>
        </section>

        {/* ---- Why there are no numbers ---- */}
        <section className="mt-5">
          <div className="rounded-lg border border-caution/20 bg-caution/[0.05] p-6 sm:p-7">
            <div className="flex items-start gap-3">
              <Info size={15} className="mt-0.5 shrink-0 text-caution" />
              <div>
                <p className="text-[0.85rem] text-caution">
                  {t('dashboard.honestyNoteTitle')}
                </p>
                <p className="mt-2 max-w-3xl text-[0.8rem] leading-relaxed text-text-muted">
                  {t('dashboard.honestyNoteBody')}
                </p>
              </div>
            </div>
          </div>
        </section>
      </div>
    </div>
  )
}