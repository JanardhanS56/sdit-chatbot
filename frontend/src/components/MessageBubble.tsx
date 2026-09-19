'use client'

import { useState } from 'react'
import type { Message } from '@/lib/api'
import { submitFeedback } from '@/lib/api'

interface Props {
  message: Message
  sessionId: string
  prevUserMessage?: string
}

function formatContent(text: string) {
  return text
    .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
    .replace(/\*(.*?)\*/g, '<em>$1</em>')
    .replace(/`(.*?)`/g, '<code>$1</code>')
    .replace(/\n\n/g, '</p><p>')
    .replace(/\n/g, '<br />')
}

export default function MessageBubble({ message, sessionId, prevUserMessage }: Props) {
  const [feedbackGiven, setFeedbackGiven] = useState<1 | -1 | null>(null)
  const [showSources, setShowSources] = useState(false)

  const isUser = message.role === 'user'
  const isError = message.isError

  const handleFeedback = async (rating: 1 | -1) => {
    setFeedbackGiven(rating)
    await submitFeedback(sessionId, prevUserMessage || '', message.content, rating)
  }

  if (isUser) {
    return (
      <div className="flex justify-end mb-3 msg-animate">
        <div className="max-w-[78%] rounded-xl rounded-tr-sm border border-violet-500/35 bg-violet-950/40 px-4 py-3 text-white shadow-[0_0_18px_rgba(124,58,237,0.12)]">
          <p className="text-sm leading-relaxed">{message.content}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex justify-start mb-3 msg-animate">
      <div className="flex gap-2.5 max-w-[88%]">
        {/* Bot avatar */}
        <div className="neon-glow mt-1 flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg border border-cyan-400/40 bg-[#0b1220]">
          <span className="text-[10px] font-bold neon-text">ST</span>
        </div>

        <div className="flex-1">
          {/* Bubble */}
          <div className={`rounded-2xl rounded-tl-sm px-4 py-3 shadow-sm border ${
            isError
              ? 'border-rose-500/40 bg-rose-950/40 text-rose-200'
              : 'border-slate-800 bg-slate-900/80'
          }`}>
            <div
              className="text-sm leading-relaxed text-slate-700 bot-message"
              dangerouslySetInnerHTML={{ __html: `<p>${formatContent(message.content)}</p>` }}
            />
          </div>

          {/* Source + feedback row */}
          {!isError && (
            <div className="flex items-center gap-3 mt-1.5 px-1">
              {message.sources && message.sources.length > 0 && (
                <button
                  onClick={() => setShowSources(!showSources)}
                    className="flex items-center gap-1 text-[10px] text-slate-500 transition-colors hover:text-cyan-300"
                >
                  {/* Link icon */}
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M13.828 10.172a4 4 0 00-5.656 0l-4 4a4 4 0 105.656 5.656l1.102-1.101m-.758-4.899a4 4 0 005.656 0l4-4a4 4 0 00-5.656-5.656l-1.1 1.1" />
                  </svg>
                  {showSources ? 'hide' : `${message.sources.length} source${message.sources.length > 1 ? 's' : ''}`}
                </button>
              )}

              <div className="flex-1" />

              {/* Feedback */}
              <div className="flex gap-1">
                {[
                  { rating: 1 as const, icon: (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M14 9V5a3 3 0 00-3-3l-4 9v11h11.28a2 2 0 002-1.7l1.38-9a2 2 0 00-2-2.3H14zm-7 9H4.72A2.24 2.24 0 012.5 16V11a2.24 2.24 0 012.22-2H7v9z" />
                    </svg>
                  ), active: 'text-emerald-500' },
                  { rating: -1 as const, icon: (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 15v4a3 3 0 003 3l4-9V2H5.72A2 2 0 003.7 3.7l-1.38 9a2 2 0 002 2.3H10zm7-13h2.67A2.31 2.31 0 0122 4v7a2.31 2.31 0 01-2.33 2H17V2z" />
                    </svg>
                  ), active: 'text-red-400' },
                ].map(({ rating, icon, active }) => (
                  <button
                    key={rating}
                    onClick={() => handleFeedback(rating)}
                    disabled={feedbackGiven !== null}
                    className={`p-1 rounded transition-colors ${
                      feedbackGiven === rating ? active : feedbackGiven !== null ? 'text-slate-200 cursor-default' : 'text-slate-300 hover:' + active.replace('text-', 'text-')
                    }`}
                    title={rating === 1 ? 'Helpful' : 'Not helpful'}
                  >
                    {icon}
                  </button>
                ))}
              </div>
            </div>
          )}

          {/* Sources list */}
          {showSources && message.sources && message.sources.length > 0 && (
            <div className="msg-animate mt-2 space-y-1 rounded-lg border border-slate-800 bg-slate-950/70 p-3 backdrop-blur">
              <p className="mb-2 font-mono text-[10px] font-semibold uppercase tracking-widest text-cyan-300">Sources</p>
              {message.sources.map((s, i) => (
                <div key={i} className="flex items-center gap-1.5 text-xs">
                  <span className="w-1 h-1 rounded-full bg-[var(--neon)] flex-shrink-0" />
                  {s.source_url ? (
                    <a href={s.source_url} target="_blank" rel="noopener noreferrer" className="text-slate-500 hover:text-[var(--dark)] transition-colors hover:underline truncate">
                      {s.title}
                    </a>
                  ) : (
                    <span className="truncate text-slate-400">{s.title}</span>
                  )}
                  <span className="text-slate-300 ml-auto flex-shrink-0">— {s.source}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
