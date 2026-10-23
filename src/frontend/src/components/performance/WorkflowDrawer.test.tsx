import { act, type ReactElement } from 'react'
import type { RetirementWorkflow } from '../../services/api'
import { afterEach, expect, it, vi } from 'vitest'
import { WorkflowDrawer } from './WorkflowDrawer'
import { api } from '../../services/api'

const hooks = vi.hoisted(() => ({ effects: [] as Array<() => void>, setWorkflow: vi.fn(), index: 0, workflow: null as RetirementWorkflow | null }))
vi.mock('react', async importOriginal => ({
  ...await importOriginal<typeof import('react')>(),
  useEffect: (effect: () => void) => { hooks.effects.push(effect) },
  useState: (value: unknown) => { const index = hooks.index++; return [index === 0 ? hooks.workflow ?? value : value, index === 0 ? hooks.setWorkflow : vi.fn()] },
}))
vi.mock('../../hooks/useAuth', () => ({ useAuth: () => ({ isAdmin: true }) }))
vi.mock('../../services/api', () => ({ api: { getRetirementWorkflow: vi.fn(), checkAgvPrStatuses: vi.fn() } }))

afterEach(() => { vi.clearAllMocks(); vi.unstubAllGlobals(); hooks.effects = []; hooks.index = 0; hooks.workflow = null })

function findButton(node: unknown, label: string): ReactElement<{ onClick: () => void; disabled?: boolean }> | undefined {
  if (!node || typeof node !== 'object') return
  if (Array.isArray(node)) return node.map(child => findButton(child, label)).find(Boolean)
  const element = node as ReactElement<{ children?: unknown; onClick: () => void }>
  if (element.type === 'button' && element.props.children === label) return element
  return findButton(element.props?.children, label)
}

function findLink(node: unknown, href: string): ReactElement<{ href: string }> | undefined {
  if (!node || typeof node !== 'object') return
  if (Array.isArray(node)) return node.map(child => findLink(child, href)).find(Boolean)
  const element = node as ReactElement<{ children?: unknown; href: string }>
  if (element.type === 'a' && element.props.href === href) return element
  return findLink(element.props?.children, href)
}

it('warns that Jira closure is required before cancelling', async () => {
  hooks.workflow = { jira_key: 'EXAMPLE-1', step_started_at: '2026-10-15', step_approved_at: '2026-10-15' } as RetirementWorkflow
  const confirm = vi.fn().mockReturnValue(false)
  vi.stubGlobal('confirm', confirm)
  const tree = WorkflowDrawer({ item: { catalog_base_name: 'example.item', display_name: 'Example', provisions: 0, unique_users: 0, experiences: 0, success_ratio: 0 }, onClose: vi.fn(), onChanged: vi.fn() })
  const stop = findButton(tree, 'Stop Retirement')
  expect(stop).toBeDefined()
  await stop!.props.onClick()
  expect(confirm).toHaveBeenCalledWith(expect.stringContaining('close EXAMPLE-1'))
  expect(confirm).toHaveBeenCalledWith(expect.stringContaining('Won’t Do'))
  expect(confirm).toHaveBeenCalledWith(expect.stringContaining('retained until'))
})

it.each([
  { label: 'completed workflow', workflow: { step_retired_at: '2026-10-03', status: 'retired' }, retired_at: null, disabled: true },
  { label: 'retired workflow status', workflow: { status: 'retired' }, retired_at: null, disabled: true },
  { label: 'catalog retirement without completed workflow', workflow: {}, retired_at: '2026-10-03', disabled: true },
  { label: 'active item', workflow: {}, retired_at: null, disabled: false },
])('gates new PR and stop buttons for $label', ({ workflow, retired_at, disabled }) => {
  hooks.workflow = { step_started_at: '2026-09-25', step_approved_at: '2026-09-25', ...workflow } as RetirementWorkflow
  const tree = WorkflowDrawer({ item: { catalog_base_name: 'example.item', display_name: 'Example', provisions: 0, unique_users: 0, experiences: 0, success_ratio: 0, retired_at }, onClose: vi.fn(), onChanged: vi.fn() })

  for (const label of ['Open Notice PR', 'Open Removal PR', 'Stop Retirement']) {
    const button = findButton(tree, label)
    expect(button).toBeDefined()
    expect(button!.props.disabled).toBe(disabled)
  }
})

it('does not offer PR creation for a legacy retired item without a workflow', () => {
  const tree = WorkflowDrawer({ item: { catalog_base_name: 'example.item', display_name: 'Example', provisions: 0, unique_users: 0, experiences: 0, success_ratio: 0, retired_at: '2026-10-03' }, onClose: vi.fn(), onChanged: vi.fn() })

  expect(findButton(tree, 'Open Notice PR')).toBeUndefined()
  expect(findButton(tree, 'Open Removal PR')).toBeUndefined()
})

it('keeps historical PR links readable for a retired item', () => {
  hooks.workflow = {
    step_started_at: '2026-09-25', step_retired_at: '2026-10-03', status: 'retired',
    agv_notice_pr_url: 'https://example.com/pull/1', agv_retire_pr_url: 'https://example.com/pull/2',
  } as RetirementWorkflow
  const tree = WorkflowDrawer({ item: { catalog_base_name: 'example.item', display_name: 'Example', provisions: 0, unique_users: 0, experiences: 0, success_ratio: 0, retired_at: '2026-10-03' }, onClose: vi.fn(), onChanged: vi.fn() })

  expect(findLink(tree, 'https://example.com/pull/1')).toBeDefined()
  expect(findLink(tree, 'https://example.com/pull/2')).toBeDefined()
  expect(findButton(tree, 'Open Notice PR')).toBeUndefined()
  expect(findButton(tree, 'Open Removal PR')).toBeUndefined()
})

it('closes the drawer and refreshes its parent when initial reconciliation deletes the workflow', async () => {
  vi.mocked(api.getRetirementWorkflow).mockResolvedValue({ workflow: { agv_revert_pr_url: 'https://example.com/pull/1' } } as Awaited<ReturnType<typeof api.getRetirementWorkflow>>)
  vi.mocked(api.checkAgvPrStatuses).mockResolvedValue({ status: 'ok', deleted: true, pr_statuses: {} })
  const onClose = vi.fn()
  const onChanged = vi.fn()
  WorkflowDrawer({ item: { catalog_base_name: 'example.item', display_name: 'Example', provisions: 0, unique_users: 0, experiences: 0, success_ratio: 0 }, onClose, onChanged })

  await act(async () => { hooks.effects[0]() })

  expect(hooks.setWorkflow).toHaveBeenLastCalledWith(null)
  expect(onClose).toHaveBeenCalledOnce()
  expect(onChanged).toHaveBeenCalledOnce()
})

function hasText(node: unknown, text: string): boolean {
  if (typeof node === 'string') return node.includes(text)
  if (!node || typeof node !== 'object') return false
  if (Array.isArray(node)) return node.some(child => hasText(child, text))
  return hasText((node as ReactElement<{ children?: unknown }>).props?.children, text)
}

it('renders without performance metrics when opened from Browse', () => {
  const tree = WorkflowDrawer({ item: { catalog_base_name: 'example.base', display_name: 'Example Base' }, onClose: vi.fn(), onChanged: vi.fn() })

  expect(hasText(tree, 'No performance data')).toBe(true)
  expect(hasText(tree, 'Provisions')).toBe(false)
  expect(findButton(tree, 'Recommend Retirement')).toBeDefined()
})
