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
  getMe: () => request<{ email: string; roles: string[] }>('/auth/me'),

  // Advisor
  submitQuery: (query: string, stages: string[] = ['prod'], includeZt = true, optedOut = false) =>
    request<{ job_id: string }>('/advisor/query', {
      method: 'POST',
      body: JSON.stringify({ query, stages, include_zt: includeZt, opted_out: optedOut }),
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
    category?: string;
    include_retired?: boolean;
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
    if (params?.category) qs.set('category', params.category);
    if (params?.include_retired) qs.set('include_retired', 'true');
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
    workloads: Array<{ product_name: string; category: string; ci_count: number }>;
    configs: Array<{ agd_config: string; ci_count: number }>;
    cloud_providers: Array<{ cloud_provider: string; ci_count: number }>;
    os_images: Array<{ os_image: string; ci_count: number }>;
  }>('/catalog/facets'),
  getInfraStats: () => request<{
    v2_items: number; with_workloads: number;
    mapped_workloads: number; verified_workloads: number; unmapped_workloads: number;
  }>('/catalog/infra-stats'),
  getWorkloadMappings: () => request<{
    mappings: Array<{ workload_role: string; product_name: string; description: string | null; category: string | null; verified: boolean }>;
    aliases: Array<{ product_name: string; alias: string }>;
  }>('/catalog/workload-mappings'),
  addWorkloadMapping: (body: { workload_role: string; product_name: string; description?: string; category?: string }) =>
    request<{ status: string }>('/catalog/workload-mappings', {
      method: 'POST',
      body: JSON.stringify(body),
    }),
  deleteWorkloadMapping: (role: string) =>
    request<{ status: string }>(`/catalog/workload-mappings/${encodeURIComponent(role)}`, { method: 'DELETE' }),
  getUnmappedWorkloads: () => request<{
    unmapped: Array<{ workload_role: string; workload_collection: string | null; ci_count: number }>;
  }>('/catalog/workload-mappings/unmapped'),
  scanWorkloads: () => request<{ job_id: string }>('/admin/scan-workloads', { method: 'POST' }),

  // Content similarity / overlap
  getSimilarItems: (ciName: string, minScore = 0.75) =>
    request<{
      ci_name: string
      similar: Array<{
        ci_name: string; display_name: string; category: string; stage: string
        summary: string | null; similarity_score: number; computed_at: string
      }>
      count: number
    }>(`/catalog/${encodeURIComponent(ciName)}/similar?min_score=${minScore}`),
  getOverlapReport: (minScore = 0.75) =>
    request<{
      pairs: Array<{
        ci_name_a: string; ci_name_b: string; similarity_score: number; computed_at: string
        display_name_a: string; category_a: string; stage_a: string; summary_a: string | null
        display_name_b: string; category_b: string; stage_b: string; summary_b: string | null
      }>
      total: number
      stats: { total_pairs: number; high_overlap: number; related: number; last_computed: string | null }
      thresholds: { related: number; high_overlap: number }
    }>(`/admin/overlap?min_score=${minScore}`),
  computeSimilarity: (threshold = 0.75, stage = 'prod') =>
    request<{ pairs_stored: number; threshold: number; stage: string }>(`/admin/compute-similarity?threshold=${threshold}&stage=${stage}`, { method: 'POST' }),

  // Retirement analysis
  getRetirementDashboard: (params?: {
    sort_by?: string; sort_dir?: string; min_score?: number;
    category?: string; has_prod?: boolean; search?: string;
    window?: string;
  }) => {
    const qs = new URLSearchParams()
    if (params) {
      Object.entries(params).forEach(([k, v]) => {
        if (v !== undefined && v !== null && v !== '') qs.set(k, String(v))
      })
    }
    const query = qs.toString()
    return request<RetirementDashboardResponse>(`/analysis/retirement${query ? '?' + query : ''}`)
  },

  syncReporting: () =>
    request<{ job_id: string }>('/admin/sync-reporting', { method: 'POST' }),
};

export interface ReportingMetricsItem {
  catalog_base_name: string
  display_name: string
  provisions: number
  provisions_quarter: number
  requests: number
  experiences: number
  unique_users: number
  success_ratio: number
  failure_ratio: number
  touched_amount: number
  closed_amount: number
  total_cost: number
  avg_cost_per_provision: number
  first_provision: string | null
  last_provision: string | null
  retirement_score: number
  synced_at: string
  category: string | null
  product: string | null
  product_family: string | null
  sales_impact: string | null
  stages: Array<{ stage: string; ci_name: string; catalog_url: string }>
  has_content: boolean
  catalog_url?: string
}

export interface RetirementDashboardResponse {
  items: ReportingMetricsItem[]
  total: number
  synced_at: string | null
  summary: { total: number; with_provisions: number; with_cost: number; with_sales: number; last_synced: string | null } | null
}
