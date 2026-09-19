import type { Document, DocumentStatus } from '../lib/types'
import { Card } from './ui/Card'

const statusLabels: Record<DocumentStatus, string> = {
  processing: 'Processing',
  ready: 'Ready',
  needs_review: 'Needs review',
  failed: 'Failed',
}

const statusClasses: Record<DocumentStatus, string> = {
  processing: 'border-blue-200 bg-blue-50 text-blue-700',
  ready: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  needs_review: 'border-amber-200 bg-amber-50 text-amber-800',
  failed: 'border-red-200 bg-red-50 text-red-700',
}

export function DocumentResult({ document }: { document: Document }) {
  const invoice = document.extraction?.invoice
  const receipt = document.extraction?.receipt
  const kind = document.classification?.document_kind
  const party = invoice?.vendor_name ?? receipt?.merchant_name
  const date = invoice?.invoice_date ?? receipt?.transaction_date
  const total = invoice?.invoice_total ?? receipt?.total
  const currency = invoice?.currency ?? receipt?.currency
  const issues = document.validation?.issues ?? []

  return (
    <main className="mx-auto max-w-5xl px-6 py-8">
      <div className="mb-6">
        <p className="text-sm text-zinc-500">Step 3 of 3</p>
        <h1 className="mt-1 text-2xl font-semibold tracking-tight">Review the result</h1>
        <p className="mt-1 text-sm text-zinc-600">
          Inspect classification, extraction highlights, validation findings, and the GL
          suggestion. Editing and approval come in a later slice.
        </p>
      </div>

      <Card className="p-6">
        <div className="flex items-start justify-between gap-4">
          <div>
            <p className="text-sm text-zinc-500">Pipeline result</p>
            <h2 className="mt-1 text-lg font-semibold">{document.original_filename}</h2>
            <p className="mt-1 text-sm text-zinc-600">
              {[kind, party, formatMoney(currency, total)].filter(Boolean).join(' · ')}
            </p>
          </div>
          <span
            className={`shrink-0 rounded-md border px-2 py-1 text-xs font-medium ${statusClasses[document.status]}`}
          >
            {statusLabels[document.status]}
          </span>
        </div>
        {document.error_message && (
          <p className="mt-4 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800">
            {document.error_message}
          </p>
        )}
      </Card>

      <div className="mt-6 grid gap-6 md:grid-cols-2">
        <Card className="p-6">
          <h2 className="text-sm font-medium">Classification</h2>
          <dl className="mt-5 space-y-4">
            <ResultField label="Document kind" value={kind} />
            <ResultField
              label="Confidence"
              value={formatConfidence(document.classification?.confidence)}
            />
            <ResultField label="Reasoning" value={document.classification?.reasoning} />
          </dl>
        </Card>

        <Card className="p-6">
          <h2 className="text-sm font-medium">GL suggestion</h2>
          <dl className="mt-5 space-y-4">
            <ResultField label="Account code" value={document.gl_suggestion?.account_code} />
            <ResultField label="Account name" value={document.gl_suggestion?.account_name} />
            <ResultField
              label="Confidence"
              value={formatConfidence(document.gl_suggestion?.confidence)}
            />
            <ResultField label="Reasoning" value={document.gl_suggestion?.reasoning} />
          </dl>
        </Card>
      </div>

      <Card className="mt-6 p-6">
        <h2 className="text-sm font-medium">Extraction highlights</h2>
        <dl className="mt-5 grid gap-x-8 gap-y-5 sm:grid-cols-2">
          <ResultField label="Vendor / merchant" value={party} />
          <ResultField label="Invoice / receipt ID" value={invoice?.invoice_number} />
          <ResultField label="Date" value={date} />
          <ResultField label="Total" value={formatMoney(currency, total)} />
          <ResultField label="Vendor VAT" value={invoice?.vendor_vat_id} />
          <ResultField label="Customer VAT" value={invoice?.customer_vat_id} />
        </dl>
      </Card>

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
                <p className="font-medium">{issue.message}</p>
                <p className="mt-1 text-xs opacity-75">{issue.code}</p>
              </li>
            ))}
          </ul>
        )}
      </Card>
    </main>
  )
}

function ResultField({ label, value }: { label: string; value: string | null | undefined }) {
  return (
    <div>
      <dt className="text-xs font-medium uppercase tracking-wide text-zinc-500">{label}</dt>
      <dd className="mt-1 text-sm leading-6 text-zinc-800">{value || '—'}</dd>
    </div>
  )
}

function formatConfidence(value: number | null | undefined): string | null {
  return value === null || value === undefined ? null : value.toFixed(2)
}

function formatMoney(currency: string | null | undefined, amount: string | null | undefined) {
  if (!amount) return null
  return [currency, amount].filter(Boolean).join(' ')
}
