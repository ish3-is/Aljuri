/**
 * Project team registry.
 *
 * Real, confirmed members of the BASIRAH graduation project. Names,
 * student IDs and the specialization are the authoritative values —
 * nothing here is a placeholder, and nothing is invented.
 *
 * Only the first member carries `isLeader`. The badge renders from that
 * flag, so there is exactly one Leader in the interface by construction
 * rather than by styling luck.
 *
 * No photographs are used: every member renders as an initials
 * placeholder, which is honest about what the project has and avoids
 * implying that portraits exist.
 */

export interface ProjectMember {
  name: string
  studentId: string
  specialization: string
  /** Exactly one member sets this. */
  isLeader?: boolean
}

/**
 * Member #1 is the project leader. Order is the displayed order and is
 * kept stable: leader first, then the rest as registered.
 */
export const projectMembers: ProjectMember[] = [
  {
    name: 'ALJURI TURKI ALMUAWI',
    studentId: '444802018',
    specialization: 'Artificial Intelligence',
    isLeader: true,
  },
  {
    name: 'Ghadeer Salman Al-hejji',
    studentId: '446802941',
    specialization: 'Artificial Intelligence',
  },
  {
    name: 'Abrar Mohammed Al-Shahrani',
    studentId: '444803701',
    specialization: 'Artificial Intelligence',
  },
  {
    name: 'Munira Fahid Al-muky',
    studentId: '444802001',
    specialization: 'Artificial Intelligence',
  },
  {
    name: 'Mona Ali',
    studentId: '443804670',
    specialization: 'Artificial Intelligence',
  },
  {
    name: 'Danah Abdulalim',
    studentId: '444801996',
    specialization: 'Artificial Intelligence',
  },
]

/** Guard used by the team section to decide between grid and empty state. */
export const hasProjectMembers = projectMembers.length > 0

/**
 * Up to two initials for the avatar placeholder. Derived, never stored:
 * a stored initials field would inevitably drift from the name.
 */
export function initialsOf(name: string): string {
  const parts = name.trim().split(/\s+/).filter(Boolean)
  if (parts.length === 0) return '?'
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase()
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase()
}
