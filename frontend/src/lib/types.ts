export type DocumentStatus =
  | 'processing'
  | 'ready'
  | 'needs_review'
  | 'approved'
  | 'rejected'
  | 'failed'
export type Decision = 'approved' | 'rejected'
export type DocumentKind = 'invoice' | 'receipt'
export type IssueSeverity = 'error' | 'warning'

export interface DocumentClassification {
  document_kind: DocumentKind
  confidence: number
  reasoning: string
}

export interface InvoiceExtraction {
  vendor_name: string | null
  vendor_vat_id: string | null
  customer_name: string | null
  customer_vat_id: string | null
  invoice_number: string | null
  invoice_date: string | null
  due_date: string | null
  purchase_order: string | null
  currency: string | null
  subtotal: string | null
  total_tax: string | null
  invoice_total: string | null
  confidence: number | null
}

export interface ReceiptExtraction {
  merchant_name: string | null
  merchant_address: string | null
  transaction_date: string | null
  transaction_time: string | null
  expense_category: string | null
  currency: string | null
  subtotal: string | null
  total_tax: string | null
  total: string | null
  confidence: number | null
}

export type FieldSource = 'document_intelligence' | 'llm_fallback' | 'human'

export interface ExtractionState {
  invoice: InvoiceExtraction | null
  receipt: ReceiptExtraction | null
  field_sources: Record<string, FieldSource>
}

export type ComparisonStatus =
  | 'match'
  | 'different'
  | 'missing_in_llm'
  | 'missing_in_document_intelligence'
  | 'missing_in_both'

export interface LlmDocumentExtraction {
  document_kind: DocumentKind | 'unsupported'
  vendor_name: string | null
  vendor_vat_id: string | null
  customer_name: string | null
  customer_vat_id: string | null
  invoice_number: string | null
  purchase_order: string | null
  invoice_date: string | null
  due_date: string | null
  currency: string | null
  subtotal: string | null
  total_tax: string | null
  total: string | null
  expense_category: string | null
  summary: string
}

export interface FieldComparison {
  field: string
  label: string
  status: ComparisonStatus
  document_intelligence_value: string | null
  llm_value: string | null
}

export interface DocumentReview {
  extraction: LlmDocumentExtraction | null
  comparisons: FieldComparison[]
  fallback_fields: string[]
  error_message: string | null
}

export interface ValidationIssue {
  code: string
  message: string
  severity: IssueSeverity
}

export interface ValidationState {
  issues: ValidationIssue[]
}

export interface GlAccountSuggestion {
  account_code: string
  account_name: string
  confidence: number
  reasoning: string
}

export interface GlAccount {
  code: string
  name: string
  description: string
}

/** Scalar fields Maya may correct. Keys mirror the backend correction models. */
export type InvoiceCorrection = Partial<Omit<InvoiceExtraction, 'confidence'>>
export type ReceiptCorrection = Partial<
  Omit<ReceiptExtraction, 'confidence' | 'merchant_address' | 'transaction_time'>
>

export interface DocumentCorrectionRequest {
  invoice?: InvoiceCorrection
  receipt?: ReceiptCorrection
}

/** Generated on demand and shown for copying. The app never sends it. */
export interface CorrectionEmailDraft {
  recipient_name: string
  subject: string
  body: string
  issue_codes: string[]
}

export interface Document {
  id: string
  original_filename: string
  content_type: string
  status: DocumentStatus
  classification: DocumentClassification | null
  extraction: ExtractionState | null
  document_review: DocumentReview | null
  validation: ValidationState | null
  gl_suggestion: GlAccountSuggestion | null
  selected_gl_account_code: string | null
  error_message: string | null
  created_at: string
  updated_at: string
}
