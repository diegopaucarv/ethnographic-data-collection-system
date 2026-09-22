import AsyncStorage from '@react-native-async-storage/async-storage'
import { Platform } from 'react-native'

const configuredApiUrl = process.env.EXPO_PUBLIC_API_URL?.trim().replace(/\/$/, '')
const API_BASE_URL = configuredApiUrl || (Platform.OS === 'android' ? 'http://10.0.2.2:8000' : 'http://localhost:8000')
const PENDING_SUBMISSIONS_KEY = 'ayni.sync.pending.v1'
const AUTH_TOKEN_KEY = 'ayni.auth.token'
const AUTH_USER_KEY = 'ayni.auth.user'
const MAX_RETRIES = 5
const RETRY_BASE_MS = 5_000
let flushInFlight: Promise<{ synced: number; pending: number; errors: string[] }> | null = null

export type LocalSubmissionState = 'draft' | 'queued' | 'syncing' | 'synced' | 'failed'

export type SubmissionEnvelope = {
  clientId: string
  formType: string
  data: Record<string, unknown>
  createdAt: string
  updatedAt: string
}

export type PendingSubmission = SubmissionEnvelope & {
  state: Exclude<LocalSubmissionState, 'synced'>
  token?: string
  serverId?: string
  retries: number
  nextAttemptAt: number
  lastError?: string
}

export type AuthResponse = {
  user: { id: string; email: string; name: string; role: string }
  token: string
}

export async function login(email: string, password: string) {
  return request<AuthResponse>('/api/auth/login', { method: 'POST', body: JSON.stringify({ email, password }) })
}

export async function getCurrentUser(token: string) {
  return request<AuthResponse['user']>('/api/auth/me', {}, token)
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

export function createSubmission(token: string, formType: string, data: Record<string, unknown>, clientId?: string) {
  return request<ApiSubmission>('/api/forms', { method: 'POST', body: JSON.stringify({ form_type: formType, data, status: 'draft', client_id: clientId }) }, token)
}

export function updateSubmission(token: string, id: string, data: Record<string, unknown>) {
  return request<ApiSubmission>(`/api/forms/${encodeURIComponent(id)}`, { method: 'PUT', body: JSON.stringify({ data }) }, token)
}

export function listSubmissions(token: string) {
  return request<{ submissions: ApiSubmission[] }>('/api/forms', {}, token)
}

export type SubmissionStatistics = {
  user_count: number | null
  total_submissions: number
  submitted_count: number
  draft_count: number
  by_form_type: Array<{ form_type: string; count: number; status: string }>
}

export function getStatistics(token: string) {
  return request<SubmissionStatistics>('/api/statistics', {}, token)
}

export function submitSubmission(token: string, id: string) {
  return request<ApiSubmission>(`/api/forms/${encodeURIComponent(id)}/submit`, { method: 'POST' }, token)
}

export async function readPendingSubmissions(): Promise<PendingSubmission[]> {
  try {
    const value = await AsyncStorage.getItem(PENDING_SUBMISSIONS_KEY)
    if (!value) return []
    const items = JSON.parse(value) as Partial<PendingSubmission>[]
    return items.filter((item) => item.clientId && item.formType && item.data).map((item) => ({
      clientId: item.clientId as string,
      formType: item.formType as string,
      data: item.data as Record<string, unknown>,
      createdAt: item.createdAt ?? new Date().toISOString(),
      updatedAt: item.updatedAt ?? item.createdAt ?? new Date().toISOString(),
      state: item.state === 'failed' ? 'failed' : item.state === 'syncing' ? 'queued' : item.state === 'draft' ? 'draft' : 'queued',
      token: item.token,
      serverId: item.serverId,
      retries: item.retries ?? 0,
      nextAttemptAt: item.nextAttemptAt ?? Date.now(),
      lastError: item.lastError,
    }))
  } catch {
    return []
  }
}

async function writePendingSubmissions(items: PendingSubmission[]) {
  await AsyncStorage.setItem(PENDING_SUBMISSIONS_KEY, JSON.stringify(items))
}

export type AuthSession = AuthResponse

export async function getStoredAuthToken() {
  return AsyncStorage.getItem(AUTH_TOKEN_KEY)
}

export async function getStoredAuthSession(): Promise<AuthSession | null> {
  const [token, user] = await Promise.all([AsyncStorage.getItem(AUTH_TOKEN_KEY), AsyncStorage.getItem(AUTH_USER_KEY)])
  if (!token || !user) return null
  try { return { token, user: JSON.parse(user) as AuthResponse['user'] } } catch { return null }
}

export async function storeAuthSession(session: AuthSession) {
  await Promise.all([
    AsyncStorage.setItem(AUTH_TOKEN_KEY, session.token),
    AsyncStorage.setItem(AUTH_USER_KEY, JSON.stringify(session.user)),
  ])
}

export async function clearStoredAuthToken() {
  await Promise.all([AsyncStorage.removeItem(AUTH_TOKEN_KEY), AsyncStorage.removeItem(AUTH_USER_KEY)])
}

export async function enqueueSubmission(formType: string, data: Record<string, unknown>, token?: string) {
  const items = await readPendingSubmissions()
  const now = new Date().toISOString()
  const envelope: SubmissionEnvelope = {
    clientId: `${Date.now()}-${Math.random().toString(36).slice(2)}-${Math.random().toString(36).slice(2)}`,
    formType,
    data,
    createdAt: now,
    updatedAt: now,
  }
  const item: PendingSubmission = {
    ...envelope,
    state: 'queued',
    token,
    retries: 0,
    nextAttemptAt: Date.now(),
  }
  await writePendingSubmissions([...items, item])
  return item
}

export async function flushPendingSubmissions(now = Date.now()) {
  if (flushInFlight) return flushInFlight
  flushInFlight = flushPendingSubmissionsInternal(now).finally(() => {
    flushInFlight = null
  })
  return flushInFlight
}

async function flushPendingSubmissionsInternal(now: number) {
  const pending = await readPendingSubmissions()
  const remaining: PendingSubmission[] = []
  let synced = 0
  const errors: string[] = []
  for (const item of pending) {
    if (item.nextAttemptAt > now || !item.token) {
      remaining.push(item)
      continue
    }
    const syncing: PendingSubmission = { ...item, state: 'syncing', updatedAt: new Date(now).toISOString() }
    try {
      const serverSubmission = await createSubmission(item.token, item.formType, item.data, item.clientId)
      synced += 1
      void serverSubmission
    } catch (error) {
      const retries = item.retries + 1
      const isUnauthorized = error instanceof ApiRequestError && error.status === 401
      const delay = isUnauthorized
        ? 60 * 60_000
        : Math.min(15 * 60_000, 2 ** Math.min(retries, 8) * RETRY_BASE_MS)
      const message = error instanceof Error ? error.message : 'Error de sincronización'
      errors.push(message)
      console.error('[ayni] submission sync failed', { clientId: item.clientId, message })
      remaining.push({
        ...syncing,
        state: 'failed',
        retries,
        lastError: message,
        updatedAt: new Date(now).toISOString(),
        nextAttemptAt: now + (retries >= MAX_RETRIES ? 60 * 60_000 : delay),
      })
    }
  }
  await writePendingSubmissions(remaining)
  return { synced, pending: remaining.length, errors }
}

export { API_BASE_URL }
