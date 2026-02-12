'use client';

import { useAppStore } from '@/lib/store';
import FileUpload from '@/components/FileUpload';
import TeamCard from '@/components/TeamCard';
import OptimizePanel from '@/components/OptimizePanel';
import ResultsTable from '@/components/ResultsTable';
import Header from '@/components/Header';
import TabNavigation from '@/components/layout/TabNavigation';
import ActivityLog from '@/components/ActivityLog';
import SwimmerAvailability from '@/components/SwimmerAvailability';
import LineupEditor from '@/components/LineupEditor';
import ComparisonView from '@/components/ComparisonView';
import ChampionshipUpload from '@/components/ChampionshipUpload';

/**
 * Single-page dashboard layout (ported from Windows).
 * Mac's primary UI uses Next.js page routing (/optimize, /results, etc.),
 * but this component provides an alternative tab-based single-page view.
 */
export default function DashboardContent() {
  const { activeTab, setonTeam, optimizationResults, meetMode } = useAppStore();

  return (
    <>
      <Header />
      <TabNavigation />

      <main className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
          <div className="lg:col-span-2 space-y-6">
            {activeTab === 'upload' && (
              <>
                <div className="mb-4">
                  <h2 className="text-2xl font-bold text-white mb-2">Upload Team Data</h2>
                  <p className="text-sm text-white/60">
                    Upload rosters for dual meets or championship meet files
                  </p>
                </div>

                {meetMode === 'championship' ? (
                  <>
                    <div className="bg-[#D4AF37]/10 border border-[#D4AF37]/20 rounded-xl p-4 mb-4">
                      <div className="flex items-start gap-2">
                        <svg className="w-5 h-5 text-[#D4AF37] flex-shrink-0 mt-0.5" fill="currentColor" viewBox="0 0 20 20">
                          <path fillRule="evenodd" d="M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z" clipRule="evenodd" />
                        </svg>
                        <div className="text-sm text-[#D4AF37]">
                          <span className="font-semibold">Championship Mode:</span> Upload a single file containing all teams. You&apos;ll select your team after upload.
                        </div>
                      </div>
                    </div>

                    <ChampionshipUpload />
                  </>
                ) : (
                  <>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <FileUpload teamType="seton" label="Seton Team File" />
                      <FileUpload teamType="opponent" label="Opponent Team File" />
                    </div>
                    <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                      <TeamCard teamType="seton" />
                      <TeamCard teamType="opponent" />
                    </div>
                    {setonTeam && <SwimmerAvailability />}
                  </>
                )}
              </>
            )}

            {activeTab === 'optimize' && (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="space-y-6">
                  <TeamCard teamType="seton" />
                  <TeamCard teamType="opponent" />
                </div>
                <OptimizePanel />
              </div>
            )}

            {activeTab === 'results' && (
              <div className="space-y-6">
                <ResultsTable />
                {optimizationResults && <LineupEditor />}
                {optimizationResults && <ComparisonView />}
              </div>
            )}
          </div>

          <div className="lg:col-span-1">
            <ActivityLog />
          </div>
        </div>
      </main>

      <footer className="border-t border-navy-light mt-12">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <p className="text-xs text-white/40 text-center">
            AquaForge &copy; 2026
          </p>
        </div>
      </footer>
    </>
  );
}
