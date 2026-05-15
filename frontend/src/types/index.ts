// ── Skill ────────────────────────────────────────────────────────────────────

export interface SkillIn {
  name: string
  level: number // 1–5
}

export interface SkillOut {
  name: string
  level: number
  weight: number
}

// ── Participant ───────────────────────────────────────────────────────────────

export interface ParticipantIn {
  name: string
  skills?: SkillIn[]
  compatibility_tags?: string[]
}

export interface ParticipantUpdate {
  name?: string
  skills?: SkillIn[]
  compatibility_tags?: string[]
}

export interface ParticipantOut {
  id: string
  name: string
  total_score: number
  compatibility_tags: string[]
  skills: SkillOut[]
  team_id: string | null
}

// ── Team ─────────────────────────────────────────────────────────────────────

export interface TeamOut {
  id: string
  name: string
  total_score: number
  participants: ParticipantOut[]
}

// ── Session ───────────────────────────────────────────────────────────────────

export type SessionStatus = 'pending' | 'distributed' | 'closed'

export interface SessionIn {
  name: string
  team_count: number
  min_team_size?: number
  max_team_size?: number
}

export interface SessionOut {
  id: string
  name: string
  team_count: number
  min_team_size: number
  max_team_size: number
  status: SessionStatus
  organizer_token: string | null
  participants: ParticipantOut[]
  teams: TeamOut[]
}

// ── Distribution ─────────────────────────────────────────────────────────────

export interface DistributeIn {
  use_compatibility?: boolean
  balance_threshold?: number
}

export interface MoveParticipantIn {
  participant_id: string
  target_team_id: string
}

// ── Misc ─────────────────────────────────────────────────────────────────────

export interface MessageOut {
  message: string
}

export interface ImportResultOut {
  imported: number
  message: string
}
