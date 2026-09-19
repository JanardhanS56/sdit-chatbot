'use client'

import { useState } from 'react'
import { personalizationOptions } from '@/lib/campusData'

interface Props { onClose: () => void; onAsk: (prompt: string) => void }

const questions = [
  ['year', 'What is your current year or level?'],
  ['department', 'Which department or area are you in?'],
  ['interest', 'What kind of activities interest you most?'],
  ['goal', 'What would you like to achieve at SDIT?'],
] as const

export default function PersonalizeMode({ onClose, onAsk }: Props) {
  const [step, setStep] = useState(0)
  const [answers, setAnswers] = useState<Record<string, string>>({})
  const [custom, setCustom] = useState('')
  const [done, setDone] = useState(false)
  const [result, setResult] = useState('')
  const [key, question] = questions[step]
  const options = personalizationOptions[key]

  function choose(value: string) {
    setAnswers(current => ({ ...current, [key]: value }))
    if (step < questions.length - 1) setStep(step + 1)
    else setDone(true)
  }

  function finish() {
    const prompt = `Create a personalised SDIT student plan using only verified knowledge-base information. My profile: year/level=${answers['year']}; department=${answers['department']}; interests=${answers['interest']}; goal=${answers['goal']}; additional note=${custom.trim() || 'None provided'}. Recommend suitable clubs, relevant annual events, and practical next steps. Clearly label approximate event timing and mention when exact details need confirmation.`
    setResult(prompt)
  }

  if (result) return <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#05070c]/90 p-4 backdrop-blur-md"><section className="w-full max-w-lg rounded-xl border border-cyan-400/25 bg-[#0d1420] p-6 shadow-[0_0_60px_rgba(0,240,255,0.12)]"><p className="font-mono text-[10px] uppercase tracking-[0.25em] text-cyan-300">Personalised mode ready</p><h2 className="mt-2 font-display text-xl font-bold text-white">Your student plan is ready</h2><p className="mt-3 text-sm leading-relaxed text-slate-400">I’ll send your answers to the chatbot so it can build a grounded response with relevant clubs, events, and next steps.</p><div className="mt-5 flex justify-end gap-2"><button onClick={onClose} className="rounded-md border border-slate-700 px-3 py-2 text-xs text-slate-300">Cancel</button><button onClick={() => onAsk(result)} className="rounded-md bg-cyan-300 px-3 py-2 text-xs font-semibold text-[#071018]">Generate plan</button></div></section></div>

  if (done) return <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#05070c]/90 p-4 backdrop-blur-md"><section className="w-full max-w-lg rounded-xl border border-cyan-400/25 bg-[#0d1420] p-6 shadow-[0_0_60px_rgba(0,240,255,0.12)]"><p className="font-mono text-[10px] uppercase tracking-[0.25em] text-cyan-300">Question 4 of 4</p><h2 className="mt-2 font-display text-xl font-bold text-white">Anything else we should consider?</h2><textarea value={custom} onChange={event => setCustom(event.target.value)} rows={4} placeholder="For example: I want to volunteer or build a portfolio." className="mt-5 w-full resize-none rounded-md border border-slate-700 bg-slate-950 px-3 py-2 text-sm text-slate-100 outline-none focus:border-cyan-400" /><div className="mt-5 flex justify-between"><button onClick={() => setDone(false)} className="rounded-md border border-slate-700 px-3 py-2 text-xs text-slate-300">Back</button><button onClick={finish} className="rounded-md bg-cyan-300 px-3 py-2 text-xs font-semibold text-[#071018]">Review answers</button></div></section></div>

  return <div className="fixed inset-0 z-50 flex items-center justify-center bg-[#05070c]/90 p-4 backdrop-blur-md"><section className="w-full max-w-lg rounded-xl border border-cyan-400/25 bg-[#0d1420] p-6 shadow-[0_0_60px_rgba(0,240,255,0.12)]"><div className="flex items-center justify-between"><p className="font-mono text-[10px] uppercase tracking-[0.25em] text-cyan-300">Personalise your experience</p><span className="font-mono text-[10px] text-slate-500">{step + 1} / {questions.length}</span></div><h2 className="mt-2 font-display text-xl font-bold text-white">{question}</h2><div className="mt-5 grid gap-2">{options.map(option => <button key={option} onClick={() => choose(option)} className="rounded-md border border-slate-700 bg-slate-950/50 px-4 py-3 text-left text-sm text-slate-300 transition hover:border-cyan-400/60 hover:bg-cyan-400/10 hover:text-cyan-200">{option}</button>)}</div><button onClick={onClose} className="mt-5 text-xs text-slate-500 hover:text-slate-300">Exit personalised mode</button></section></div>
}
