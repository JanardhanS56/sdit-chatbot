'use client'

import { useState } from 'react'
import { campusEvents } from '@/lib/campusData'

const months = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December']
const typeStyles: Record<string, string> = {
  academic: 'border-sky-400/40 bg-sky-400/10 text-sky-200',
  technical: 'border-cyan-400/40 bg-cyan-400/10 text-cyan-200',
  cultural: 'border-fuchsia-400/40 bg-fuchsia-400/10 text-fuchsia-200',
  community: 'border-emerald-400/40 bg-emerald-400/10 text-emerald-200',
  sports: 'border-amber-400/40 bg-amber-400/10 text-amber-200',
}

export default function CalendarView({ onClose }: { onClose: () => void }) {
  const [month, setMonth] = useState(new Date().getMonth())
  const events = campusEvents.filter(event => event.months.includes(month))

  return (
    <div className="fixed inset-0 z-50 overflow-y-auto bg-[#05070c]/90 p-3 backdrop-blur-md sm:p-8">
      <section className="mx-auto max-w-6xl rounded-xl border border-cyan-400/25 bg-[#0d1420] shadow-[0_0_60px_rgba(0,240,255,0.12)]">
        <div className="flex flex-wrap items-center justify-between gap-3 border-b border-slate-800 px-5 py-4 sm:px-7">
          <div><p className="font-mono text-[10px] uppercase tracking-[0.25em] text-cyan-300">Campus calendar</p><h2 className="mt-1 font-display text-xl font-bold text-white">SDIT events across the year</h2><p className="mt-1 text-xs text-slate-500">Annual timing is approximate. Exact dates require a current college announcement.</p></div>
          <button onClick={onClose} className="rounded-md border border-slate-700 px-3 py-2 text-xs text-slate-300 hover:border-cyan-400 hover:text-cyan-200" title="Close calendar">Close</button>
        </div>
        <div className="grid gap-5 p-4 sm:p-7 lg:grid-cols-[1fr_280px]">
          <div className="grid grid-cols-2 gap-2 sm:grid-cols-3 md:grid-cols-4">
            {months.map((item, index) => {
              const count = campusEvents.filter(event => event.months.includes(index)).length
              return <button key={item} onClick={() => setMonth(index)} className={`min-h-24 rounded-lg border p-3 text-left transition ${month === index ? 'border-cyan-300 bg-cyan-400/10 shadow-[0_0_18px_rgba(0,240,255,0.12)]' : 'border-slate-800 bg-slate-950/40 hover:border-slate-600'}`}><span className="font-display text-sm font-semibold text-slate-200">{item}</span><span className="mt-4 block font-mono text-[10px] text-slate-500">{count ? `${count} event${count > 1 ? 's' : ''}` : 'No listed events'}</span></button>
            })}
          </div>
          <div className="rounded-lg border border-slate-800 bg-slate-950/40 p-4"><p className="font-mono text-[10px] uppercase tracking-widest text-slate-500">{months[month]} focus</p><div className="mt-3 space-y-3">{events.length ? events.map(event => <article key={event.name} className={`rounded-md border p-3 ${typeStyles[event.type]}`}><div className="flex items-start justify-between gap-2"><h3 className="text-sm font-semibold">{event.name}</h3><span className="font-mono text-[9px] uppercase opacity-70">approx.</span></div><p className="mt-1 text-xs leading-relaxed opacity-80">{event.description}</p><p className="mt-2 font-mono text-[10px] opacity-70">Typical timing: {event.month}</p></article>) : <p className="text-sm leading-relaxed text-slate-500">No event is listed for this month in the current knowledge base.</p>}</div></div>
        </div>
      </section>
    </div>
  )
}
