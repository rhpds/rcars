import { describe, expect, it } from 'vitest'
import { contentTypeParam, isArchitecture, isZtItem, itemKey } from './helpers'

describe('contentTypeParam', () => {
  it('sends the explicit hands-on set by default', () => {
    expect(contentTypeParam(new Set(['hands_on']))).toBe('lab,demo,sandbox')
  })

  it('is additive when architectures are selected', () => {
    expect(contentTypeParam(new Set(['hands_on', 'architecture'])))
      .toBe('lab,demo,sandbox,architecture')
  })

  it('can select architectures only', () => {
    expect(contentTypeParam(new Set(['architecture']))).toBe('architecture')
  })

  it('falls back to the hands-on default when nothing is selected', () => {
    expect(contentTypeParam(new Set())).toBe('lab,demo,sandbox')
  })
})

describe('itemKey', () => {
  it('prefers content_id, which every row has', () => {
    expect(itemKey({ content_id: 'pa:275', ci_name: null })).toBe('pa:275')
    expect(itemKey({ content_id: 'babylon:a.prod', ci_name: 'a.prod' })).toBe('babylon:a.prod')
  })

  it('falls back to ci_name', () => {
    expect(itemKey({ ci_name: 'a.prod' })).toBe('a.prod')
  })
})

describe('isZtItem', () => {
  it('does not throw when ci_name is null', () => {
    expect(isZtItem({ catalog_namespace: null, ci_name: null })).toBe(false)
  })

  it('detects ZT items by namespace or ci_name', () => {
    expect(isZtItem({ catalog_namespace: 'zt-foo', ci_name: null })).toBe(true)
    expect(isZtItem({ catalog_namespace: 'babylon-catalog-prod', ci_name: 'zt-bar.prod' })).toBe(true)
    expect(isZtItem({ catalog_namespace: 'babylon-catalog-prod', ci_name: 'a.prod' })).toBe(false)
  })
})

describe('isArchitecture', () => {
  it('keys off source, so future sources inherit the same rule', () => {
    expect(isArchitecture({ source: 'portfolio_arch' })).toBe(true)
    expect(isArchitecture({ source: 'babylon' })).toBe(false)
    expect(isArchitecture({})).toBe(false)
  })
})

import { architectureDetailUrl, architectureSubline, assetTypeLabel } from './helpers'

describe('assetTypeLabel', () => {
  it('maps each asset type to its full name', () => {
    expect(assetTypeLabel('PA')).toBe('Portfolio Architecture')
    expect(assetTypeLabel('SP')).toBe('Solution Pattern')
    expect(assetTypeLabel('VP')).toBe('Validated Pattern')
  })

  it('prefers Validated Pattern when a row carries both', () => {
    expect(assetTypeLabel('PA,VP')).toBe('Validated Pattern')
    expect(assetTypeLabel(' pa , vp ')).toBe('Validated Pattern')
  })

  it('falls back to Architecture, never Reference Architecture', () => {
    expect(assetTypeLabel(null)).toBe('Architecture')
    expect(assetTypeLabel('')).toBe('Architecture')
    expect(assetTypeLabel('Whatever')).toBe('Architecture')
  })
})

describe('architectureDetailUrl', () => {
  it('builds the Architecture Center URL from pa_name', () => {
    expect(architectureDetailUrl('275-rhacs-multitenant'))
      .toBe('https://www.redhat.com/architect/portfolio/detail/275-rhacs-multitenant/')
  })

  it('returns # for a missing pa_name so the link is inert', () => {
    expect(architectureDetailUrl(null)).toBe('#')
  })
})

describe('architectureSubline', () => {
  it('shows the slug and the primary solution', () => {
    expect(architectureSubline({ pa_name: '275-rhacs', solutions: ['Security', 'Platform'] }))
      .toBe('275-rhacs · Security')
  })

  it('falls back to Architecture with no solutions', () => {
    expect(architectureSubline({ pa_name: '275-rhacs', solutions: [] }))
      .toBe('275-rhacs · Architecture')
  })
})
