import { useEffect, useRef, useState } from 'react'

import type { CorrectionEmailDraft } from '../lib/types'
import { Button } from './ui/Button'

interface CorrectionEmailDialogProps {
  draft: CorrectionEmailDraft | null
  loading: boolean
  error: string | null
  onClose: () => void
}

export function CorrectionEmailDialog({ draft, loading, error, onClose }: CorrectionEmailDialogProps) {
  const dialogRef = useRef<HTMLDivElement>(null)
  const [copied, setCopied] = useState(false)

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
              Generated from the blocking errors. Copy it into your mail client; this app does
              not send email.
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
            <div className="grid gap-1 sm:grid-cols-[80px_1fr]">
              <span className="text-zinc-500">To</span>
              <span className="font-medium">{draft.recipient_name}</span>
              <span className="text-zinc-500">Subject</span>
              <span className="font-medium">{draft.subject}</span>
            </div>
            <pre className="whitespace-pre-wrap rounded-lg border border-zinc-200 bg-zinc-50 p-4 font-sans leading-6 text-zinc-800">
              {draft.body}
            </pre>
            <p className="text-xs text-zinc-500">Covers: {draft.issue_codes.join(', ')}</p>
          </div>
        )}

        <div className="mt-6 flex justify-end gap-3">
          <Button variant="outline" onClick={onClose}>
            Close
          </Button>
          <Button disabled={!draft} onClick={() => void copy()}>
            {copied ? 'Copied' : 'Copy'}
          </Button>
        </div>
      </div>
    </div>
  )
}
