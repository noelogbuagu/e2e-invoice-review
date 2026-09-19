import { useCallback, useState } from 'react'

import {
  correctDocument,
  decideDocument,
  documentFileUrl,
  draftCorrectionEmail,
  selectGlAccount,
} from '../lib/document-api'
import { correctionFrom, draftFrom } from '../lib/review-fields'
import { summarizeReview, supplierFixableIssues } from '../lib/review-outcome'
import type { CorrectionEmailDraft, Decision, Document, GlAccount } from '../lib/types'
import { CorrectionEmailDialog } from './CorrectionEmailDialog'
import { CrossCheckSection } from './CrossCheckSection'
import { DocumentPreview } from './DocumentPreview'
import { ExtractionSection } from './ExtractionSection'
import { StatusBadge } from './StatusBadge'
import { Button } from './ui/Button'
import { Card } from './ui/Card'

interface DocumentReviewProps {
  document: Document
  accounts: GlAccount[]
  onChanged: (document: Document) => void
}

type Busy = 'save' | 'account' | Decision | null

const outcomeClasses = {
  passed: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  attention: 'border-amber-200 bg-amber-50 text-amber-900',
  blocked: 'border-red-200 bg-red-50 text-red-900',
  decided: 'border-zinc-200 bg-zinc-50 text-zinc-800',
  failed: 'border-red-200 bg-red-50 text-red-900',
}

export function DocumentReview({ document, accounts, onChanged }: DocumentReviewProps) {
  const extraction = document.extraction
  const [draft, setDraft] = useState<Record<string, string>>(() =>
    extraction ? draftFrom(extraction) : {},
  )
  const [dirty, setDirty] = useState(false)
  const [busy, setBusy] = useState<Busy>(null)
  const [error, setError] = useState<string | null>(null)
  const [email, setEmail] = useState<{
    open: boolean
    draft: CorrectionEmailDraft | null
    error: string | null
  }>({ open: false, draft: null, error: null })

  const issues = document.validation?.issues ?? []
  const errors = issues.filter((issue) => issue.severity === 'error')
  const fixable = supplierFixableIssues(issues)
  const locked = document.status === 'approved' || document.status === 'rejected'
  const reviewable = document.status === 'ready' || document.status === 'needs_review'
  const outcome = summarizeReview(document.status, issues)
  const selectedAccount = accounts.find((a) => a.code === document.selected_gl_account_code)

  const kind = document.classification?.document_kind
  const invoice = extraction?.invoice
  const receipt = extraction?.receipt
  const party = invoice?.vendor_name ?? receipt?.merchant_name
  const total = invoice?.invoice_total ?? receipt?.total
  const currency = invoice?.currency ?? receipt?.currency

  const approveBlockedReason = dirty
    ? 'Save your changes before approving.'
    : errors.length > 0
      ? `${errors.length} blocking error${errors.length === 1 ? '' : 's'} must be fixed first.`
      : !selectedAccount
        ? 'Select a GL account before approving.'
        : null

  async function run(next: Busy, action: () => Promise<Document>) {
    setBusy(next)
    setError(null)
    try {
      onChanged(await action())
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'The request failed.')
    } finally {
      setBusy(null)
    }
  }

  async function save() {
    if (!extraction) return
    await run('save', async () => {
      const changed = await correctDocument(document.id, correctionFrom(extraction, draft))
      if (changed.extraction) setDraft(draftFrom(changed.extraction))
      setDirty(false)
      return changed
    })
  }

  function reset() {
    if (extraction) setDraft(draftFrom(extraction))
    setDirty(false)
  }

  function openEmail() {
    setEmail({ open: true, draft: null, error: null })
    draftCorrectionEmail(document.id)
      .then((draft) => setEmail({ open: true, draft, error: null }))
      .catch((reason: unknown) =>
        setEmail({
          open: true,
          draft: null,
          error: reason instanceof Error ? reason.message : 'Could not draft the email.',
        }),
      )
  }

  const closeEmail = useCallback(() => setEmail({ open: false, draft: null, error: null }), [])

  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <div className="mb-6">
        <p className="text-sm text-zinc-500">Step 3 of 3</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Review the document</h1>
        <p className="mt-1 text-sm text-zinc-600">
          Document Intelligence is the primary reading. The independent LLM check follows it.
          Correct fields, confirm the GL account, then approve or reject.
        </p>
      </div>

      <Card className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div className="min-w-0">
            <p className="text-sm text-zinc-500">
              {kind === 'receipt' ? 'Receipt' : kind === 'invoice' ? 'Invoice' : 'Document'}
            </p>
            <h2 className="mt-1 truncate text-lg font-semibold">{document.original_filename}</h2>
            <p className="mt-1 text-sm text-zinc-600">
              {[party, [currency, total].filter(Boolean).join(' ')].filter(Boolean).join(' · ')}
            </p>
          </div>
          <StatusBadge status={document.status} />
        </div>
        <div className={`mt-4 rounded-lg border p-4 text-sm ${outcomeClasses[outcome.kind]}`}>
          <p className="font-medium">{outcome.title}</p>
          <p className="mt-1 opacity-90">{outcome.description}</p>
        </div>
        {document.error_message && (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {document.error_message}
          </p>
        )}
        <details className="mt-4">
          <summary className="cursor-pointer text-sm font-medium text-zinc-700">
            Show source document
          </summary>
          <div className="mt-3">
            <DocumentPreview
              src={documentFileUrl(document.id)}
              filename={document.original_filename}
              contentType={document.content_type}
            />
          </div>
        </details>
      </Card>

      {extraction && (
        <ExtractionSection
          extraction={extraction}
          draft={draft}
          disabled={!reviewable || busy !== null}
          dirty={dirty}
          saving={busy === 'save'}
          onChange={(key, value) => {
            setDraft((current) => ({ ...current, [key]: value }))
            setDirty(true)
          }}
          onSave={() => void save()}
          onReset={reset}
          onDraftEmail={reviewable && fixable.length > 0 ? openEmail : null}
        />
      )}

      {email.open && (
        <CorrectionEmailDialog
          draft={email.draft}
          loading={email.draft === null && email.error === null}
          error={email.error}
          onClose={closeEmail}
        />
      )}

      {document.document_review && <CrossCheckSection review={document.document_review} />}

      <Card className="mt-6 p-6">
        <h2 className="text-sm font-medium">Validation findings</h2>
        {issues.length === 0 ? (
          <p className="mt-4 rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-800">
            No validation findings.
          </p>
        ) : (
          <ul className="mt-4 space-y-3">
            {issues.map((issue) => (
              <li
                key={`${issue.code}-${issue.message}`}
                className={`rounded-lg border p-4 text-sm ${
                  issue.severity === 'error'
                    ? 'border-red-200 bg-red-50 text-red-800'
                    : 'border-amber-200 bg-amber-50 text-amber-800'
                }`}
              >
                <p className="font-medium">
                  {issue.severity === 'error' ? 'Error' : 'Warning'} · {issue.message}
                </p>
                <p className="mt-1 text-xs opacity-75">{issue.code}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>

      <Card className="mt-6 p-6">
        <h2 className="text-sm font-medium">GL account</h2>
        {document.gl_suggestion ? (
          <p className="mt-2 text-sm text-zinc-600">
            Suggested {document.gl_suggestion.account_code} {document.gl_suggestion.account_name}{' '}
            (confidence {document.gl_suggestion.confidence.toFixed(2)}).{' '}
            {document.gl_suggestion.reasoning}
          </p>
        ) : (
          <p className="mt-2 text-sm text-zinc-600">No suggestion was produced.</p>
        )}
        <label className="mt-4 block text-sm">
          <span className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            Selected account
          </span>
          <select
            className="mt-1 block w-full rounded-lg border border-zinc-300 bg-white px-3 py-2 text-sm disabled:bg-zinc-100"
            value={document.selected_gl_account_code ?? ''}
            disabled={!reviewable || busy !== null || accounts.length === 0}
            onChange={(event) =>
              void run('account', () => selectGlAccount(document.id, event.target.value))
            }
          >
            <option value="" disabled>
              {accounts.length === 0 ? 'Loading catalog…' : 'Choose an account'}
            </option>
            {accounts.map((account) => (
              <option key={account.code} value={account.code}>
                {account.code} · {account.name}
              </option>
            ))}
          </select>
        </label>
        {selectedAccount && (
          <p className="mt-2 text-xs text-zinc-500">{selectedAccount.description}</p>
        )}
      </Card>

      {error && (
        <p
          role="alert"
          className="mt-6 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800"
        >
          {error}
        </p>
      )}

      {!locked && (
        <Card className="mt-6 p-6">
          <div className="flex flex-wrap items-center justify-between gap-4">
            <div>
              <h2 className="text-sm font-medium">Decision</h2>
              <p className="mt-1 text-sm text-zinc-600">
                {approveBlockedReason ?? 'Everything needed for approval is in place.'}
              </p>
            </div>
            <div className="flex gap-3">
              <Button
                variant="outline"
                disabled={!reviewable || busy !== null}
                onClick={() => void run('rejected', () => decideDocument(document.id, 'rejected'))}
              >
                {busy === 'rejected' ? 'Rejecting…' : 'Reject'}
              </Button>
              <Button
                disabled={!reviewable || busy !== null || approveBlockedReason !== null}
                onClick={() => void run('approved', () => decideDocument(document.id, 'approved'))}
              >
                {busy === 'approved' ? 'Approving…' : 'Approve'}
              </Button>
            </div>
          </div>
        </Card>
      )}
    </main>
  )
}
