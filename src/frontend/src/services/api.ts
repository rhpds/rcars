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
  submitQuery: (query: string, prodOnly = true, optedOut = false) =>
    request<{ job_id: string }>('/advisor/query', {
      method: 'POST',
      body: JSON.stringify({ query, prod_only: prodOnly, opted_out: optedOut }),
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
  listCatalog: (params?: { stage?: string; category?: string; limit?: number; offset?: number }) => {
    const qs = new URLSearchParams();
    if (params?.stage) qs.set('stage', params.stage);
    if (params?.category) qs.set('category', params.category);
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

  // Analysis
  startScan: () => request<{ job_id: string; enqueued: number }>('/analysis/scan', { method: 'POST' }),
  checkStale: () => request<{ job_id: string }>('/analysis/check-stale', { method: 'POST' }),
  rescanStale: () => request<{ job_id: string; enqueued: number }>('/analysis/rescan-stale', { method: 'POST' }),
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
  getTokenUsage: (days = 30) => request<unknown>(`/admin/token-usage?days=${days}`),
  listJobs: (limit = 50) => request<{ items: unknown[]; total: number }>(`/admin/jobs?limit=${limit}`),
  getWorkerHealth: () => request<unknown>('/admin/workers'),
  getScanProgress: () => request<{
    queued: number; running: number; complete: number; failed: number;
    total: number; total_propagated: number; recent_complete: string[]; recent_failures: string[];
  }>('/admin/scan-progress'),
  getJobStatus: (jobId: string) =>
    request<{ status: string; result: unknown; error: string | null }>(`/advisor/query/${jobId}/result`),
  getQueryHistory: (limit = 50) => request<{ items: unknown[]; total: number }>(`/admin/queries?limit=${limit}`),
};
