import { motion } from 'motion/react'
import { useCallback, useMemo, useState } from 'react'
import { useI18n } from '../../i18n/useI18n'
import { cn } from '../../lib/utils'
import { getConfidenceDisplay } from '../../lib/display'
import { EVIDENCE_FILTERS } from '../../lib/filters'
import type { EvidenceEdge, EvidenceGraph, EvidenceNode } from '../../types/analysis'
import type { FilterKind } from '../../lib/filters'

/* ============================================================
   EVIDENCE GRAPH — Phase 4 Enhanced

   Groups nodes by stage: Input → Extraction → Verification → Intelligence → Correlation → Decision
   Displays correlations, supports filtering, shows confidence indicators.
   ============================================================ */

const VIEW = 100
const PAD = 13

function project(node: EvidenceNode): { x: number; y: number } {
  return {
    x: PAD + (node.x / 100) * (VIEW - PAD * 2),
    y: PAD + (node.y / 100) * (VIEW - PAD * 2),
  }
}

const POLARITY_COLOR: Record<EvidenceNode['polarity'], string> = {
  risk: 'var(--color-danger)',
  neutral: 'var(--color-signal)',
  trust: 'var(--color-trusted)',
}

interface EvidenceGraphViewProps {
  graph: EvidenceGraph
  correlations?: Array<{ conflictType: string; evidenceA: string; evidenceB: string; severity: string; explanation: string; entities: string[] }>
}

export function EvidenceGraphView({ graph, correlations = [] }: EvidenceGraphViewProps) {
  const { t, language } = useI18n()
  const [selected, setSelected] = useState<string | null>(null)
  const [hovered, setHovered] = useState<string | null>(null)
  const [activeFilter, setActiveFilter] = useState<FilterKind | null>(null)

  const activeId = hovered ?? selected

  const positions = useMemo(() => {
    const map = new Map<string, { x: number; y: number }>()
    for (const node of graph.nodes) map.set(node.id, project(node))
    return map
  }, [graph])

  const activeNode = useMemo(
    () => graph.nodes.find((node) => node.id === activeId) ?? null,
    [activeId, graph.nodes],
  )

  /** An edge is "in path" when both of its ends are in the active set. */
  const edgeInPath = (edge: EvidenceEdge) =>
    activeId !== null &&
    (edge.from === activeId || edge.to === activeId) &&
    positions.has(edge.from) &&
    positions.has(edge.to)

  const toggle = useCallback((id: string) => {
    setSelected((prev) => (prev === id ? null : id))
  }, [])

  /** Apply active filter to node list */
  const filteredNodes = useMemo(() => {
    if (!activeFilter) return graph.nodes
    return graph.nodes.filter((node) => {
      if (activeFilter === 'verified' && node.weight === 'primary') return true
      if (activeFilter === 'risk' && node.polarity === 'risk') return true
      if (activeFilter === 'trust' && node.polarity === 'trust') return true
      if (activeFilter === 'conflict' && correlations.some(c => c.evidenceA === node.id || c.evidenceB === node.id)) return true
      if (activeFilter === 'unavailable' && (!node.detailEn || node.detailEn.includes('Unavailable'))) return true
      return false
    })
  }, [graph.nodes, activeFilter, correlations])

  return (
      <div className="w-full">
        {/* Filter bar */}
        {activeFilter && (
          <div className="mb-3 flex flex-wrap gap-2">
            <span className="text-sm text-muted-foreground">{t('graphFilterTitle')}</span>
            {EVIDENCE_FILTERS.map((f) => (
              <button
                key={f.kind}
                onClick={() => setActiveFilter(f.kind === activeFilter ? null : f.kind)}
                className={cn(
                  'px-2 py-1 text-xs rounded border',
                  activeFilter === f.kind
                    ? 'bg-accent border-accent-text text-accent-text'
                    : 'border-border hover:bg-muted'
                )}
              >
                {f.label}
              </button>
            ))}
            <button
              onClick={() => setActiveFilter(null)}
              className="text-xs text-muted-foreground hover:text-foreground"
            >
              {t('filterClear')}
            </button>
          </div>
        )}

        {/* ---- PRINT-ONLY TEXTUAL FALLBACK ---- */}
        <div className="basirah-graph-text">
          <ul>
            {filteredNodes.map((node) => {
              const conf = getConfidenceDisplay(node.weight === 'primary' ? 'verified' : 'weak')
              return (
                <li key={`print-${node.id}`} style={{ marginBottom: '6pt' }}>
                  <strong>{language === 'ar' ? node.labelAr : node.labelEn}</strong>{' '}
                  <em>({node.polarity} / {node.weight} / {conf.label})</em>
                  <div>
                    {language === 'ar' ? node.detailAr : node.detailEn}
                  </div>
                </li>
              )
            })}
          </ul>
          {graph.edges.length > 0 && (
            <div>
              <strong>{t('graph.subtitle')}</strong>
              <ul>
                {graph.edges.map((edge, index) => {
                  const from = graph.nodes.find((n) => n.id === edge.from)
                  const to = graph.nodes.find((n) => n.id === edge.to)
                  const label = (node?: EvidenceNode) =>
                    node ? (language === 'ar' ? node.labelAr : node.labelEn) : edge.from
                  return (
                    <li key={`print-edge-${index}`}>
                      {label(from)} → {label(to)} ({edge.relation})
                    </li>
                  )
                })}
              </ul>
            </div>
          )}
          {correlations.length > 0 && (
            <div>
              <strong>{t('graphCorrelations')}</strong>
              <ul className="ml-4 list-disc">
                {correlations.map((c, i) => (
                  <li key={`corr-${i}`}>
                    <strong>{c.conflictType}:</strong> {c.explanation}
                  </li>
                ))}
              </ul>
            </div>
          )}
        </div>

        <div className="basirah-graph-visual grid gap-5 lg:grid-cols-[minmax(0,1fr)_16rem]">
          {/* Graph canvas */}
          <div className="relative">
          <svg
            viewBox={`0 0 ${VIEW} ${VIEW}`}
            className="mx-auto w-full max-w-[560px] touch-manipulation"
            role="application"
            aria-label={t('graph.title')}
            onClick={() => setSelected(null)}
          >
            <defs>
              <marker
                id="edge-arrow"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="4"
                markerHeight="4"
                orient="auto-start-reverse"
              >
                <path d="M0 0L10 5L0 10z" fill="var(--color-line-bright)" />
              </marker>
              <marker
                id="edge-arrow-active"
                viewBox="0 0 10 10"
                refX="8"
                refY="5"
                markerWidth="4"
                markerHeight="4"
                orient="auto-start-reverse"
              >
                <path d="M0 0L10 5L0 10z" fill="var(--color-signal)" />
              </marker>
            </defs>

            {/* Edges */}
            <g>
              {graph.edges.map((edge, index) => {
                const from = positions.get(edge.from)
                const to = positions.get(edge.to)
                if (!from || !to) return null

                const inPath = edgeInPath(edge)
                const dashed = edge.relation === 'contradicts'
                const stroke = inPath ? 'var(--color-signal)' : 'var(--color-line-bright)'
                const opacity = activeId === null ? 0.55 : inPath ? 0.95 : 0.15

                return (
                  <g key={`${edge.from}-${edge.to}-${index}`}>
                    <motion.line
                      x1={from.x}
                      y1={from.y}
                      x2={to.x}
                      y2={to.y}
                      stroke={stroke}
                      strokeWidth={inPath ? 0.7 : 0.5}
                      strokeDasharray={dashed ? '2 2' : undefined}
                      markerEnd={inPath ? 'url(#edge-arrow-active)' : 'url(#edge-arrow)'}
                      animate={{ opacity }}
                      transition={{ duration: 0.3 }}
                    />
                    {inPath && (
                      <motion.circle
                        r="1.1"
                        fill="var(--color-signal)"
                        initial={{ cx: from.x, cy: from.y, opacity: 0 }}
                        animate={{
                          cx: to.x,
                          cy: to.y,
                          opacity: [0, 1, 0],
                        }}
                        transition={{
                          duration: 1.4,
                          repeat: Infinity,
                          ease: 'linear',
                        }}
                      />
                    )}
                  </g>
                )
              })}
            </g>

            {/* Nodes */}
            <g>
              {filteredNodes.map((node) => {
                const conf = getConfidenceDisplay(node.weight === 'primary' ? 'verified' : 'weak')
                const pos = positions.get(node.id)
                if (!pos) return null
                const isSelected = selected === node.id
                const isHovered = hovered === node.id

                return (
                  <g
                    key={node.id}
                    onClick={() => toggle(node.id)}
                    onMouseEnter={() => setHovered(node.id)}
                    onMouseLeave={() => setHovered(null)}
                    style={{ cursor: 'pointer' }}
                  >
                    {isHovered && (
                      <circle
                        cx={pos.x}
                        cy={pos.y}
                        r="20"
                        fill="none"
                        stroke="var(--color-signal)"
                        strokeWidth="1"
                        opacity="0.2"
                        style={{ transition: 'opacity 0.3s' }}
                      />
                    )}
                    <motion.circle
                      cx={pos.x}
                      cy={pos.y}
                      r={node.weight === 'primary' ? 10 : 8}
                      fill={POLARITY_COLOR[node.polarity]}
                      stroke={isSelected ? 'var(--color-signal)' : 'none'}
                      strokeWidth={isSelected ? 2 : 0}
                      animate={{ r: node.weight === 'primary' ? 10 : 8 }}
                      transition={{ duration: 0.3 }}
                    >
                      <title>
                        {language === 'ar' ? node.labelAr : node.labelEn} — {conf.label}
                      </title>
                    </motion.circle>
                    <text
                      x={pos.x}
                      y={pos.y - 16}
                      textAnchor="middle"
                      fontSize="6"
                      fill="var(--color-foreground)"
                      className="select-none"
                    >
                      {language === 'ar' ? node.labelAr : node.labelEn}
                    </text>
                  </g>
                )
              })}
            </g>
          </svg>
          </div>

          {/* Detail panel */}
          <div className="space-y-2">
            {activeNode ? (
              <div className="rounded border bg-card p-3 space-y-2">
                <div className="flex items-center justify-between">
                  <h3 className="font-semibold">
                    {language === 'ar' ? activeNode.labelAr : activeNode.labelEn}
                  </h3>
                  <span className="text-xs text-muted-foreground">
                    {activeNode.polarity} / {activeNode.weight}
                  </span>
                </div>
                <p className="text-sm">
                  {language === 'ar' ? activeNode.detailAr : activeNode.detailEn}
                </p>
                <div className="mt-2 text-xs text-muted-foreground">
                  {t('graphDetailLabel')}
                </div>
              </div>
            ) : (
              <div className="rounded border bg-card p-3 text-sm text-muted-foreground">
                {t('graph.select')}
              </div>
            )}
          </div>
        </div>
      </div>
  )
}
