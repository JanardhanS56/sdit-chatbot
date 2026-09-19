'use client'

import { useEffect, useRef, useState } from 'react'
import { v4 as uuidv4 } from 'uuid'
import type { Message } from '@/lib/api'
import { clearSession, sendMessage } from '@/lib/api'
import MessageBubble from '@/components/MessageBubble'
import SuggestedQuestions from '@/components/SuggestedQuestions'
import TypingIndicator from '@/components/TypingIndicator'
import CalendarView from '@/components/CalendarView'
import PersonalizeMode from '@/components/PersonalizeMode'

const SESSION_KEY = 'sdit_session_id'

function getSessionId() {
  if (typeof window === 'undefined') return uuidv4()
  const existing = sessionStorage.getItem(SESSION_KEY)
  if (existing) return existing
  const created = uuidv4()
  sessionStorage.setItem(SESSION_KEY, created)
  return created
}

const welcome: Message = {
  id: 'welcome',
  role: 'assistant',
  content: "**Welcome to SDIT Tech-Bot.** Ask me about admissions, courses, departments, facilities, placements, or official contact information. I will use the available SDIT knowledge base and show sources when they are available.",
  timestamp: new Date(),
}

export default function ChatPage() {
  const [messages, setMessages] = useState<Message[]>([welcome])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [userType, setUserType] = useState<'student' | 'faculty' | 'visitor'>('student')
  const [sessionId] = useState(getSessionId)
  const [showComplaint, setShowComplaint] = useState(false)
  const [showCalendar, setShowCalendar] = useState(false)
  const [showPersonalize, setShowPersonalize] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, loading])

  async function submit(text = input) {
    const query = text.trim()
    if (!query || loading) return
    setMessages(current => [...current, { id: uuidv4(), role: 'user', content: query, timestamp: new Date() }])
    setInput('')
    setLoading(true)
    try {
      const response = await sendMessage(query, sessionId, userType)
      setMessages(current => [...current, { id: uuidv4(), role: 'assistant', content: response.answer, sources: response.sources, timestamp: new Date() }])
    } catch (error) {
      setMessages(current => [...current, { id: uuidv4(), role: 'assistant', content: error instanceof Error ? error.message : 'The assistant is temporarily unavailable. Please try again or contact the helpdesk.', timestamp: new Date(), isError: true }])
    } finally {
      setLoading(false)
      inputRef.current?.focus()
    }
  }

  async function newChat() {
    await clearSession(sessionId)
    sessionStorage.removeItem(SESSION_KEY)
    window.location.reload()
  }

  return (
    <div className="cyber-grid min-h-screen overflow-hidden bg-[#070a10] text-slate-100">
      <div className="pointer-events-none fixed inset-0 bg-[radial-gradient(circle_at_12%_8%,rgba(0,240,255,0.12),transparent_30%),radial-gradient(circle_at_88%_88%,rgba(124,58,237,0.14),transparent_32%)]" />
      <header className="relative z-10 border-b border-slate-800/80 bg-[#0a0e17]/90 px-4 py-2.5 backdrop-blur-md">
        <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 text-xs">
          <div className="flex min-w-0 items-center gap-2.5">
            <div className="neon-glow flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border border-cyan-400/50 bg-[#0b1220] font-display font-bold text-cyan-300">ST</div>
            <div className="min-w-0"><p className="truncate font-display font-semibold tracking-wide text-slate-100">Shree Devi Institute of Technology</p><p className="hidden truncate font-mono text-[10px] text-slate-500 sm:block">Kenjar, Mangaluru · Campus information assistant</p></div>
          </div>
          <div className="hidden items-center gap-3 font-mono text-[10px] text-slate-500 md:flex"><span className="text-cyan-300">●</span> KNOWLEDGE LINK ONLINE</div>
        </div>
      </header>

      <main className="relative z-10 mx-auto flex min-h-[calc(100vh-49px)] w-full max-w-7xl items-center justify-center p-3 sm:p-6">
        <section className="flex h-[min(860px,calc(100vh-73px))] min-h-[560px] w-full max-w-5xl flex-col overflow-hidden rounded-xl border border-cyan-400/20 bg-[#0f1523]/90 shadow-[0_0_55px_rgba(0,240,255,0.12)] backdrop-blur-xl">
          <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800/90 bg-slate-950/45 px-4 py-3 sm:px-6">
            <div><div className="flex items-center gap-2"><h1 className="font-display text-base font-bold tracking-wider sm:text-lg">SDIT <span className="neon-text">TECH-BOT</span></h1><span className="rounded border border-cyan-400/30 bg-cyan-950/40 px-1.5 py-0.5 font-mono text-[9px] text-cyan-300">RAG AI</span></div><p className="mt-0.5 font-mono text-[10px] text-slate-500">Verified campus guidance · conversational search</p></div>
            <div className="flex items-center gap-2"><span className="hidden items-center gap-1.5 rounded-full border border-emerald-500/30 bg-emerald-950/30 px-2.5 py-1 font-mono text-[10px] text-emerald-300 sm:flex"><span className="h-1.5 w-1.5 rounded-full bg-emerald-400 shadow-[0_0_8px_#34d399]" /> LIVE</span><button onClick={() => setShowCalendar(true)} className="rounded-md border border-cyan-400/30 px-2 py-1.5 text-xs text-cyan-200 transition hover:bg-cyan-950/40" title="Open annual events calendar">Calendar</button><button onClick={() => setShowPersonalize(true)} className="rounded-md border border-fuchsia-400/30 px-2 py-1.5 text-xs text-fuchsia-200 transition hover:bg-fuchsia-950/40" title="Start personalised mode">Personalise</button><select aria-label="User type" value={userType} onChange={e => setUserType(e.target.value as typeof userType)} className="rounded-md border border-slate-700 bg-slate-950 px-2 py-1.5 text-xs text-slate-300 outline-none focus:border-cyan-400"><option value="student">Student</option><option value="faculty">Faculty</option><option value="visitor">Visitor</option></select><button onClick={() => setShowComplaint(true)} className="rounded-md border border-rose-500/30 px-2 py-1.5 text-xs text-rose-300 transition hover:bg-rose-950/40" title="Open complaint form">Report</button><button onClick={newChat} className="rounded-md bg-cyan-300 px-2.5 py-1.5 font-display text-xs font-semibold text-[#071018] transition hover:bg-cyan-200" title="Start a new conversation">New chat</button></div>
          </div>

          <div className="flex-1 overflow-y-auto px-3 py-5 sm:px-8">{messages.map((message, index) => { const previous = [...messages].slice(0, index).reverse().find(item => item.role === 'user'); return <MessageBubble key={message.id} message={message} sessionId={sessionId} prevUserMessage={previous?.content} /> })}{loading && <TypingIndicator />}<div ref={bottomRef} /></div>
          {messages.length === 1 && <div className="border-t border-slate-800/80 px-3 pt-3 sm:px-8"><SuggestedQuestions onSelect={submit} userType={userType} /></div>}
          <form onSubmit={event => { event.preventDefault(); submit() }} className="border-t border-slate-800/90 bg-slate-950/65 px-3 py-3 sm:px-8"><div className="flex items-end gap-2 rounded-lg border border-slate-700/80 bg-[#0a0e17] px-3 py-2 transition focus-within:border-cyan-400/70 focus-within:shadow-[0_0_15px_rgba(0,240,255,0.16)]"><span className="pb-2 font-mono text-cyan-300">&gt;</span><textarea ref={inputRef} rows={1} value={input} onChange={event => setInput(event.target.value)} onKeyDown={event => { if (event.key === 'Enter' && !event.shiftKey) { event.preventDefault(); submit() } }} placeholder="Ask about admissions, courses, facilities, or placements..." disabled={loading} className="max-h-28 min-h-8 flex-1 resize-none bg-transparent py-1.5 text-sm text-slate-100 outline-none placeholder:text-slate-600 disabled:opacity-50" /><button type="submit" disabled={loading || !input.trim()} className="flex h-9 w-9 shrink-0 items-center justify-center rounded-md bg-cyan-300 font-bold text-[#071018] transition hover:bg-cyan-200 disabled:bg-slate-700 disabled:text-slate-500" title="Send message">↗</button></div><p className="mt-2 text-center font-mono text-[10px] text-slate-600">For urgent matters, contact SDIT helpdesk: +91 9353619812</p></form>
        </section>
      </main>
      {showComplaint && <ComplaintForm onClose={() => setShowComplaint(false)} />}
      {showCalendar && <CalendarView onClose={() => setShowCalendar(false)} />}
      {showPersonalize && <PersonalizeMode onClose={() => setShowPersonalize(false)} onAsk={prompt => { setShowPersonalize(false); submit(prompt) }} />}
    </div>
  )
}

function ComplaintForm({ onClose }: { onClose: () => void }) {
  const [category, setCategory] = useState('academic')
  const [description, setDescription] = useState('')
  const [name, setName] = useState('')
  const [studentId, setStudentId] = useState('')
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')

  async function handleSubmit() {
    if (description.trim().length < 10) return
    setStatus('loading')
    try { const response = await fetch(`${process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'}/complaint`, { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ student_name: name, student_id: studentId, category, description }) }); if (!response.ok) throw new Error(); setStatus('done') } catch { setStatus('error') }
  }

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/70 p-4 backdrop-blur-sm"><div className="w-full max-w-md rounded-xl border border-cyan-400/30 bg-[#111827] shadow-[0_0_35px_rgba(0,240,255,0.18)]"><div className="flex items-center justify-between border-b border-slate-800 px-5 py-4"><h2 className="font-display font-semibold">Submit a complaint</h2><button onClick={onClose} className="text-slate-400 hover:text-white" title="Close">×</button></div>{status === 'done' ? <div className="p-8 text-center"><p className="text-emerald-300">Complaint submitted successfully.</p><button onClick={onClose} className="mt-5 rounded-md bg-cyan-300 px-4 py-2 text-sm font-semibold text-[#071018]">Close</button></div> : <div className="space-y-4 p-5"><div className="grid grid-cols-2 gap-3"><input value={name} onChange={e => setName(e.target.value)} placeholder="Name (optional)" className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400" /><input value={studentId} onChange={e => setStudentId(e.target.value)} placeholder="USN / ID" className="rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400" /></div><select value={category} onChange={e => setCategory(e.target.value)} className="w-full rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400"><option value="academic">Academic</option><option value="facility">Facility</option><option value="hostel">Hostel</option><option value="other">Other</option></select><textarea value={description} onChange={e => setDescription(e.target.value)} rows={5} placeholder="Describe your issue (minimum 10 characters)" className="w-full resize-none rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm outline-none focus:border-cyan-400" />{status === 'error' && <p className="text-xs text-rose-300">Could not submit. Please try again or contact the helpdesk.</p>}<div className="flex justify-end gap-2"><button onClick={onClose} className="px-3 py-2 text-sm text-slate-400">Cancel</button><button onClick={handleSubmit} disabled={status === 'loading' || description.trim().length < 10} className="rounded-md bg-cyan-300 px-4 py-2 text-sm font-semibold text-[#071018] disabled:opacity-40">{status === 'loading' ? 'Submitting...' : 'Submit'}</button></div></div>}</div></div>
}