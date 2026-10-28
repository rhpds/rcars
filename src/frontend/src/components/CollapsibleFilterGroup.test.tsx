import { renderToStaticMarkup } from 'react-dom/server'
import { describe, expect, it } from 'vitest'
import { CollapsibleFilterGroup } from './CollapsibleFilterGroup'

const render = (props: Partial<Parameters<typeof CollapsibleFilterGroup>[0]> = {}) =>
  renderToStaticMarkup(
    <CollapsibleFilterGroup title="Platform" {...props}>
      <span>BODY</span>
    </CollapsibleFilterGroup>,
  )

describe('CollapsibleFilterGroup', () => {
  it('starts closed and hides its body and note', () => {
    const html = render({ note: 'NOTE' })
    expect(html).toContain('Platform')
    expect(html).toContain('aria-expanded="false"')
    expect(html).not.toContain('BODY')
    expect(html).not.toContain('NOTE')
  })

  it('starts open when defaultOpen is set', () => {
    const html = render({ defaultOpen: true, note: 'NOTE' })
    expect(html).toContain('aria-expanded="true"')
    expect(html).toContain('BODY')
    expect(html).toContain('NOTE')
  })

  it('starts open when a filter in it is already active', () => {
    expect(render({ activeCount: 2 })).toContain('BODY')
  })

  it('shows the active count when there is no clear action', () => {
    expect(render({ activeCount: 2 })).toContain('(2)')
    expect(render({ activeCount: 0 })).not.toContain('(0)')
  })

  it('shows a Clear button with the count when a clear action is given', () => {
    const html = render({ activeCount: 3, onClear: () => {} })
    expect(html).toContain('Clear (3)')
    expect(render({ activeCount: 0, onClear: () => {} })).not.toContain('Clear')
  })
})
