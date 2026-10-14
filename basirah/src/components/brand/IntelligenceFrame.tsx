import { motion } from "motion/react";
import basirahMark from "../../assets/basirah-mark.png";
import { usePrefersReducedMotion } from "../../hooks/useEnvironment";
import { useI18n } from "../../i18n/useI18n";
import type { TranslationKey } from "../../i18n/translations";

/* ============================================================
   HERO INTELLIGENCE FRAME

   The mark, enlarged, inside a circular instrumentation frame that
   reads as an analysis instrument rather than a badge: a static
   segmented ring, a slowly travelling arc, a scanner sweep, and a
   six-label perimeter naming the modalities in scope.

   URL IS DELIBERATELY SECONDARY. It is the last label on the
   perimeter, set in the dimmest tier and given a shorter tick, which
   restates the product's own priority (images first, links second)
   visually rather than only in copy. Every label is Latin-only
   tooling vocabulary — these are instrumentation labels, and they
   read as such in both languages, exactly like the `mono-label`
   treatment elsewhere.

   RESPONSIVE: the frame is sized in viewport-relative clamp units
   rather than fixed pixels, so it shrinks on a phone instead of
   eating the first screen. The mark is sized by HEIGHT and its width
   follows the source aspect ratio (447:628), so it can never be
   stretched or cropped.
   ============================================================ */

interface PerimeterLabel {
  key: string;
  labelKey: TranslationKey;
  /** Angle in degrees, 0 = top, clockwise. */
  angle: number;
  /** Secondary labels render dimmer and smaller. */
  secondary?: boolean;
}

/**
 * Six modalities around the perimeter. The arc runs clockwise from
 * the top, and URL sits at the bottom where the eye lands last.
 */
const LABELS: PerimeterLabel[] = [
  { key: "image", labelKey: "hero.modImage", angle: 0 },
  { key: "evidence", labelKey: "hero.modEvidence", angle: 60 },
  { key: "trust", labelKey: "hero.modTrust", angle: 120 },
  { key: "files", labelKey: "hero.modFiles", angle: 180 },
  { key: "encoding", labelKey: "hero.modEncoding", angle: 240 },
  { key: "url", labelKey: "hero.modUrl", angle: 300, secondary: true },
];

export function IntelligenceFrame({ className }: { className?: string }) {
  const { t, tLatin } = useI18n();
  const reduced = usePrefersReducedMotion();
  const active = !reduced;

  // Mark height inside the frame. The clamp keeps it generous on
  // desktop and modest on a phone without a media query.
  const markHeight = "clamp(112px, 30svh, 232px)";
  const markWidth = `calc(${markHeight} * 0.7118)`;

  return (
    // The outer wrapper clips decoration. The ambient glow below uses a
    // negative inset so it can bleed past the ring; on a narrow viewport
    // that bleed widened the document and produced a horizontal scrollbar.
    // Clipping the halo is invisible (a soft radial edge is the same
    // either way) and keeps the frame the only thing that can be wider
    // than its container.
    <div
      className={`relative aspect-square w-full max-w-[440px] overflow-hidden ${className ?? ""}`}
    >
      <div
        className="relative size-full"
        role="img"
        aria-label={t("hero.frameLabel")}
      >
        {/* --- ambient glow, driven by the theme token so light mode
             gets a much softer halo automatically --- */}
        <motion.span
          aria-hidden
          className="pointer-events-none absolute -inset-[18%] rounded-full blur-[54px]"
          style={{
            background:
              "radial-gradient(circle at 50% 42%, color-mix(in srgb, var(--bas-accent-cyan) 26%, transparent) 0%, transparent 66%)",
            opacity: "var(--bas-glow-strength)",
          }}
          animate={active ? { opacity: [0.55, 1, 0.55] } : undefined}
          transition={{ duration: 8, repeat: Infinity, ease: "easeInOut" }}
        />

        {/* --- static segmented ring: the instrument's fixed scale --- */}
        <svg
          aria-hidden
          viewBox="0 0 400 400"
          className="pointer-events-none absolute inset-0 size-full"
        >
          <circle
            cx="200"
            cy="200"
            r="188"
            fill="none"
            stroke="var(--bas-border)"
            strokeWidth="1"
          />
          {/* Fine segmentation — 60 ticks reads as calibration marks. */}
          <g stroke="var(--bas-border-bright)" strokeWidth="1">
            {Array.from({ length: 60 }, (_, index) => {
              const angle = (index * 6 * Math.PI) / 180;
              const major = index % 5 === 0;
              const r1 = major ? 174 : 179;
              const r2 = 186;
              return (
                <line
                  key={index}
                  x1={200 + Math.cos(angle) * r1}
                  y1={200 + Math.sin(angle) * r1}
                  x2={200 + Math.cos(angle) * r2}
                  y2={200 + Math.sin(angle) * r2}
                  opacity={major ? 0.75 : 0.32}
                />
              );
            })}
          </g>

          {/* Six axis ticks, one per perimeter label. */}
          <g stroke="var(--bas-accent-cyan)" strokeWidth="1.25" opacity="0.6">
            {LABELS.map((label) => {
              const angle = (label.angle * Math.PI) / 180;
              return (
                <line
                  key={`axis-${label.key}`}
                  x1={200 + Math.cos(angle) * 164}
                  y1={200 + Math.sin(angle) * 164}
                  x2={200 + Math.cos(angle) * 186}
                  y2={200 + Math.sin(angle) * 186}
                  opacity={label.secondary ? 0.3 : 0.7}
                />
              );
            })}
          </g>
        </svg>

        {/* --- travelling arc: slow, one revolution --- */}
        <motion.svg
          aria-hidden
          viewBox="0 0 400 400"
          className="pointer-events-none absolute inset-0 size-full"
          animate={active ? { rotate: 360 } : undefined}
          transition={{ duration: 26, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "50% 50%" }}
        >
          <circle
            cx="200"
            cy="200"
            r="188"
            fill="none"
            stroke="var(--bas-accent-cyan)"
            strokeWidth="1.5"
            strokeLinecap="round"
            strokeDasharray="120 1060"
            opacity="0.85"
          />
        </motion.svg>

        {/* --- counter-rotating inner arc: counterpoint, not decoration
             for its own sake — it implies an instrument reading --- */}
        <motion.svg
          aria-hidden
          viewBox="0 0 400 400"
          className="pointer-events-none absolute inset-[7%] size-[86%]"
          animate={active ? { rotate: -360 } : undefined}
          transition={{ duration: 40, repeat: Infinity, ease: "linear" }}
          style={{ transformOrigin: "50% 50%" }}
        >
          <circle
            cx="200"
            cy="200"
            r="188"
            fill="none"
            stroke="var(--bas-accent-violet)"
            strokeWidth="1"
            strokeDasharray="6 22"
            strokeLinecap="round"
            opacity="0.35"
          />
        </motion.svg>

        {/* --- scanner sweep: a soft radial wash rotating slowly across
             the mark. Reduced-motion: absent, not merely faster. --- */}
        {active && (
          <motion.span
            aria-hidden
            className="pointer-events-none absolute inset-[9%] overflow-hidden rounded-full"
            animate={{ rotate: 360 }}
            transition={{ duration: 9, repeat: Infinity, ease: "linear" }}
          >
            <span
              className="absolute inset-0"
              style={{
                background:
                  "conic-gradient(from 0deg, transparent 0deg, color-mix(in srgb, var(--bas-accent-cyan) 16%, transparent) 42deg, transparent 96deg, transparent 360deg)",
              }}
            />
          </motion.span>
        )}

        {/* --- the mark itself, sized by height --- */}
        <div className="absolute inset-0 flex items-center justify-center">
          <img
            src={basirahMark}
            alt={tLatin("brand.name")}
            style={{ height: markHeight, width: markWidth }}
            decoding="async"
            className="relative z-10 h-auto w-auto max-w-full select-none object-contain"
            draggable={false}
          />
        </div>

        {/* --- perimeter labels --- */}
        {LABELS.map((label) => {
          const radians = (label.angle * Math.PI) / 180;
          const radius = 42.5; // percent, from centre
          return (
            <span
              key={label.key}
              aria-hidden
              dir="ltr"
              className={
                label.secondary
                  ? "absolute top-1/2 start-1/2 -translate-y-1/2 -translate-x-1/2 text-[0.5rem] tracking-[0.18em] text-text-dim/60 uppercase sm:text-[0.56rem]"
                  : "absolute top-1/2 start-1/2 -translate-y-1/2 -translate-x-1/2 text-[0.52rem] tracking-[0.2em] text-signal/75 uppercase sm:text-[0.6rem]"
              }
              style={{
                left: `${50 + Math.sin(radians) * radius}%`,
                top: `${50 - Math.cos(radians) * radius}%`,
                transform: "translate(-50%, -50%)",
              }}
            >
              {tLatin(label.labelKey)}
            </span>
          );
        })}

        {/* --- scanner readout under the frame, purely typographic --- */}
        <span
          aria-hidden
          dir="ltr"
          className="mono-label absolute -bottom-1 start-1/2 -translate-x-1/2 text-[0.5rem] text-text-dim/70"
        >
          {tLatin("brand.subtitle")}
        </span>
      </div>
    </div>
  );
}
