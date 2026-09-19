import type { DocumentReview, DocumentStatus, ValidationIssue } from './types'

export type OutcomeKind = 'passed' | 'attention' | 'blocked' | 'decided' | 'failed'

export interface ReviewOutcome {
  kind: OutcomeKind
  title: string
  description: string
}

function count(n: number, noun: string): string {
  return `${n} ${noun}${n === 1 ? '' : 's'}`
}

/** Mirrors backend/app/correction_email/eligibility.py: errors the supplier can fix. */
const INTERNAL_ISSUE_CODES = new Set(['duplicate_invoice', 'low_extraction_confidence'])

export function supplierFixableIssues(issues: ValidationIssue[]): ValidationIssue[] {
  return issues.filter(
    (issue) => issue.severity === 'error' && !INTERNAL_ISSUE_CODES.has(issue.code),
  )
}

export function summarizeReview(status: DocumentStatus, issues: ValidationIssue[]): ReviewOutcome {
  const errors = issues.filter((issue) => issue.severity === 'error').length
  const warnings = issues.filter((issue) => issue.severity === 'warning').length

  switch (status) {
    case 'failed':
      return {
        kind: 'failed',
        title: 'Processing failed',
        description: 'The document could not be processed. Try again or check the provider setup.',
      }
    case 'approved':
      return {
        kind: 'decided',
        title: 'Approved',
        description: 'This document is approved and can no longer be edited.',
      }
    case 'rejected':
      return {
        kind: 'decided',
        title: 'Rejected',
        description: 'This document is rejected and can no longer be edited.',
      }
    case 'processing':
      return { kind: 'attention', title: 'Processing', description: 'The pipeline is running.' }
    case 'needs_review':
    case 'ready':
      if (errors > 0) {
        return {
          kind: 'blocked',
          title: 'Approval blocked',
          description: `${count(errors, 'error')} must be fixed before approval.${
            warnings > 0 ? ` ${count(warnings, 'warning')} to verify.` : ''
          }`,
        }
      }
      if (warnings > 0) {
        return {
          kind: 'attention',
          title: 'Passed with warnings',
          description: `${count(warnings, 'warning')} to verify. You can still approve.`,
        }
      }
      return {
        kind: 'passed',
        title: 'Passed automatic checks',
        description: 'No findings. Confirm the GL account and approve.',
      }
    default: {
      const exhaustive: never = status
      return exhaustive
    }
  }
}

export interface CrossCheckSummary {
  kind: 'agreement' | 'supplemented' | 'differences' | 'unavailable'
  title: string
  description: string
}

export function summarizeCrossCheck(review: DocumentReview): CrossCheckSummary {
  if (review.error_message) {
    return { kind: 'unavailable', title: 'LLM check unavailable', description: review.error_message }
  }
  const compared = review.comparisons.filter((item) => item.status !== 'missing_in_both')
  const conflicts = compared.filter((item) => item.status === 'different').length
  const filled = review.fallback_fields.length
  if (conflicts > 0) {
    return {
      kind: 'differences',
      title: `Models disagree on ${count(conflicts, 'field')}`,
      description: 'Document Intelligence stays selected. Check the highlighted rows below.',
    }
  }
  if (filled > 0) {
    return {
      kind: 'supplemented',
      title: `LLM filled ${count(filled, 'missing field')}`,
      description: 'Document Intelligence stays primary. Gaps came from the independent reading.',
    }
  }
  return {
    kind: 'agreement',
    title: 'LLM check agrees',
    description: `The independent reading matched all ${compared.length} compared fields.`,
  }
}
