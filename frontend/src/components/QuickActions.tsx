'use client';

import { useEffect, useState } from 'react';
import { useRouter } from 'next/navigation';

interface QuickAction {
  key: string;
  label: string;
  description: string;
  icon: string;
  href?: string;
  action?: () => void;
}

interface QuickActionsProps {
  show: boolean;
  onClose: () => void;
}

const actions: QuickAction[] = [
  { key: 'm', label: 'Meet Setup', description: 'Configure meet and upload rosters', icon: '📋', href: '/meet' },
  { key: 'o', label: 'Optimize', description: 'Run lineup optimization', icon: '⚡', href: '/optimize' },
  { key: 'r', label: 'Results', description: 'View optimization results', icon: '📊', href: '/results' },
  { key: 'a', label: 'Analytics', description: 'Review performance analytics', icon: '📈', href: '/analytics' },
  { key: 'h', label: 'Home', description: 'Return to dashboard', icon: '🏠', href: '/' },
];

export default function QuickActions({ show, onClose }: QuickActionsProps) {
  const router = useRouter();
  const [search, setSearch] = useState('');

  useEffect(() => {
    if (!show) return;
    
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') {
        onClose();
        return;
      }
      
      // Check for action shortcuts
      const action = actions.find(a => a.key === e.key.toLowerCase());
      if (action && action.href) {
        router.push(action.href);
        onClose();
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [show, onClose, router]);

  if (!show) return null;

  const filteredActions = search
    ? actions.filter(a => 
        a.label.toLowerCase().includes(search.toLowerCase()) ||
        a.description.toLowerCase().includes(search.toLowerCase())
      )
    : actions;

  return (
    <div 
      className="fixed inset-0 z-[100] flex items-start justify-center pt-[15vh] bg-black/60 backdrop-blur-sm animate-fade-in"
      onClick={onClose}
    >
      <div 
        className="w-full max-w-lg mx-4 glass-card overflow-hidden shadow-2xl animate-scale-in"
        onClick={e => e.stopPropagation()}
      >
        {/* Search Input */}
        <div className="p-4 border-b border-[var(--navy-500)]">
          <input
            type="text"
            placeholder="Search actions or press shortcut key..."
            value={search}
            onChange={e => setSearch(e.target.value)}
            autoFocus
            className="input w-full text-lg bg-transparent border-none focus:ring-0 placeholder:text-white/30"
          />
        </div>

        {/* Action List */}
        <div className="max-h-80 overflow-y-auto p-2">
          {filteredActions.map(action => (
            <button
              key={action.key}
              onClick={() => {
                if (action.href) router.push(action.href);
                if (action.action) action.action();
                onClose();
              }}
              className="w-full flex items-center gap-4 px-4 py-3 rounded-lg hover:bg-white/5 transition-colors text-left group"
            >
              <span className="text-2xl opacity-80 group-hover:opacity-100 transition-opacity">
                {action.icon}
              </span>
              <div className="flex-1">
                <p className="font-medium text-white group-hover:text-[var(--gold-400)] transition-colors">
                  {action.label}
                </p>
                <p className="text-sm text-white/50">{action.description}</p>
              </div>
              <kbd className="px-2 py-1 bg-[var(--navy-600)] rounded text-xs text-white/50 font-mono">
                {action.key.toUpperCase()}
              </kbd>
            </button>
          ))}
        </div>

        {/* Footer */}
        <div className="p-3 border-t border-[var(--navy-600)] flex items-center justify-between text-xs text-white/40">
          <span>Press shortcut key to navigate</span>
          <span>ESC to close</span>
        </div>
      </div>
    </div>
  );
}

// Hook for keyboard shortcut
export function useQuickActions() {
  const [showQuickActions, setShowQuickActions] = useState(false);

  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      // Cmd/Ctrl + K to open quick actions
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setShowQuickActions(true);
      }
    };

    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  return {
    showQuickActions,
    openQuickActions: () => setShowQuickActions(true),
    closeQuickActions: () => setShowQuickActions(false),
  };
}
