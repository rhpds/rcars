import { act } from 'react'
import { afterEach, expect, it, vi } from 'vitest'
import { WorkflowDrawer } from './WorkflowDrawer'
import { api } from '../../services/api'

const hooks = vi.hoisted(() => ({ effects: [] as Array<() => void>, setWorkflow: vi.fn(), index: 0 }))
vi.mock('react', async importOriginal => ({
  ...await importOriginal<typeof import('react')>(),
  useEffect: (effect: () => void) => { hooks.effects.push(effect) },
  useState: (value: unknown) => [value, hooks.index++ === 0 ? hooks.setWorkflow : vi.fn()],
}))
vi.mock('../../hooks/useAuth', () => ({ useAuth: () => ({ isAdmin: true }) }))
vi.mock('../../services/api', () => ({ api: { getRetirementWorkflow: vi.fn(), checkAgvPrStatuses: vi.fn() } }))

afterEach(() => { vi.clearAllMocks(); hooks.effects = []; hooks.index = 0 })

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
