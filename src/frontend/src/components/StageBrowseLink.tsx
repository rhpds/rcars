import type { CSSProperties } from 'react'
import { useAuth } from '../hooks/useAuth'

const stageBadgeClass: Record<string, string> = {
  prod: 'ca-env-prod', event: 'ca-env-event', dev: 'ca-env-dev', test: 'ca-env-test',
}

interface Props {
  displayName: string
  stage: string
  style?: CSSProperties
}

/**
 * Environment badge that opens RCARS Browse with the stage toggle on.
 * Browse only supports prod for everyone, dev/event for curators and admins,
 * and has no test stage, so those badges render as plain text.
 */
export function StageBrowseLink({ displayName, stage, style }: Props) {
  const { isCurator, isAdmin } = useAuth()
  const className = `ca-env-tag ${stageBadgeClass[stage] || 'ca-env-test'}`
  const canBrowse = stage === 'prod' || ((stage === 'dev' || stage === 'event') && (isCurator || isAdmin))
  if (!canBrowse) return <span className={className} style={style}>{stage}</span>
  const href = `/browse?search=${encodeURIComponent(displayName)}&stage=${encodeURIComponent(stage)}`
  return (
    <a href={href} target="_blank" rel="noreferrer" className={className} style={style}
      onClick={e => e.stopPropagation()}>
      {stage}
    </a>
  )
}
