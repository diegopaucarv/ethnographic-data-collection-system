import AsyncStorage from '@react-native-async-storage/async-storage'

const API_BASE_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost:8000'
const PENDING_SUBMISSIONS_KEY = 'ayni.sync.pending.v1'
const MAX_RETRIES = 5

export type PendingSubmission = {
  clientId: string
  formType: string
  data: Record<string, unknown>
  token?: string
  retries: number
  nextAttemptAt: number
  createdAt: string
}

export type AuthResponse = {
  user: { id: string; email: string; name: string; role: string }
  token: string
}

export async function login(email: string, password: string) {
  return request<AuthResponse>(`/api/auth/login?email=${encodeURIComponent(email)}&password=${encodeURIComponent(password)}`, { method: 'POST' })
}

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

export async function readPendingSubmissions(): Promise<PendingSubmission[]> {
  try {
    const value = await AsyncStorage.getItem(PENDING_SUBMISSIONS_KEY)
    return value ? (JSON.parse(value) as PendingSubmission[]) : []
  } catch {
    return []
  }
}

async function writePendingSubmissions(items: PendingSubmission[]) {
  await AsyncStorage.setItem(PENDING_SUBMISSIONS_KEY, JSON.stringify(items))
}

export async function enqueueSubmission(formType: string, data: Record<string, unknown>, token?: string) {
  const items = await readPendingSubmissions()
  const item: PendingSubmission = {
    clientId: `${Date.now()}-${Math.random().toString(36).slice(2)}`,
    formType,
    data,
    token,
    retries: 0,
    nextAttemptAt: Date.now(),
    createdAt: new Date().toISOString(),
  }
  await writePendingSubmissions([...items, item])
  return item
}

export async function flushPendingSubmissions(now = Date.now()) {
  const pending = await readPendingSubmissions()
  const remaining: PendingSubmission[] = []
  let synced = 0
  for (const item of pending) {
    if (item.nextAttemptAt > now) { remaining.push(item); continue }
    if (!item.token) { remaining.push(item); continue }
    try {
      await createSubmission(item.token, item.formType, item.data)
      synced += 1
    } catch {
      const retries = item.retries + 1
      if (retries < MAX_RETRIES) {
        remaining.push({ ...item, retries, nextAttemptAt: now + Math.min(15 * 60_000, 2 ** retries * 5_000) })
      } else {
        remaining.push({ ...item, retries, nextAttemptAt: now + 60 * 60_000 })
      }
    }
  }
  await writePendingSubmissions(remaining)
  return { synced, pending: remaining.length }
}

export { API_BASE_URL }
