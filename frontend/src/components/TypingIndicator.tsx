export default function TypingIndicator() {
  return (
    <div className="flex justify-start mb-3 msg-animate">
      <div className="flex gap-2.5">
        {/* Avatar */}
        <div className="neon-glow flex h-8 w-8 flex-shrink-0 items-center justify-center rounded-lg border border-cyan-400/40 bg-[#0b1220]">
          <span className="text-[10px] font-bold neon-text">ST</span>
        </div>
        {/* Dots bubble */}
        <div className="flex items-center gap-2 rounded-xl rounded-tl-sm border border-slate-800 bg-slate-900/80 px-4 py-3 shadow-sm">
          <span className="typing-dot" />
          <span className="typing-dot" />
          <span className="typing-dot" />
        </div>
      </div>
    </div>
  )
}
