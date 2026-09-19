import { apiBaseUrl } from './env'
import type {
  CorrectionEmailDraft,
  Decision,
  Document,
  DocumentCorrectionRequest,
  GlAccount,
} from './types'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, init)
  if (!response.ok) {
    let message = `Request failed (${response.status})`
    try {
      const body = (await response.json()) as { detail?: unknown }
      if (typeof body.detail === 'string' && body.detail) {
        message = body.detail
      }
    } catch {
      // Keep the HTTP fallback when the server did not return JSON.
    }
    throw new Error(message)
  }
  if (response.status === 204) {
    return undefined as T
  }
  return response.json() as Promise<T>
}

function json(method: 'PUT' | 'POST', body: unknown): RequestInit {
  return { method, headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) }
}

function documentPath(id: string, suffix = ''): string {
  return `/api/documents/${encodeURIComponent(id)}${suffix}`
}

export function uploadDocument(file: File): Promise<Document> {
  const body = new FormData()
  body.append('file', file)
  return request<Document>('/api/documents', { method: 'POST', body })
}

export function listDocuments(): Promise<Document[]> {
  return request<Document[]>('/api/documents')
}

export function getDocument(id: string): Promise<Document> {
  return request<Document>(documentPath(id))
}

export function deleteDocument(id: string): Promise<void> {
  return request<void>(documentPath(id), { method: 'DELETE' })
}

export function documentFileUrl(id: string): string {
  return `${apiBaseUrl}${documentPath(id, '/file')}`
}

export function correctDocument(id: string, body: DocumentCorrectionRequest): Promise<Document> {
  return request<Document>(documentPath(id), json('PUT', body))
}

export function selectGlAccount(id: string, glAccountCode: string): Promise<Document> {
  return request<Document>(
    documentPath(id, '/accounting'),
    json('PUT', { gl_account_code: glAccountCode }),
  )
}

export function decideDocument(id: string, decision: Decision): Promise<Document> {
  return request<Document>(documentPath(id, '/decision'), json('POST', { decision }))
}

export function draftCorrectionEmail(id: string): Promise<CorrectionEmailDraft> {
  return request<CorrectionEmailDraft>(documentPath(id, '/correction-email'), { method: 'POST' })
}

export function listGlAccounts(): Promise<GlAccount[]> {
  return request<GlAccount[]>('/api/accounting/gl-accounts')
}
