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

function findButton(node: unknown, label: string): ReactElement<{ onClick: () => void }> | undefined {
  if (!node || typeof node !== 'object') return
  if (Array.isArray(node)) return node.map(child => findButton(child, label)).find(Boolean)
  const element = node as ReactElement<{ children?: unknown; onClick: () => void }>
  if (element.type === 'button' && element.props.children === label) return element
  return findButton(element.props?.children, label)
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
