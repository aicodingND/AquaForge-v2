'use client';

import Header from '@/components/Header';
import QuickActions, { useQuickActions } from '@/components/QuickActions';

interface AppShellProps {
  children: React.ReactNode;
}

export default function AppShell({ children }: AppShellProps) {
  const { showQuickActions, closeQuickActions } = useQuickActions();

  return (
    <div className="min-h-screen bg-[var(--navy-900)]">
      <Header />
      <main className="pt-20 pb-12 w-full max-w-7xl mx-auto px-4 lg:px-8">
        {children}
      </main>
      
      {/* Quick Actions Modal (Cmd+K) */}
      <QuickActions show={showQuickActions} onClose={closeQuickActions} />
      
      {/* Keyboard shortcut hint */}
      <div className="fixed bottom-4 right-4 hidden lg:flex items-center gap-2 text-xs text-white/30">
        <kbd className="px-2 py-1 bg-[var(--navy-700)] rounded border border-[var(--navy-600)]">⌘K</kbd>
        <span>Quick actions</span>
      </div>
    </div>
  );
}
