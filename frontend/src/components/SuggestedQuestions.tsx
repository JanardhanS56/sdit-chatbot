'use client'

import { useState, useEffect } from 'react'

// Dynamic suggestion pools — rotated on each mount
const POOLS = {
  student: [
    "Who is the principal of SDIT?",
    "What are the B.E. programs offered?",
    "How do I apply for admission?",
    "What is the fee structure?",
    "Tell me about hostel facilities",
    "What placement companies visit SDIT?",
    "How does the anti-ragging committee work?",
    "What clubs can I join?",
    "What scholarships are available?",
    "Tell me about the library",
  ],
  faculty: [
    "Who are the HODs at SDIT?",
    "How does the grievance redressal work?",
    "What is the IQAC structure?",
    "Tell me about research centres",
    "What is the CBCS curriculum?",
  ],
  visitor: [
    "Where is SDIT located?",
    "What courses does SDIT offer?",
    "What is SDIT's placement track record?",
    "How can I contact SDIT?",
    "Tell me about SDIT's vision and mission",
  ],
}

interface Props {
  onSelect: (q: string) => void
  userType?: 'student' | 'faculty' | 'visitor'
}

export default function SuggestedQuestions({ onSelect, userType = 'student' }: Props) {
  const [displayed, setDisplayed] = useState<string[]>([])

  useEffect(() => {
    const pool = POOLS[userType] || POOLS.student
    const shuffled = [...pool].sort(() => Math.random() - 0.5)
    setDisplayed(shuffled.slice(0, 5))
  }, [userType])

  if (!displayed.length) return null

  return (
    <div className="animate-fade-in pb-3">
      <p className="mb-2.5 flex items-center gap-1.5 font-mono text-[10px] font-semibold uppercase tracking-widest text-slate-500">
        <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
        </svg>
        Try asking
      </p>
      <div className="flex flex-wrap gap-2">
        {displayed.map((q, i) => (
          <button
            key={q}
            onClick={() => onSelect(q)}
            className="chip rounded-full border border-slate-700/80 bg-slate-900/80 px-3.5 py-1.5 text-xs text-slate-300 shadow-sm transition-all duration-200 hover:border-cyan-400/60 hover:bg-slate-800 hover:text-cyan-300"
            style={{ animationDelay: `${i * 60}ms` }}
          >
            {q}
          </button>
        ))}
      </div>
    </div>
  )
}
