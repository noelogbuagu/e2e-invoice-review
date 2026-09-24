import { Button } from './ui/Button'
import { Card, CardContent, CardHeader } from './ui/Card'

interface WelcomePortalProps {
  onStart: () => void
  onHistory: () => void
}

const steps = [
  ['1', 'Upload a document', 'Choose an invoice or receipt and check the preview.'],
  [
    '2',
    'Run the pipeline',
    'Classify, extract, cross-check with an independent LLM read, validate policy, suggest a GL account.',
  ],
  [
    '3',
    'Review and decide',
    'Correct fields, confirm the GL account, approve or reject, or draft a supplier correction email.',
  ],
]

export function WelcomePortal({ onStart, onHistory }: WelcomePortalProps) {
  return (
    <main className="mx-auto flex min-h-screen max-w-3xl items-center px-6 py-12">
      <Card className="w-full overflow-hidden">
        <CardHeader className="bg-black p-8 text-white sm:p-10">
          <div className="flex items-center gap-3">
            <img src="/plurobi-mark.png" alt="" className="h-10 w-10" />
            <p className="text-xl font-bold">Plurobi.</p>
          </div>
          <h1 className="pt-4 text-3xl font-bold tracking-tight">Document review</h1>
          <p className="max-w-xl pt-1 text-base leading-7 text-mist">
            Upload an invoice or receipt, run the review pipeline, and inspect the prepared result
            before bookkeeping.
          </p>
          <div className="flex flex-wrap gap-3 pt-5">
            <Button onClick={onStart}>Review a document</Button>
            <Button onClick={onHistory} variant="inverse">
              View history
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-8 sm:p-10">
          <h2 className="text-sm font-medium text-zinc-900">How it works</h2>
          <ol className="mt-5 divide-y divide-zinc-100">
            {steps.map(([number, title, copy]) => (
              <li
                key={number}
                className="grid gap-2 py-4 first:pt-0 last:pb-0 sm:grid-cols-[32px_160px_1fr] sm:items-start"
              >
                <span className="flex h-7 w-7 items-center justify-center rounded-md bg-brand-500 text-xs font-semibold text-white">
                  {number}
                </span>
                <span className="text-sm font-medium text-zinc-900">{title}</span>
                <span className="text-sm leading-6 text-zinc-500">{copy}</span>
              </li>
            ))}
          </ol>
        </CardContent>
      </Card>
    </main>
  )
}
