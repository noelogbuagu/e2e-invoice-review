import { useState, type FormEvent } from 'react'

import { login } from '../lib/document-api'
import { Button } from './ui/Button'
import { Card, CardContent, CardHeader } from './ui/Card'

interface LoginPageProps {
  onSuccess: () => void
}

export function LoginPage({ onSuccess }: LoginPageProps) {
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  async function submit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      await login(password)
      onSuccess()
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : 'Could not sign in.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-zinc-100 px-6 py-12">
      <div className="w-full max-w-sm">
        <div className="mb-6 flex items-center justify-center gap-3">
          <img src="/plurobi-mark.png" alt="" className="h-10 w-10" />
          <p className="text-xl font-bold">Plurobi.</p>
        </div>
        <Card className="shadow-md">
          <CardHeader>
            <h1 className="text-2xl font-semibold tracking-tight">Document review</h1>
            <p className="text-sm text-zinc-500">Enter the shared password to continue.</p>
          </CardHeader>
          <CardContent>
            <form className="space-y-4" onSubmit={(event) => void submit(event)}>
              <div>
                <label className="text-sm font-medium text-zinc-900" htmlFor="access-password">
                  Password
                </label>
                <div className="relative mt-2">
                  <input
                    id="access-password"
                    type={showPassword ? 'text' : 'password'}
                    autoComplete="current-password"
                    required
                    value={password}
                    onChange={(event) => setPassword(event.target.value)}
                    className="h-10 w-full rounded-md border border-zinc-200 bg-white px-3 pr-16 text-sm shadow-sm outline-none focus-visible:ring-2 focus-visible:ring-brand-500"
                  />
                  <button
                    type="button"
                    className="absolute inset-y-0 right-2 text-xs font-medium text-zinc-500 hover:text-zinc-900"
                    onClick={() => setShowPassword((current) => !current)}
                  >
                    {showPassword ? 'Hide' : 'Show'}
                  </button>
                </div>
              </div>
              {error && (
                <p
                  role="alert"
                  className="rounded-md border border-red-200 bg-red-50 px-3 py-2 text-sm text-red-800"
                >
                  {error}
                </p>
              )}
              <Button type="submit" className="w-full" disabled={submitting}>
                {submitting ? 'Signing in…' : 'Continue'}
              </Button>
            </form>
          </CardContent>
        </Card>
      </div>
    </main>
  )
}
