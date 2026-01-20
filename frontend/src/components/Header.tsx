'use client';

import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useAppStore } from '@/lib/store';
import { mainNavigation, secondaryNavigation } from '@/config/navigation';
import { siteConfig, meetModes } from '@/config/site';
import { useState } from 'react';

export default function Header() {
  const pathname = usePathname();
  const { meetMode, setMeetMode } = useAppStore();
  const [isMobileMenuOpen, setIsMobileMenuOpen] = useState(false);

  return (
    <header className="fixed top-0 left-0 right-0 z-50 glass-card border-b border-[var(--navy-600)] backdrop-blur-md bg-[var(--navy-900)]/80 h-16">
      <div className="h-full px-4 lg:px-8 flex items-center justify-between">
        {/* Left: Logo & Brand */}
        <div className="flex items-center gap-8">
          <Link href="/" className="flex items-center gap-3 hover:opacity-90 transition-opacity">
            <div className="w-9 h-9 rounded-lg bg-gradient-to-br from-[var(--gold-400)] to-[var(--gold-500)] flex items-center justify-center font-bold text-[var(--navy-900)] text-lg shadow-lg shadow-[var(--gold-500)]/20">
              {siteConfig.name[0]}
            </div>
            <div className="hidden md:block">
              <h1 className="text-lg font-bold text-white tracking-tight">{siteConfig.name}</h1>
              <p className="text-[10px] text-[var(--gold-500)] font-medium tracking-wider uppercase">Optimizer</p>
            </div>
          </Link>

          {/* Desktop Navigation */}
          <nav className="hidden md:flex items-center gap-1">
            {mainNavigation.map((item) => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.id}
                  href={item.href}
                  className={`relative px-4 py-2 rounded-full text-sm font-medium transition-all duration-300 ${
                    isActive
                      ? 'text-white bg-white/10 shadow-inner'
                      : 'text-white/60 hover:text-white hover:bg-white/5'
                  }`}
                >
                  <span className="flex items-center gap-2">
                    <span className="opacity-80">{item.icon}</span>
                    {item.label}
                  </span>
                  {isActive && (
                    <span className="absolute bottom-0 left-1/2 -translate-x-1/2 w-1 h-1 rounded-full bg-[var(--gold-400)] translate-y-2" />
                  )}
                </Link>
              );
            })}
          </nav>
        </div>

        {/* Right: Mode Switcher & Settings */}
        <div className="flex items-center gap-4">
          {/* Mode Switcher - Visible on desktop/tablet */}
          <div className="hidden md:flex bg-[var(--navy-800)] rounded-full p-1 border border-[var(--navy-600)]">
             {meetModes.map((mode) => (
               <button
                 key={mode.id}
                 data-testid={`mode-${mode.id}`}
                 onClick={() => setMeetMode(mode.id)}
                 className={`px-4 py-1.5 rounded-full text-xs font-semibold transition-all duration-300 ${
                   meetMode === mode.id
                     ? 'bg-[var(--gold-500)] text-[var(--navy-900)] shadow-sm'
                     : 'text-white/50 hover:text-white'
                 }`}
               >
                 {mode.label}
               </button>
             ))}
          </div>

          <div className="h-6 w-px bg-[var(--navy-600)] hidden lg:block" />

          {/* Secondary Actions */}
          <Link 
            href="/settings" 
            className={`p-2 rounded-full transition-colors ${
              pathname === '/settings' ? 'bg-white/10 text-white' : 'text-white/60 hover:text-white hover:bg-white/5'
            }`}
          >
            ⚙️
          </Link>

          {/* Mobile Menu Toggle */}
          <button 
            className="md:hidden p-2 text-white/80"
            onClick={() => setIsMobileMenuOpen(!isMobileMenuOpen)}
          >
            ☰
          </button>
        </div>
      </div>

      {/* Mobile Menu */}
      {isMobileMenuOpen && (
        <div className="md:hidden absolute top-16 left-0 right-0 bg-[var(--navy-900)] border-b border-[var(--navy-600)] p-4 animate-fade-in shadow-xl">
           <div className="mb-4">
             <p className="text-xs text-white/50 uppercase tracking-wider mb-2 font-semibold">Meet Mode</p>
             <div className="bg-[var(--navy-800)] rounded-lg p-1 flex">
               {meetModes.map((mode) => (
                 <button
                   key={mode.id}
                   onClick={() => setMeetMode(mode.id)}
                 className={`flex-1 py-2 rounded-md text-xs font-semibold transition-all ${
                   meetMode === mode.id
                     ? 'bg-[var(--gold-500)] text-[var(--navy-900)]'
                     : 'text-white/50'
                 }`}
               >
                 {mode.label}
               </button>
             ))}
           </div>
        </div>
          <div className="space-y-1">
            {[...mainNavigation, ...secondaryNavigation].map((item) => (
              <Link
                key={item.id}
                href={item.href}
                onClick={() => setIsMobileMenuOpen(false)}
                className={`flex items-center gap-3 px-4 py-3 rounded-lg text-sm font-medium ${
                  pathname === item.href
                    ? 'bg-white/10 text-white'
                    : 'text-white/60 hover:bg-white/5'
                }`}
              >
                <span>{item.icon}</span>
                {item.label}
              </Link>
            ))}
          </div>
        </div>
      )}
    </header>
  );
}
