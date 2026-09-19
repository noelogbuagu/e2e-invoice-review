export const PROCESSING_STEPS = [
  {
    title: 'Classify document',
    description: 'Recognizing whether the upload is an invoice or a receipt.',
  },
  {
    title: 'Extract fields',
    description: 'Using the matching Document Intelligence model to read the document.',
  },
  {
    title: 'Independent LLM review',
    description: 'A second read of the original document. Document Intelligence stays primary.',
  },
  {
    title: 'Validate Northstar policy',
    description: 'Applying deterministic invoice or receipt rules, including VAT and totals.',
  },
  {
    title: 'Suggest GL account',
    description: 'Matching the normalized fields to the fixed Northstar catalog.',
  },
] as const

export function processingStepAt(elapsedMs: number): number {
  if (elapsedMs >= 14000) return 4
  if (elapsedMs >= 11000) return 3
  if (elapsedMs >= 5000) return 2
  if (elapsedMs >= 2500) return 1
  return 0
}
