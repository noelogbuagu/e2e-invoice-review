import type { DocumentStatus } from '../lib/types'

const labels: Record<DocumentStatus, string> = {
  processing: 'Processing',
  ready: 'Ready',
  needs_review: 'Needs review',
  approved: 'Approved',
  rejected: 'Rejected',
  failed: 'Failed',
}

const classes: Record<DocumentStatus, string> = {
  processing: 'border-brand-200 bg-brand-50 text-brand-700',
  ready: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  needs_review: 'border-amber-200 bg-amber-50 text-amber-800',
  approved: 'border-emerald-300 bg-emerald-100 text-emerald-900',
  rejected: 'border-zinc-300 bg-zinc-100 text-zinc-700',
  failed: 'border-red-200 bg-red-50 text-red-700',
}

export function StatusBadge({ status }: { status: DocumentStatus }) {
  return (
    <span
      className={`shrink-0 rounded-md border px-2 py-1 text-xs font-medium ${classes[status]}`}
    >
      {labels[status]}
    </span>
  )
}
