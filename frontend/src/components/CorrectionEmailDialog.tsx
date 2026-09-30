import { useEffect, useRef, useState } from 'react'

import type { CorrectionEmailDraft } from '../lib/types'
import { Button } from './ui/Button'

interface CorrectionEmailDialogProps {
  draft: CorrectionEmailDraft | null
  loading: boolean
  error: string | null
  onClose: () => void
  onSend: (toEmail: string) => Promise<void>
}

export function CorrectionEmailDialog({
  draft,
  loading,
  error,
  onClose,
  onSend,
}: CorrectionEmailDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const [copied, setCopied] = useState(false)
  const [toEmail, setToEmail] = useState('')
  const [sending, setSending] = useState(false)
  const [sendError, setSendError] = useState<string | null>(null)

  useEffect(() => {
    dialogRef.current?.focus()
    function onKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose()
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose])

  async function copy() {
    if (!draft) return
    await navigator.clipboard.writeText(
      `To: ${draft.recipient_name}\nSubject: ${draft.subject}\n\n${draft.body}`,
    )
    setCopied(true)
  }

  async function send() {
    if (!draft || !toEmail) return
    setSending(true)
    setSendError(null)
    try {
      await onSend(toEmail)
    } catch (reason) {
      setSendError(reason instanceof Error ? reason.message : 'Could not send the email.')
      setSending(false)
    }
  }

  return (
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-zinc-900/40 p-4"
      onClick={onClose}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="correction-email-title"
        tabIndex={-1}
        className="w-full max-w-2xl rounded-xl border border-zinc-200 bg-white p-6 shadow-xl focus:outline-none"
        onClick={(event) => event.stopPropagation()}
      >
        <div className="flex items-start justify-between gap-4">
          <div>
            <h2 id="correction-email-title" className="text-lg font-semibold">
              Draft correction email
            </h2>
            <p className="mt-1 text-sm text-zinc-600">
              Generated from the blocking errors. Send it through Maya’s connected mailbox or
              copy it as a fallback.
            </p>
          </div>
          <Button variant="ghost" size="sm" onClick={onClose} aria-label="Close dialog">
            ✕
          </Button>
        </div>

        {loading && <p className="mt-6 text-sm text-zinc-500">Drafting…</p>}
        {error && (
          <p
            role="alert"
            className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800"
          >
            {error}
          </p>
        )}
        {draft && (
          <div className="mt-6 space-y-4 text-sm">
            <div className="grid items-center gap-2 sm:grid-cols-[80px_1fr]">
              <label htmlFor="correction-email-to" className="text-zinc-500">
                To
              </label>
              <input
                id="correction-email-to"
                type="email"
                required
                value={toEmail}
                disabled={sending}
                placeholder={`${draft.recipient_name} email address`}
                className="rounded-lg border border-zinc-300 px-3 py-2 disabled:bg-zinc-100"
                onChange={(event) => setToEmail(event.target.value)}
              />
              <span className="text-zinc-500">Subject</span>
              <span className="font-medium">{draft.subject}</span>
            </div>
            <pre className="whitespace-pre-wrap rounded-lg border border-zinc-200 bg-zinc-50 p-4 font-sans leading-6 text-zinc-800">
              {draft.body}
            </pre>
            <p className="text-xs text-zinc-500">Covers: {draft.issue_codes.join(', ')}</p>
            {sendError && (
              <p role="alert" className="rounded-lg border border-red-200 bg-red-50 p-3 text-red-800">
                {sendError}
              </p>
            )}
          </div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" disabled={sending} onClick={onClose}>
            Close
          </Button>
          <Button variant="outline" disabled={!draft || sending} onClick={() => void copy()}>
            {copied ? 'Copied' : 'Copy'}
          </Button>
          <Button
            disabled={!draft || !toEmail || sending}
            onClick={() => void send()}
          >
            {sending ? 'Sending…' : 'Send and await reply'}
          </Button>
        </div>
      </div>
    </div>
  )
}
