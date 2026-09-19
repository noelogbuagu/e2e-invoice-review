import type {
  DocumentCorrectionRequest,
  ExtractionState,
  FieldSource,
  InvoiceCorrection,
  ReceiptCorrection,
} from './types'

export type FieldInput = 'text' | 'date' | 'amount'

export interface EditableField {
  key: string
  label: string
  input: FieldInput
}

export interface FieldGroup {
  title: string
  fields: EditableField[]
}

type InvoiceKey = keyof InvoiceCorrection
type ReceiptKey = keyof ReceiptCorrection

function invoiceField(key: InvoiceKey, label: string, input: FieldInput = 'text'): EditableField {
  return { key, label, input }
}

function receiptField(key: ReceiptKey, label: string, input: FieldInput = 'text'): EditableField {
  return { key, label, input }
}

export const INVOICE_GROUPS: FieldGroup[] = [
  {
    title: 'Parties and VAT',
    fields: [
      invoiceField('vendor_name', 'Supplier'),
      invoiceField('vendor_vat_id', 'Supplier VAT number'),
      invoiceField('customer_name', 'Customer'),
      invoiceField('customer_vat_id', 'Customer VAT number'),
    ],
  },
  {
    title: 'Invoice details',
    fields: [
      invoiceField('invoice_number', 'Invoice number'),
      invoiceField('purchase_order', 'Purchase order'),
      invoiceField('invoice_date', 'Invoice date', 'date'),
      invoiceField('due_date', 'Due date', 'date'),
      invoiceField('currency', 'Currency'),
    ],
  },
  {
    title: 'Amounts',
    fields: [
      invoiceField('subtotal', 'Subtotal', 'amount'),
      invoiceField('total_tax', 'VAT total', 'amount'),
      invoiceField('invoice_total', 'Invoice total', 'amount'),
    ],
  },
]

export const RECEIPT_GROUPS: FieldGroup[] = [
  {
    title: 'Receipt details',
    fields: [
      receiptField('merchant_name', 'Merchant'),
      receiptField('transaction_date', 'Transaction date', 'date'),
      receiptField('expense_category', 'Expense category'),
      receiptField('currency', 'Currency'),
    ],
  },
  {
    title: 'Amounts',
    fields: [
      receiptField('subtotal', 'Subtotal', 'amount'),
      receiptField('total_tax', 'VAT total', 'amount'),
      receiptField('total', 'Receipt total', 'amount'),
    ],
  },
]

export const SOURCE_LABELS: Record<FieldSource, string> = {
  document_intelligence: 'Document Intelligence',
  llm_fallback: 'LLM filled gap',
  human: 'Edited by reviewer',
}

/** Current scalar values as input strings, keyed by field name. */
export function draftFrom(extraction: ExtractionState): Record<string, string> {
  const document: Record<string, unknown> = { ...(extraction.invoice ?? extraction.receipt) }
  const groups = extraction.invoice ? INVOICE_GROUPS : RECEIPT_GROUPS
  const draft: Record<string, string> = {}
  for (const group of groups) {
    for (const field of group.fields) {
      const value = document[field.key]
      draft[field.key] = typeof value === 'string' ? value : ''
    }
  }
  return draft
}

/** Only changed fields are sent. Empty input clears the field. */
export function correctionFrom(
  extraction: ExtractionState,
  draft: Record<string, string>,
): DocumentCorrectionRequest {
  const original = draftFrom(extraction)
  const changes: Record<string, string | null> = {}
  for (const [key, value] of Object.entries(draft)) {
    const trimmed = value.trim()
    if (trimmed !== original[key]) changes[key] = trimmed || null
  }
  return extraction.invoice ? { invoice: changes } : { receipt: changes }
}
