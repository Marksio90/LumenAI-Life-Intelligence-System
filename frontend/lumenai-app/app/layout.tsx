import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import ToastContainer from '@/components/ToastContainer'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'LumenAI - Your Life Intelligence Assistant',
  description: 'Personal AI assistant for life planning, emotional support, and daily productivity',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="pl">
      <body className={inter.className}>
        {children}
        <ToastContainer />
      </body>
    </html>
  )
}
