import { describe, expect, it } from 'vitest'
import { NONE_LABEL, labelDisplay, matchesLabels, countLabelValues } from './labelFilters'

describe('labelDisplay', () => {
  it('replaces underscores with spaces', () => {
    expect(labelDisplay('Ansible_Automation')).toBe('Ansible Automation')
  })

  it('converts NONE_LABEL to "None"', () => {
    expect(labelDisplay(NONE_LABEL)).toBe('None')
  })
})

describe('matchesLabels', () => {
  it('returns true when selected is empty', () => {
    expect(matchesLabels(['OpenShift'], new Set())).toBe(true)
  })

  it('returns false when values do not match selected', () => {
    expect(matchesLabels(['OpenShift'], new Set(['AI']))).toBe(false)
  })

  it('returns true when any value is in selected', () => {
    expect(matchesLabels(['AI', 'OpenShift'], new Set(['AI']))).toBe(true)
  })

  it('returns true when values is empty and NONE_LABEL is selected', () => {
    expect(matchesLabels([], new Set([NONE_LABEL]))).toBe(true)
  })

  it('returns true when values is empty and NONE_LABEL is among selected', () => {
    expect(matchesLabels([], new Set(['AI', NONE_LABEL]))).toBe(true)
  })

  it('returns false when values has items but NONE_LABEL is selected', () => {
    expect(matchesLabels(['AI'], new Set([NONE_LABEL]))).toBe(false)
  })
})

describe('countLabelValues', () => {
  it('counts each value once per item, with NONE_LABEL for empty, sorted by count desc then name', () => {
    const items = [
      { v: ['A'] },
      { v: ['A', 'B'] },
      { v: [] }
    ]
    const result = countLabelValues(items, i => i.v)
    expect(result).toEqual([
      ['A', 2],
      ['B', 1],
      [NONE_LABEL, 1]
    ])
  })
})
