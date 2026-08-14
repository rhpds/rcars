const BASE = '/api/v1';

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const resp = await fetch(`${BASE}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...options?.headers,
    },
  });
  if (!resp.ok) {
    const error = await resp.json().catch(() => ({ error: resp.statusText }));
    throw new Error(error.detail || error.error || resp.statusText);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json();
}

export const api = {
  // Auth
  getMe: () => request<{ email: string; roles: string[]; performance_public: boolean }>('/auth/me'),

  // Advisor
  submitQuery: (query: string, stages: string[] = ['prod'], includeZt = true) =>
    request<{ job_id: string }>('/advisor/query', {
      method: 'POST',
      body: JSON.stringify({ query, stages, include_zt: includeZt }),
    }),
  submitChat: (message: string, sessionId?: string | null, stages: string[] = ['prod'],
               includeZt = true, routed?: Record<string, unknown>) =>
    request<{ job_id: string; session_id: string }>('/advisor/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId ?? null, stages,
                             include_zt: includeZt, routed: routed ?? null }),
    }),
  getQueryResult: (jobId: string) =>
    request<{ status: string; result: unknown; error: string | null }>(`/advisor/query/${jobId}/result`),
  listSessions: () => request<{ items: unknown[]; total: number }>('/advisor/sessions'),
  getSession: (sessionId: string) => request<{ session_id: string; turns: unknown[] }>(`/advisor/sessions/${sessionId}`),
  selectRecommendation: (sessionId: string, turnIndex: number, ciName: string) =>
    request<{ status: string }>(`/advisor/sessions/${sessionId}/select`, {
      method: 'POST',
      body: JSON.stringify({ turn_index: turnIndex, ci_name: ciName }),
    }),

  // Catalog
  listCatalog: (params?: {
    search?: string;
    stage?: string;
    cloud_provider?: string;
    workloads?: string;
    agd_config?: string;
    content_filter?: string;
    content_type?: string;
    category?: string;
    include_retired?: string | boolean;
    limit?: number;
    offset?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.search) qs.set('search', params.search);
    if (params?.stage) qs.set('stage', params.stage);
    if (params?.cloud_provider) qs.set('cloud_provider', params.cloud_provider);
    if (params?.workloads) qs.set('workloads', params.workloads);
    if (params?.agd_config) qs.set('agd_config', params.agd_config);
    if (params?.content_filter) qs.set('content_filter', params.content_filter);
    if (params?.content_type) qs.set('content_type', params.content_type);
    if (params?.category) qs.set('category', params.category);
    if (params?.include_retired) qs.set('include_retired', String(params.include_retired));
    if (params?.limit) qs.set('limit', String(params.limit));
    if (params?.offset) qs.set('offset', String(params.offset));
    return request<{ items: unknown[]; total: number }>(`/catalog?${qs}`);
  },
  getCatalogItem: (ciName: string) => request<unknown>(`/catalog/${encodeURIComponent(ciName)}`),
  getCatalogStats: () => request<unknown>('/catalog/stats'),
  refreshCatalog: () => request<{ job_id: string }>('/catalog/refresh', { method: 'POST' }),

  // Curation
  addTag: (ciName: string, tagType: string, tagValue: string) =>
    request<{ status: string }>(`/catalog/${encodeURIComponent(ciName)}/tags`, {
      method: 'POST',
      body: JSON.stringify({ tag_type: tagType, tag_value: tagValue }),
    }),
  removeTag: (ciName: string, tagId: number) =>
    request<{ status: string }>(`/catalog/${encodeURIComponent(ciName)}/tags/${tagId}`, { method: 'DELETE' }),
  setNote: (ciName: string, note: string) =>
    request<{ status: string }>(`/catalog/${encodeURIComponent(ciName)}/note`, {
      method: 'PUT',
      body: JSON.stringify({ note }),
    }),
  flagItem: (ciName: string) =>
    request<{ status: string }>(`/catalog/${encodeURIComponent(ciName)}/flag`, { method: 'POST' }),
  setContentPath: (ciName: string, path: string | null) =>
    request<{ status: string; content_path: string | null; job_id: string }>(`/catalog/${encodeURIComponent(ciName)}/content-path`, {
      method: 'POST',
      body: JSON.stringify({ path }),
    }),
  overrideUrl: (ciName: string, url: string) =>
    request<{ status: string }>(`/catalog/${encodeURIComponent(ciName)}/override-url`, {
      method: 'POST',
      body: JSON.stringify({ url }),
    }),
  setCuratedDuration: (ciName: string, durationMin: number | null) =>
    request<{ status: string }>(`/catalog/${encodeURIComponent(ciName)}/duration`, {
      method: 'PUT',
      body: JSON.stringify({ duration_min: durationMin }),
    }),

  // Analysis
  startScan: () => request<{ job_id: string; enqueued: number }>('/analysis/scan', { method: 'POST' }),
  checkStale: () => request<{ job_id: string }>('/analysis/check-stale', { method: 'POST' }),
  rescanAll: () => request<{ job_id: string; marked_stale: number; enqueued: number; total_scannable?: number; unique_pairs?: number }>('/analysis/rescan-all', { method: 'POST' }),
  analyzeSingle: (ciName: string) =>
    request<{ job_id: string }>(`/analysis/${encodeURIComponent(ciName)}`, { method: 'POST' }),

  // SSE streaming
  streamJob: (jobId: string, onMessage: (msg: { user_message: string; phase: string; status: string }) => void): () => void => {
    const es = new EventSource(`${BASE}/analysis/jobs/${jobId}/stream`)
    es.onmessage = (e) => {
      try { onMessage(JSON.parse(e.data)) } catch { /* ignore */ }
    }
    es.onerror = () => es.close()
    return () => es.close()
  },

  // Admin
  getJob: (jobId: string) => request<{ id: string; status: string; progress_json: Record<string, unknown> | null; result_json: Record<string, unknown> | null; error: string | null }>(`/admin/jobs/${jobId}`),
  getTokenUsage: (days = 30) => request<unknown>(`/admin/token-usage?days=${days}`),
  listJobs: (limit = 50) => request<{ items: unknown[]; total: number }>(`/admin/jobs?limit=${limit}`),
  getScanProgress: () => request<{
    queued: number; running: number; complete: number; failed: number;
    total: number; total_propagated: number; recent_complete: string[]; recent_failures: string[];
  }>('/admin/scan-progress'),
  getJobStatus: (jobId: string) =>
    request<{ status: string; result: unknown; error: string | null }>(`/advisor/query/${jobId}/result`),
  getQueryHistory: (limit = 50) => request<{ items: unknown[]; total: number }>(`/admin/queries?limit=${limit}`),
  getQuerySessionDetail: (sessionId: string) => request<{ session_id: string; turns: unknown[] }>(`/admin/queries/${sessionId}`),

  // Scheduled maintenance
  getScheduleStatus: () => request<{
    pipeline_enabled: boolean; pipeline_schedule: string;
    last_pipeline: { job_id: string; status: string; created_at: string; completed_at: string | null; result: Record<string, unknown> | null; error: string | null } | null;
  }>('/admin/schedule'),
  runMaintenance: () => request<{ job_id: string }>('/admin/run-maintenance', { method: 'POST' }),

  // LLM provider
  getLlmProviderStatus: () => request<{
    litemaas_enabled: boolean; litemaas_url: string | null; litemaas_models: string[];
    vertex_enabled: boolean; vertex_region: string | null; vertex_models: string[];
    analysis_model: string; triage_model: string; rationale_model: string; scanning_model: string;
  }>('/admin/llm-provider'),

  // Reporting status
  getReportingStatus: () => request<{
    configured: boolean; total: number; with_provisions: number; with_cost: number; with_sales: number; last_synced: string | null;
  }>('/admin/reporting-status'),

  // Infrastructure
  searchInfrastructure: (params?: { workloads?: string; agd_config?: string; cloud_provider?: string; ocp_version?: string; os_image?: string; stage?: string; limit?: number }) => {
    const qs = new URLSearchParams();
    if (params?.workloads) qs.set('workloads', params.workloads);
    if (params?.agd_config) qs.set('agd_config', params.agd_config);
    if (params?.cloud_provider) qs.set('cloud_provider', params.cloud_provider);
    if (params?.ocp_version) qs.set('ocp_version', params.ocp_version);
    if (params?.os_image) qs.set('os_image', params.os_image);
    if (params?.stage) qs.set('stage', params.stage);
    if (params?.limit) qs.set('limit', String(params.limit));
    return request<{ items: unknown[]; total: number }>(`/catalog/search/infrastructure?${qs}`);
  },
  getCatalogFacets: () => request<{
    workloads: string[];
    agd_configs: string[];
    cloud_providers: string[];
    os_images: string[];
  }>('/catalog/facets'),
  getInfraStats: () => request<{
    v2_items: number; with_workloads: number;
    mapped_workloads: number; verified_workloads: number; unmapped_workloads: number;
  }>('/catalog/infra-stats'),
  getInfrastructureCatalog: (params?: {
    type?: string; category?: string; collection?: string;
    search?: string; has_mappings?: boolean; limit?: number;
  }) => {
    const qs = new URLSearchParams();
    if (params?.type) qs.set('type', params.type);
    if (params?.category) qs.set('category', params.category);
    if (params?.collection) qs.set('collection', params.collection);
    if (params?.search) qs.set('search', params.search);
    if (params?.has_mappings !== undefined) qs.set('has_mappings', String(params.has_mappings));
    if (params?.limit) qs.set('limit', String(params.limit));
    return request<{
      items: Array<{
        role_name: string; fqcn: string | null; collection: string | null;
        type: string; description: string | null;
        products: string[]; capabilities: string[];
        category: string | null; requires: string[];
        source_sha: string | null; scanned_at: string | null;
        item_count: number;
      }>;
      total: number;
    }>(`/catalog/infrastructure?${qs}`);
  },
  scanWorkloads: () => request<{ job_id: string }>('/admin/scan-workloads', { method: 'POST' }),

  // Content overlap
  getOverlapReport: (params?: {
    verdict?: string; search?: string; stage?: string; page?: number; page_size?: number;
    min_shared_products?: number; min_shared_topics?: number;
  }) => {
    const p = new URLSearchParams()
    if (params?.verdict) p.set('verdict', params.verdict)
    if (params?.search) p.set('search', params.search)
    if (params?.stage) p.set('stage', params.stage)
    if (params?.page) p.set('page', String(params.page))
    if (params?.page_size) p.set('page_size', String(params.page_size))
    if (params?.min_shared_products != null) p.set('min_shared_products', String(params.min_shared_products))
    if (params?.min_shared_topics != null) p.set('min_shared_topics', String(params.min_shared_topics))
    const qs = p.toString()
    return request<{
      items: Array<{
        content_id: string; display_name: string; content_type: string; source: string
        ci_name: string | null; category: string | null; stage: string | null
        neighbor_count: number
        neighbors: Array<{
          content_id: string; display_name: string; content_type: string
          source: string; ci_name: string | null; category: string | null
          stage: string | null; shared_products: number; shared_topics: number
          verdict: string | null; recommendation: string | null; assessed_at: string | null
        }>
      }>
      total_items: number; page: number; page_size: number
      stats: {
        redundant: number; complementary: number; differentiated: number
        unassessed: number; total_pairs: number; last_computed: string | null
      }
    }>(`/analysis/overlap${qs ? `?${qs}` : ''}`)
  },

  getOverlapAssessment: (contentIdA: string, contentIdB: string) =>
    request<{
      assessment: {
        verdict: string; shared_topics: string[]; differentiators_a: string[]
        differentiators_b: string[]; recommendation: string; rationale: string
        model: string; tokens: { input: number; output: number }
      } | null
      assessed_at: string | null
      reason?: string
    }>(`/analysis/overlap/${encodeURIComponent(contentIdA)}/${encodeURIComponent(contentIdB)}`),

  // Performance analysis
  getPerformanceDashboard: (params?: {
    sort_by?: string; sort_dir?: string; min_score?: number;
    search?: string; window?: string; channel?: string; workflow_status?: string;
  }) => {
    const qs = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qs.set(k, String(v))
      })
    }
    const query = qs.toString()
    return request<PerformanceDashboardResponse>(`/analysis/performance${query ? '?' + query : ''}`)
  },

  // Retirement workflows
  getRetirementWorkflow: (baseName: string) =>
    request<{ workflow: RetirementWorkflow | null }>(`/analysis/performance/workflow/${encodeURIComponent(baseName)}`),

  reviewRetirementItem: (baseName: string) =>
    request<{ status: string; workflow: RetirementWorkflow }>(`/analysis/performance/workflow/${encodeURIComponent(baseName)}/review`, { method: 'PUT' }),

  approveRetirementItem: (baseName: string, reason: string, replacementCi?: string, replacementName?: string) =>
    request<{ status: string; workflow: RetirementWorkflow }>(`/analysis/performance/workflow/${encodeURIComponent(baseName)}/approve`, {
      method: 'PUT',
      body: JSON.stringify({ reason, replacement_ci: replacementCi || null, replacement_name: replacementName || null }),
    }),

  notifyRetirementOwner: (baseName: string) =>
    request<{ status: string; workflow: RetirementWorkflow }>(`/analysis/performance/workflow/${encodeURIComponent(baseName)}/notify`, { method: 'PUT' }),

  startRetirement: (baseName: string, targetDays?: number, jiraProject?: string) =>
    request<{ status: string; workflow: RetirementWorkflow; jira_key: string }>(`/analysis/performance/workflow/${encodeURIComponent(baseName)}/start`, {
      method: 'PUT',
      body: JSON.stringify({ target_days: targetDays ?? 30, jira_project: jiraProject ?? 'RHDPCD' }),
    }),

  updateRetirementNotes: (baseName: string, notes: string) =>
    request<{ status: string; workflow: RetirementWorkflow }>(`/analysis/performance/workflow/${encodeURIComponent(baseName)}/notes`, {
      method: 'PUT',
      body: JSON.stringify({ notes }),
    }),

  linkRetirementJira: (baseName: string, jiraKey: string) =>
    request<{ status: string; workflow: RetirementWorkflow }>(`/analysis/performance/workflow/${encodeURIComponent(baseName)}/link-jira`, {
      method: 'PUT',
      body: JSON.stringify({ jira_key: jiraKey }),
    }),

  cancelRetirementWorkflow: (baseName: string) =>
    request<{ status: string; deleted: boolean }>(`/analysis/performance/workflow/${encodeURIComponent(baseName)}`, { method: 'DELETE' }),

  ignoreItem: (baseName: string) =>
    request<{ status: string; ignored_until: string }>(`/analysis/performance/ignore/${encodeURIComponent(baseName)}`, { method: 'PUT' }),

  unignoreItem: (baseName: string) =>
    request<{ status: string }>(`/analysis/performance/ignore/${encodeURIComponent(baseName)}`, { method: 'DELETE' }),

  // Non-prod items
  getNonprodItems: (params?: {
    sort_by?: string; sort_dir?: string; content_type?: string;
    stage?: string; search?: string;
    window?: string; status?: string;
  }) => {
    const qs = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qs.set(k, String(v))
      })
    }
    const query = qs.toString()
    return request<NonProdDashboardResponse>(`/analysis/nonprod${query ? '?' + query : ''}`)
  },

  ignoreNonprodItem: (baseName: string) =>
    request<{ status: string; ignored_until: string }>(`/analysis/nonprod/ignore/${encodeURIComponent(baseName)}`, { method: 'PUT' }),

  unignoreNonprodItem: (baseName: string) =>
    request<{ status: string }>(`/analysis/nonprod/ignore/${encodeURIComponent(baseName)}`, { method: 'DELETE' }),

  syncReporting: () =>
    request<{ job_id: string }>('/admin/sync-reporting', { method: 'POST' }),

  // API Keys
  listApiKeys: (active = true) =>
    request<{ keys: Array<{ id: number; key_prefix: string; name: string; created_by: string; role: string; created_at: string; expires_at: string | null; last_used_at: string | null; is_active: boolean }> }>(
      `/auth/keys?active=${active}`
    ),
  createApiKey: (name: string, role: string, expiresInDays: number | null) =>
    request<{ api_key: string; id: number; name: string; role: string; expires_at: string | null }>(
      '/auth/keys',
      { method: 'POST', body: JSON.stringify({ name, role, expires_in_days: expiresInDays }) }
    ),
  revokeApiKey: (keyId: number) =>
    request<{ id: number; revoked_at: string }>(`/auth/keys/${keyId}`, { method: 'DELETE' }),

  getRoleAssignments: () => request<{ assignments: RoleAssignment[] }>('/admin/role-assignments'),
  addRoleAssignment: (type: string, value: string, role: string) =>
    request<RoleAssignment>('/admin/role-assignments', {
      method: 'POST',
      body: JSON.stringify({ type, value, role }),
    }),
  deleteRoleAssignment: (id: number) =>
    request<void>(`/admin/role-assignments/${id}`, { method: 'DELETE' }),
};

export interface RetirementWorkflow {
  catalog_base_name: string
  content_id: string
  status: string
  step_reviewed_at: string | null
  step_reviewed_by: string | null
  step_approved_at: string | null
  step_approved_by: string | null
  approval_reason: string | null
  approval_snapshot: Record<string, number | string> | null
  step_notified_at: string | null
  step_notified_by: string | null
  step_started_at: string | null
  step_started_by: string | null
  retirement_target_date: string | null
  step_retired_at: string | null
  replacement_ci: string | null
  replacement_name: string | null
  curator_notes: string | null
  jira_key: string | null
  jira_project: string
  created_at: string
  updated_at: string
}

export interface ScoreBreakdownFactor {
  factor: string
  points: number
  max: number
  level: string
  reason: string
}

export interface ScoreBreakdown {
  score: number
  factors: ScoreBreakdownFactor[]
  summary: string
}

export interface MarketingMetrics {
  provisions: number
  unique_users: number
  experiences: number
  page_views: number
  score: number | null
}

export interface SalesMetrics {
  provisions: number
  unique_users: number
  experiences: number
  page_views: number
  pipeline_touched: number
  closed_amount: number
  total_cost: number
  score: number | null
}

export interface PerformanceItem {
  content_id: string
  catalog_base_name: string
  display_name: string
  ci_name?: string | null
  category: string | null
  performance_score: number
  score_breakdown?: ScoreBreakdown | null
  channel_scores?: Record<string, { score?: number }> | null
  channels_present: string[]
  marketing?: MarketingMetrics | null
  sales?: SalesMetrics | null
  provisions: number
  experiences: number
  requests: number
  unique_users: number
  success_ratio: number
  failure_ratio: number
  pipeline_touched: number
  closed_amount: number
  total_cost: number
  avg_cost_per_provision: number
  first_activity: string | null
  last_activity: string | null
  sales_impact: string | null
  stages: Array<{ stage: string; ci_name: string; catalog_url: string }>
  owners: Array<{ name: string; email: string }>
  has_content: boolean
  catalog_url?: string
  workflow_status?: string | null
  jira_key?: string | null
  retirement_target_date?: string | null
  ignored_until?: string | null
}

export interface PerformanceDashboardResponse {
  items: PerformanceItem[]
  total: number
  synced_at: string | null
  summary: { total: number; last_synced: string | null } | null
  window: string
  channel: string
}

export interface NonProdItem {
  content_id: string
  catalog_base_name: string
  display_name: string
  content_type: string | null
  stage: string | null
  catalog_namespace: string | null
  ci_name: string | null
  provisions: number
  requests: number
  experiences: number
  unique_users: number
  success_ratio: number
  failure_ratio: number
  first_provision: string | null
  last_provision: string | null
  stages: Array<{ stage: string; ci_name: string; catalog_url: string; has_showroom: boolean }>
  workflow_status?: string | null
  jira_key?: string | null
  retirement_target_date?: string | null
  ignored_until?: string | null
}

export interface NonProdDashboardResponse {
  items: NonProdItem[]
  total: number
  synced_at: string | null
  window: string
}

export interface RoleAssignment {
  id: number | null
  type: string
  value: string
  role: string
  source: string
  added_by: string | null
  added_at: string | null
}
