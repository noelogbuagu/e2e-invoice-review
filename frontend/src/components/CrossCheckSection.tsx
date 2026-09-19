import { summarizeCrossCheck } from '../lib/review-outcome'
import type { ComparisonStatus, DocumentReview } from '../lib/types'
import { Card } from './ui/Card'

const statusLabels: Record<ComparisonStatus, string> = {
  match: 'Match',
  different: 'Disagree',
  missing_in_llm: 'LLM: not found',
  missing_in_document_intelligence: 'Filled by LLM',
  missing_in_both: 'Not found',
}

const statusClasses: Record<ComparisonStatus, string> = {
  match: 'text-emerald-700',
  different: 'text-red-700 font-medium',
  missing_in_llm: 'text-zinc-500',
  missing_in_document_intelligence: 'text-blue-700',
  missing_in_both: 'text-zinc-400',
}

const summaryClasses = {
  agreement: 'border-emerald-200 bg-emerald-50 text-emerald-900',
  supplemented: 'border-blue-200 bg-blue-50 text-blue-900',
  differences: 'border-amber-200 bg-amber-50 text-amber-900',
  unavailable: 'border-zinc-200 bg-zinc-50 text-zinc-700',
}

export function CrossCheckSection({ review }: { review: DocumentReview }) {
  const summary = summarizeCrossCheck(review)
  const rows = review.comparisons.filter((item) => item.status !== 'missing_in_both')

  return (
    <Card className="mt-6 p-6">
      <h2 className="text-sm font-medium">Independent LLM check</h2>
      <p className="mt-1 text-sm text-zinc-600">
        Azure OpenAI read the original file without seeing the Document Intelligence output.
        It fills gaps only; conflicts stay on the primary value.
      </p>
      <div className={`mt-4 rounded-lg border p-4 text-sm ${summaryClasses[summary.kind]}`}>
        <p className="font-medium">{summary.title}</p>
        <p className="mt-1 opacity-90">{summary.description}</p>
      </div>
      {review.extraction?.summary && (
        <p className="mt-3 text-sm italic text-zinc-600">“{review.extraction.summary}”</p>
      )}
      {rows.length > 0 && (
        <table className="mt-4 w-full text-sm">
          <thead className="text-left text-xs uppercase tracking-wide text-zinc-500">
            <tr>
              <th className="py-2 pr-4 font-medium">Field</th>
              <th className="py-2 pr-4 font-medium">Document Intelligence</th>
              <th className="py-2 pr-4 font-medium">LLM</th>
              <th className="py-2 font-medium">Result</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-zinc-100">
            {rows.map((item) => (
              <tr key={item.field} className={item.status === 'different' ? 'bg-red-50/50' : ''}>
                <td className="py-2 pr-4 text-zinc-700">{item.label}</td>
                <td className="py-2 pr-4 text-zinc-900">{item.document_intelligence_value ?? '—'}</td>
                <td className="py-2 pr-4 text-zinc-900">{item.llm_value ?? '—'}</td>
                <td className={`py-2 ${statusClasses[item.status]}`}>{statusLabels[item.status]}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </Card>
  )
}
