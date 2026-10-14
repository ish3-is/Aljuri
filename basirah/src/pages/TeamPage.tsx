import { motion } from 'motion/react'
import { Crown } from 'lucide-react'
import { Panel, SectionLabel } from '../components/ui/primitives'
import { UniversityAffiliation } from '../components/brand/UniversityAffiliation'
import {
  hasProjectMembers,
  initialsOf,
  projectMembers,
} from '../data/projectMembers'
import { useI18n } from '../i18n/useI18n'

/* ============================================================
   TEAM

   Cards, not an HR directory: name, student ID, specialization,
   and an initials avatar. No photographs exist for this project and
   none are implied.

   The Leader badge renders from `member.isLeader`, so exactly one
   card can carry it. The leader is also listed first and gets a
   slightly stronger surface — the distinction is structural, not
   a decorative flourish.

   Student IDs are LTR-embedded even in the Arabic experience: a
   number run must never be reordered by the bidi algorithm.
   ============================================================ */

export function TeamPage() {
  const { t } = useI18n()

  if (!hasProjectMembers) {
    return (
      <div className="px-5 pt-28 pb-10 sm:px-8 sm:pt-32">
        <div className="mx-auto max-w-[1400px]">
          <SectionLabel index="01" title={t('team.title')} className="mb-8" />
          <p className="text-[0.85rem] text-text-dim">{t('about.membersTitle')}</p>
        </div>
      </div>
    )
  }

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
            title={t('team.title')}
            subtitle={t('team.subtitle')}
            className="mb-10"
          />
        </motion.div>

        <ul className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
          {projectMembers.map((member, index) => (
            <motion.li
              key={member.studentId}
              initial={{ opacity: 0, y: 16 }}
              whileInView={{ opacity: 1, y: 0 }}
              viewport={{ once: true, margin: '-40px' }}
              transition={{ delay: (index % 3) * 0.06, duration: 0.5 }}
              className={
                member.isLeader
                  ? 'relative overflow-hidden rounded-lg border border-signal/28 bg-signal/[0.05] p-6'
                  : 'relative overflow-hidden rounded-lg border border-line/70 bg-surface/40 p-6'
              }
            >
              {member.isLeader && (
                <span
                  aria-hidden
                  className="absolute inset-x-0 top-0 h-px bg-gradient-to-r from-transparent via-signal/50 to-transparent"
                />
              )}

              {/* Initials avatar — a placeholder, honestly */}
              <div className="flex items-center gap-4">
                <span
                  aria-hidden
                  className={
                    member.isLeader
                      ? 'flex size-12 shrink-0 items-center justify-center rounded-lg border border-signal/30 bg-signal/10 font-mono text-[0.8rem] tracking-wider text-signal'
                      : 'flex size-12 shrink-0 items-center justify-center rounded-lg border border-line bg-surface font-mono text-[0.8rem] tracking-wider text-text-dim'
                  }
                >
                  {initialsOf(member.name)}
                </span>

                <div className="min-w-0 flex-1">
                  {member.isLeader && (
                    <span className="inline-flex items-center gap-1.5 rounded-full border border-signal/35 bg-signal/10 px-2.5 py-0.5 text-[0.6rem] tracking-[0.14em] text-signal uppercase">
                      <Crown size={10} />
                      {t('team.leader')}
                    </span>
                  )}
                </div>
              </div>

              <p
                dir="ltr"
                className={
                  member.isLeader
                    ? 'mt-5 text-start text-[0.98rem] leading-snug text-signal'
                    : 'mt-5 text-start text-[0.9rem] leading-snug text-text'
                }
              >
                {member.name}
              </p>

              <dl className="mt-4 space-y-2.5 text-[0.75rem]">
                <div className="flex items-baseline justify-between gap-3">
                  <dt className="text-text-dim">{t('team.studentIdLabel')}</dt>
                  <dd className="ltr-embed text-text-muted">{member.studentId}</dd>
                </div>
                <div className="flex items-baseline justify-between gap-3">
                  <dt className="shrink-0 text-text-dim">
                    {t('team.specializationLabel')}
                  </dt>
                  <dd dir="ltr" className="text-end text-text-muted">
                    {member.specialization}
                  </dd>
                </div>
                <div className="flex items-baseline justify-between gap-3">
                  <dt className="text-text-dim">{t('team.roleLabel')}</dt>
                  <dd className="text-text-muted">
                    {member.isLeader ? t('team.leader') : t('team.member')}
                  </dd>
                </div>
              </dl>
            </motion.li>
          ))}
        </ul>

        {/* ---- Academic affiliation, directly under the roster ---- */}
        <section className="mt-12">
          <Panel accent className="flex flex-col items-start gap-6 p-6 sm:flex-row sm:items-center sm:justify-between sm:p-7">
            <div className="min-w-0">
              <p className="mono-label text-signal/70">
                {t('team.universityTitle')}
              </p>
              <p className="mt-2 text-[0.95rem] text-text">
                {t('team.universityName')}
              </p>
              <p className="mt-1.5 text-[0.78rem] text-text-dim">
                {t('team.universitySub')}
              </p>
            </div>
            <UniversityAffiliation width={168} markOnly className="shrink-0 sm:ps-6" />
          </Panel>
        </section>
      </div>
    </div>
  )
}