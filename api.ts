const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000'

export type ApiSubmission = {
  id: string
  user_id: string
  form_type: string
  form_code: string
  data: Record<string, unknown>
  status: 'draft' | 'submitted' | 'synced'
  created_at: string
  updated_at: string
  submitted_at?: string | null
}

type ApiError = { detail?: string }

export class ApiRequestError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function request<T>(path: string, options: RequestInit = {}, token?: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${path}`, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options.headers,
    },
  })
  if (!response.ok) {
    let message = `Request failed with status ${response.status}`
    try { message = ((await response.json()) as ApiError).detail ?? message } catch {}
    throw new ApiRequestError(response.status, message)
  }
  return response.json() as Promise<T>
}

export function createSubmission(token: string, formType: string, data: Record<string, unknown>) {
  return request<ApiSubmission>('/api/forms', { method: 'POST', body: JSON.stringify({ form_type: formType, data, status: 'draft' }) }, token)
}

export function updateSubmission(token: string, id: string, data: Record<string, unknown>) {
  return request<ApiSubmission>(`/api/forms/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify({ data }) }, token)
}

export function listSubmissions(token: string) {
  return request<{ submissions: ApiSubmission[] }>('/api/forms', {}, token)
}

export function submitSubmission(token: string, id: string) {
  return request<ApiSubmission>(`/api/forms/${encodeURIComponent(id)}/submit`, { method: 'POST' }, token)
}

export { API_BASE_URL }
