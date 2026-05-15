import type { SkillOut } from '../../types'

const LEVEL_COLOR: Record<number, string> = {
  1: 'bg-gray-100 text-gray-600',
  2: 'bg-blue-50 text-blue-700',
  3: 'bg-green-50 text-green-700',
  4: 'bg-yellow-50 text-yellow-700',
  5: 'bg-orange-50 text-orange-700',
}

export default function SkillBadge({ skill }: { skill: SkillOut }) {
  return (
    <span className={`badge ${LEVEL_COLOR[skill.level] ?? 'bg-gray-100 text-gray-600'}`}>
      {skill.name} {skill.level}/5
    </span>
  )
}
