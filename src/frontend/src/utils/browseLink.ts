/** RCARS Browse URL for a catalog item, with the stage toggle on so dev/event items show up. */
export function browseStageUrl(displayName: string, stage: string): string {
  return `/browse?search=${encodeURIComponent(displayName)}&stage=${encodeURIComponent(stage)}`
}
