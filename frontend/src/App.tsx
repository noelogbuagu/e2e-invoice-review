import { useState } from 'react'

import { DocumentInbox } from './components/DocumentInbox'
import { DocumentReview } from './components/DocumentReview'
import { ProcessingStep } from './components/ProcessingStep'
import { UploadStep } from './components/UploadStep'
import { WelcomePortal } from './components/WelcomePortal'
import { Button } from './components/ui/Button'
import {
  deleteDocument,
  getDocument,
  listDocuments,
  listGlAccounts,
  uploadDocument,
} from './lib/document-api'
import type { Document, GlAccount } from './lib/types'

type View = 'welcome' | 'upload' | 'processing' | 'result' | 'history'

function AppHeader({
  onHome,
  onNew,
  onHistory,
}: {
  onHome: () => void
  onNew: () => void
  onHistory: () => void
}) {
  return (
    <header className="border-b border-zinc-200 bg-white">
      <div className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-3">
        <button type="button" onClick={onHome} className="text-left">
          <p className="font-semibold text-zinc-950">Document review</p>
          <p className="text-xs text-zinc-500">Northstar Facilities B.V.</p>
        </button>
        <nav className="flex items-center gap-2" aria-label="Application">
          <Button onClick={onHistory} variant="ghost" size="sm">
            History
          </Button>
          <Button onClick={onNew} size="sm">
            New review
          </Button>
        </nav>
      </div>
    </header>
  )
}

function message(reason: unknown, fallback: string): string {
  return reason instanceof Error ? reason.message : fallback
}

function App() {
  const [view, setView] = useState<View>('welcome')
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<Document | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [documents, setDocuments] = useState<Document[]>([])
  const [historyLoading, setHistoryLoading] = useState(false)
  const [deletingId, setDeletingId] = useState<string | null>(null)
  const [accounts, setAccounts] = useState<GlAccount[]>([])

  function showResult(document: Document) {
    setResult(document)
    setView('result')
    if (accounts.length === 0) {
      listGlAccounts()
        .then(setAccounts)
        .catch((reason: unknown) => setError(message(reason, 'Could not load the GL catalog.')))
    }
  }

  function startReview() {
    setFile(null)
    setResult(null)
    setError(null)
    setView('upload')
  }

  function openHistory() {
    setError(null)
    setView('history')
    setHistoryLoading(true)
    listDocuments()
      .then(setDocuments)
      .catch((reason: unknown) => setError(message(reason, 'Could not load review history.')))
      .finally(() => setHistoryLoading(false))
  }

  function home() {
    setError(null)
    setView('welcome')
  }

  async function processDocument() {
    if (!file) return
    setError(null)
    setResult(null)
    setView('processing')
    try {
      showResult(await uploadDocument(file))
    } catch (reason) {
      setError(message(reason, 'Could not process the document.'))
      setView('upload')
    }
  }

  async function openDocument(document: Document) {
    setError(null)
    try {
      showResult(await getDocument(document.id))
    } catch (reason) {
      setError(message(reason, 'Could not open the review.'))
    }
  }

  async function removeDocument(document: Document) {
    if (!window.confirm(`Delete the review of ${document.original_filename}? This cannot be undone.`)) {
      return
    }
    setDeletingId(document.id)
    setError(null)
    try {
      await deleteDocument(document.id)
      setDocuments((current) => current.filter((item) => item.id !== document.id))
    } catch (reason) {
      setError(message(reason, 'Could not delete the review.'))
    } finally {
      setDeletingId(null)
    }
  }

  return (
    <div className="min-h-screen bg-zinc-50 text-zinc-950">
      {view !== 'welcome' && (
        <AppHeader onHome={home} onNew={startReview} onHistory={openHistory} />
      )}
      {view === 'welcome' && <WelcomePortal onStart={startReview} onHistory={openHistory} />}
      {view === 'upload' && (
        <UploadStep
          file={file}
          error={error}
          onChoose={(next) => {
            setFile(next)
            setError(null)
          }}
          onProcess={() => void processDocument()}
          onBack={home}
        />
      )}
      {view === 'processing' && file && <ProcessingStep filename={file.name} />}
      {view === 'result' && result && (
        <DocumentReview
          key={result.id}
          document={result}
          accounts={accounts}
          onChanged={setResult}
        />
      )}
      {view === 'history' && (
        <main className="mx-auto max-w-4xl px-6 py-10">
          <p className="text-sm text-zinc-500">Saved locally</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Review history</h1>
          <p className="mt-1 text-sm text-zinc-600">
            Open a saved review or delete it so the same document can be demonstrated again.
          </p>
          {error && (
            <p
              role="alert"
              className="mt-5 rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-800"
            >
              {error}
            </p>
          )}
          {historyLoading && documents.length === 0 ? (
            <p className="mt-6 text-sm text-zinc-500">Loading…</p>
          ) : (
            <DocumentInbox
              documents={documents}
              deletingId={deletingId}
              onOpen={(document) => void openDocument(document)}
              onDelete={(document) => void removeDocument(document)}
              onNew={startReview}
            />
          )}
        </main>
      )}
    </div>
  )
}

export default App
