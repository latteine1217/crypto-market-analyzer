import type { Metadata } from 'next'
import { Inter } from 'next/font/google'
import './globals.css'
import { Navbar } from '@/components/Navbar'
import { Providers } from '@/components/Providers'
import { ErrorBoundary } from '@/components/ErrorBoundary'

const inter = Inter({ subsets: ['latin'] })

export const metadata: Metadata = {
  title: 'Crypto Market Dashboard',
  description: 'Real-time cryptocurrency market analysis and monitoring',
}

export default function RootLayout({
  children,
}: {
  children: React.ReactNode
}) {
  return (
    <html lang="en">
      <body className={`${inter.className} bg-background text-foreground min-h-screen`}>
        <Providers>
          <ErrorBoundary>
            <Navbar />
            <main className="container mx-auto px-4 py-6">
              {children}
            </main>
          </ErrorBoundary>
        </Providers>
      </body>
    </html>
  )
}
