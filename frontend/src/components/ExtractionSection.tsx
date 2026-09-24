import { INVOICE_GROUPS, RECEIPT_GROUPS, SOURCE_LABELS } from '../lib/review-fields'
import type { ExtractionState, FieldSource } from '../lib/types'
import { Button } from './ui/Button'
import { Card } from './ui/Card'

interface ExtractionSectionProps {
  extraction: ExtractionState
  draft: Record<string, string>
  disabled: boolean
  dirty: boolean
  saving: boolean
  onChange: (key: string, value: string) => void
  onSave: () => void
  onReset: () => void
  /** Present only when supplier-fixable errors exist and the review is still open. */
  onDraftEmail: (() => void) | null
}

const sourceClasses: Record<FieldSource, string> = {
  document_intelligence: 'bg-zinc-100 text-zinc-600',
  llm_fallback: 'bg-brand-50 text-brand-700',
  human: 'bg-emerald-50 text-emerald-700',
}

export function ExtractionSection({
  extraction,
  draft,
  disabled,
  dirty,
  saving,
  onChange,
  onSave,
  onReset,
  onDraftEmail,
}: ExtractionSectionProps) {
  const groups = extraction.invoice ? INVOICE_GROUPS : RECEIPT_GROUPS
  const confidence = (extraction.invoice ?? extraction.receipt)?.confidence

  return (
    <Card className="mt-6 p-6">
      <div className="flex flex-wrap items-start justify-between gap-4">
        <div>
          <h2 className="text-sm font-medium">Document Intelligence extraction</h2>
          <p className="mt-1 text-sm text-zinc-600">
            Primary reading{confidence != null ? ` · confidence ${confidence.toFixed(2)}` : ''}.
            Edit any value and save to re-run Plurobi policy.
          </p>
        </div>
        <div className="flex gap-2">
          {onDraftEmail && (
            <Button variant="outline" size="sm" disabled={disabled} onClick={onDraftEmail}>
              Draft correction email
            </Button>
          )}
          <Button variant="ghost" size="sm" disabled={!dirty || disabled} onClick={onReset}>
            Discard
          </Button>
          <Button size="sm" disabled={disabled} onClick={onSave}>
            {saving ? 'Saving…' : dirty ? 'Save and re-check' : 'Re-check policy'}
          </Button>
        </div>
      </div>

      {groups.map((group) => (
        <fieldset key={group.title} className="mt-6">
          <legend className="text-xs font-medium uppercase tracking-wide text-zinc-500">
            {group.title}
          </legend>
          <div className="mt-3 grid gap-4 sm:grid-cols-2">
            {group.fields.map((field) => {
              const source = extraction.field_sources[field.key]
              return (
                <label key={field.key} className="block text-sm">
                  <span className="flex items-center justify-between gap-2">
                    <span className="font-medium text-zinc-800">{field.label}</span>
                    {source && (
                      <span
                        className={`rounded px-1.5 py-0.5 text-[11px] ${sourceClasses[source]}`}
                      >
                        {SOURCE_LABELS[source]}
                      </span>
                    )}
                  </span>
                  <input
                    type={field.input === 'date' ? 'date' : 'text'}
                    inputMode={field.input === 'amount' ? 'decimal' : undefined}
                    value={draft[field.key] ?? ''}
                    disabled={disabled}
                    placeholder="Not found"
                    onChange={(event) => onChange(field.key, event.target.value)}
                    className="mt-1 block w-full rounded-lg border border-zinc-300 px-3 py-2 text-sm placeholder:text-zinc-400 disabled:bg-zinc-100"
                  />
                </label>
              )
            })}
          </div>
        </fieldset>
      ))}
    </Card>
  )
}
