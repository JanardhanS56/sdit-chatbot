const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface Source {
  title: string
  source: string
  source_url: string
  similarity: number
}

export interface ChatResponse {
  session_id: string
  answer: string
  sources: Source[]
  response_time_ms: number
}

export interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  sources?: Source[]
  timestamp: Date
  isError?: boolean
}

export async function sendMessage(
  message: string,
  sessionId: string,
  userType: string = 'student'
): Promise<ChatResponse> {
  const res = await fetch(`${API_URL}/chat`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      session_id: sessionId,
      user_type: userType,
    }),
  })

  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw new Error(err.detail || 'Something went wrong. Please try again.')
  }

  return res.json()
}

export async function submitFeedback(
  sessionId: string,
  question: string,
  answer: string,
  rating: 1 | -1,
  comment?: string
) {
  await fetch(`${API_URL}/feedback`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ session_id: sessionId, question, answer, rating, comment }),
  }).catch(() => {/* feedback is non-critical */})
}

export async function clearSession(sessionId: string) {
  await fetch(`${API_URL}/session/${sessionId}`, { method: 'DELETE' }).catch(() => {})
}
