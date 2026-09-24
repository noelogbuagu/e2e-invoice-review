import type { Document } from '../lib/types'
import { StatusBadge } from './StatusBadge'
import { Button } from './ui/Button'
import { Card } from './ui/Card'

interface DocumentInboxProps {
  documents: Document[]
  deletingId: string | null
  onOpen: (document: Document) => void
  onDelete: (document: Document) => void
  onNew: () => void
}

function partyOf(document: Document): string {
  const invoice = document.extraction?.invoice
  const receipt = document.extraction?.receipt
  return invoice?.vendor_name ?? receipt?.merchant_name ?? document.original_filename
}

function amountOf(document: Document): string {
  const invoice = document.extraction?.invoice
  const receipt = document.extraction?.receipt
  const total = invoice?.invoice_total ?? receipt?.total
  const currency = invoice?.currency ?? receipt?.currency
  return total ? [currency, total].filter(Boolean).join(' ') : '—'
}

export function DocumentInbox({
  documents,
  deletingId,
  onOpen,
  onDelete,
  onNew,
}: DocumentInboxProps) {
  if (documents.length === 0) {
    return (
      <Card className="mt-6 p-12 text-center">
        <p className="text-sm text-zinc-600">No documents reviewed yet.</p>
        <Button onClick={onNew} className="mt-5">
          Review a document
        </Button>
      </Card>
    )
  }

  return (
    <Card className="mt-6 divide-y divide-zinc-100">
      {documents.map((document) => (
        <div key={document.id} className="flex items-center gap-2 px-3 py-2">
          <button
            type="button"
            onClick={() => onOpen(document)}
            className="min-w-0 flex-1 rounded-lg px-2 py-2.5 text-left transition hover:bg-zinc-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
          >
            <div className="flex items-baseline justify-between gap-3">
              <p className="truncate font-medium text-zinc-900">{partyOf(document)}</p>
              <span className="shrink-0 font-medium tabular-nums text-zinc-900">
                {amountOf(document)}
              </span>
            </div>
            <div className="mt-1.5 flex items-center justify-between gap-3">
              <p className="truncate text-sm text-zinc-500">
                <span className="mr-2 font-medium text-zinc-700">
                  {document.classification?.document_kind === 'receipt' ? 'Receipt' : 'Invoice'}
                </span>
                {document.original_filename}
                <span className="ml-2 text-zinc-400">
                  {new Date(document.created_at).toLocaleString()}
                </span>
              </p>
              <StatusBadge status={document.status} />
            </div>
          </button>
          <Button
            variant="ghost"
            size="sm"
            disabled={deletingId !== null}
            onClick={() => onDelete(document)}
            aria-label={`Delete ${document.original_filename}`}
          >
            {deletingId === document.id ? 'Deleting…' : 'Delete'}
          </Button>
        </div>
      ))}
    </Card>
  )
}
