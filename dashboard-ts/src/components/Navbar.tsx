'use client'

import { useState } from 'react'
import Link from 'next/link'
import { usePathname } from 'next/navigation'
import { clsx } from 'clsx'

export function Navbar() {
  const pathname = usePathname()
  const [isMenuOpen, setIsMenuOpen] = useState(false)

  const links = [
    { href: '/', label: 'Home' },
    { href: '/technical', label: 'Technical' },
    { href: '/liquidity', label: 'Liquidity' },
    { href: '/onchain', label: 'On-Chain' },
  ]

  return (
    <nav className="border-b border-gray-800 bg-gray-900/50 backdrop-blur-sm sticky top-0 z-50">
      <div className="container mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link href="/" className="text-xl font-bold flex items-center gap-2" onClick={() => setIsMenuOpen(false)}>
            <span>Crypto Dashboard</span>
          </Link>

          {/* Desktop Menu */}
          <div className="hidden md:flex space-x-1">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                className={clsx(
                  'px-4 py-2 rounded-md transition-colors',
                  pathname === link.href
                    ? 'bg-primary text-white'
                    : 'text-gray-400 hover:text-white hover:bg-gray-800'
                )}
              >
                {link.label}
              </Link>
            ))}
          </div>

          {/* Mobile Menu Button */}
          <button 
            className="md:hidden p-2 text-gray-400 hover:text-white focus:outline-none"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
          >
            <svg className="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              {isMenuOpen ? (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              ) : (
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 6h16M4 12h16M4 18h16" />
              )}
            </svg>
          </button>
        </div>
      </div>

      {/* Mobile Menu Dropdown */}
      {isMenuOpen && (
        <div className="md:hidden border-t border-gray-800 bg-gray-900">
          <div className="px-2 pt-2 pb-3 space-y-1 sm:px-3">
            {links.map((link) => (
              <Link
                key={link.href}
                href={link.href}
                onClick={() => setIsMenuOpen(false)}
                className={clsx(
                  'block px-3 py-2 rounded-md text-base font-medium',
                  pathname === link.href
                    ? 'bg-primary text-white'
                    : 'text-gray-300 hover:text-white hover:bg-gray-700'
                )}
              >
                {link.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </nav>
  )
}
