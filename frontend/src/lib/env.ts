const configuredBaseUrl = import.meta.env.VITE_API_BASE_URL

if (configuredBaseUrl === undefined || configuredBaseUrl === null) {
  throw new Error('VITE_API_BASE_URL is required')
}

export const apiBaseUrl = configuredBaseUrl === '/' ? '' : configuredBaseUrl.replace(/\/$/, '')
