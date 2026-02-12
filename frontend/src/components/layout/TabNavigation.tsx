'use client';

import { useAppStore } from '@/lib/store';

/**
 * Tab navigation for single-page dashboard layout (ported from Windows).
 * Mac's primary UI uses Next.js page routing instead, but this component
 * is used by DashboardContent for an alternative single-page view.
 */
export default function TabNavigation() {
    const { activeTab, setActiveTab } = useAppStore();

    const tabs: { id: typeof activeTab; label: string; icon: string }[] = [
        { id: 'upload', label: 'Upload', icon: '\u{1F4C1}' },
        { id: 'optimize', label: 'Optimize', icon: '\u{26A1}' },
        { id: 'results', label: 'Results', icon: '\u{1F4CA}' },
    ];

    return (
        <nav className="border-b border-navy-light bg-navy-primary/50">
            <div className="max-w-6xl mx-auto px-6">
                <div className="flex gap-1">
                    {tabs.map((tab) => (
                        <button
                            key={tab.id}
                            onClick={() => setActiveTab(tab.id)}
                            className={`
                                px-6 py-3 text-sm font-medium transition-all relative
                                ${activeTab === tab.id
                                    ? 'text-gold-highlight'
                                    : 'text-white/50 hover:text-white/80'
                                }
                            `}
                        >
                            <span className="mr-2">{tab.icon}</span>
                            {tab.label}
                            {activeTab === tab.id && (
                                <div className="absolute bottom-0 left-0 right-0 h-0.5 bg-gold-primary" />
                            )}
                        </button>
                    ))}
                </div>
            </div>
        </nav>
    );
}
