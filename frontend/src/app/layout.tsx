import type { Metadata } from 'next'
import './globals.css'

export const metadata: Metadata = {
  title: 'SDIT Tech-Bot — Campus Intelligence',
  description: 'AI-powered campus assistant for Shree Devi Institute of Technology, Mangaluru. Get instant answers about admissions, departments, facilities, placements, and more.',
  keywords: 'SDIT, Shree Devi Institute of Technology, Mangaluru, chatbot, campus assistant, AI',
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link href="https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap" rel="stylesheet" />
      </head>
      <body className="font-sans antialiased">{children}</body>
    </html>
  )
}
