import { useState } from 'react'

import { DocumentResult } from './components/DocumentResult'
import { ProcessingStep } from './components/ProcessingStep'
import { UploadStep } from './components/UploadStep'
import { WelcomePortal } from './components/WelcomePortal'
import { Button } from './components/ui/Button'
import { Card } from './components/ui/Card'
import { uploadDocument } from './lib/document-api'
import type { Document } from './lib/types'

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

function App() {
  const [view, setView] = useState<View>('welcome')
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<Document | null>(null)
  const [error, setError] = useState<string | null>(null)

  function startReview() {
    setFile(null)
    setResult(null)
    setError(null)
    setView('upload')
  }

  function openHistory() {
    setError(null)
    setView('history')
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
      const processed = await uploadDocument(file)
      setResult(processed)
      setView('result')
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not process the document.')
      setView('upload')
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
      {view === 'result' && result && <DocumentResult document={result} />}
      {view === 'history' && (
        <main className="mx-auto max-w-4xl px-6 py-10">
          <p className="text-sm text-zinc-500">Saved locally</p>
          <h1 className="mt-1 text-2xl font-semibold tracking-tight">Review history</h1>
          <Card className="mt-6 p-12 text-center">
            <p className="text-sm text-zinc-600">
              Review history will be added in a later build step.
            </p>
            <Button onClick={startReview} className="mt-5">
              Review a document
            </Button>
          </Card>
        </main>
      )}
    </div>
  )
}

export default App
