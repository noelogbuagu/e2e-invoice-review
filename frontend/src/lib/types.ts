export type DocumentStatus = 'processing' | 'ready' | 'needs_review' | 'failed'
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

export interface ExtractionState {
  invoice: InvoiceExtraction | null
  receipt: ReceiptExtraction | null
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

export interface Document {
  id: string
  original_filename: string
  content_type: string
  status: DocumentStatus
  classification: DocumentClassification | null
  extraction: ExtractionState | null
  validation: ValidationState | null
  gl_suggestion: GlAccountSuggestion | null
  error_message: string | null
  created_at: string
  updated_at: string
}
