"use client";

import { usePathname } from "next/navigation";
import { useAppStore } from "@/lib/store";
import { mainNavigation } from "@/config/navigation";

interface WorkflowStep {
  id: string;
  label: string;
  href: string;
  completed: boolean;
  current: boolean;
}

export default function WorkflowBreadcrumbs() {
  const pathname = usePathname();
  const { setonTeam, opponentTeam, optimizationResults, meetMode } =
    useAppStore();

  // Define workflow steps based on mode
  const getWorkflowSteps = (): WorkflowStep[] => {
    if (meetMode === "dual") {
      const hasSeton = setonTeam?.data && setonTeam.data.length > 0;
      const hasOpponent = opponentTeam?.data && opponentTeam.data.length > 0;
      const hasResults = optimizationResults != null && optimizationResults.length > 0;

      return [
        {
          id: "upload",
          label: "Upload Teams",
          href: "/meet",
          completed: !!(hasSeton && hasOpponent),
          current: pathname === "/meet",
        },
        {
          id: "optimize",
          label: "Optimize",
          href: "/optimize",
          completed: hasResults,
          current: pathname === "/optimize",
        },
        {
          id: "results",
          label: "View Results",
          href: "/results",
          completed: false, // Results are never "completed" - they're the final step
          current: pathname === "/results",
        },
      ];
    } else {
      // Championship mode workflow
      const hasPsychSheet = setonTeam?.data && setonTeam.data.length > 0;
      const hasResults = optimizationResults != null && optimizationResults.length > 0;

      return [
        {
          id: "upload",
          label: "Upload Psych Sheet",
          href: "/meet",
          completed: !!hasPsychSheet,
          current: pathname === "/meet",
        },
        {
          id: "optimize",
          label: "Championship Strategy",
          href: "/optimize",
          completed: hasResults,
          current: pathname === "/optimize",
        },
        {
          id: "results",
          label: "Analytics",
          href: "/results",
          completed: false,
          current: pathname === "/results",
        },
      ];
    }
  };

  const steps = getWorkflowSteps();
  const currentStepIndex = steps.findIndex((step) => step.current);

  // Don't show breadcrumbs on dashboard or unrelated pages
  if (
    pathname === "/" ||
    !steps.some((step) => step.current || pathname.startsWith(step.href))
  ) {
    return null;
  }

  return (
    <div className="bg-[var(--navy-800)]/50 border-b border-[var(--navy-600)] px-4 py-3">
      <div className="max-w-7xl mx-auto">
        {/* Mode Badge */}
        <div className="flex items-center gap-3 mb-3">
          <div
            className={`inline-flex items-center gap-2 px-3 py-1 rounded-full text-xs font-semibold ${
              meetMode === "dual"
                ? "bg-blue-500/20 text-blue-300 border border-blue-400/30"
                : "bg-purple-500/20 text-purple-300 border border-purple-400/30"
            }`}
          >
            <span className="w-2 h-2 rounded-full bg-current animate-pulse" />
            {meetMode === "dual" ? "DUAL MEET" : "CHAMPIONSHIP"}
          </div>
          <span className="text-xs text-white/50 font-medium uppercase tracking-wider">
            Workflow Progress
          </span>
        </div>

        {/* Progress Steps */}
        <div className="flex items-center gap-4 flex-wrap">
          {steps.map((step, index) => {
            const isPast = index < currentStepIndex;
            const isCurrent = step.current;
            const isFuture = index > currentStepIndex;

            return (
              <div key={step.id} className="flex items-center gap-3">
                {/* Step */}
                <div className="flex items-center gap-2">
                  {/* Step Circle */}
                  <div
                    className={`
                    w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold
                    transition-all duration-300 border-2
                    ${
                      isCurrent
                        ? "bg-[var(--gold-500)] text-[var(--navy-900)] border-[var(--gold-500)] shadow-lg shadow-[var(--gold-500)]/30"
                        : step.completed
                          ? "bg-green-500/20 text-green-300 border-green-400/50"
                          : "bg-[var(--navy-700)] text-white/40 border-[var(--navy-600)]"
                    }
                  `}
                  >
                    {step.completed ? (
                      <svg
                        className="w-4 h-4"
                        fill="currentColor"
                        viewBox="0 0 20 20"
                      >
                        <path
                          fillRule="evenodd"
                          d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z"
                          clipRule="evenodd"
                        />
                      </svg>
                    ) : (
                      <span>{index + 1}</span>
                    )}
                  </div>

                  {/* Step Label */}
                  <div className="flex flex-col gap-0.5">
                    <div
                      className={`
                      text-sm font-medium transition-colors duration-300
                      ${
                        isCurrent
                          ? "text-white"
                          : step.completed
                            ? "text-green-300"
                            : "text-white/50"
                      }
                    `}
                    >
                      {step.label}
                    </div>

                    {/* Step Status */}
                    <div className="text-xs">
                      {isCurrent && (
                        <span className="text-[var(--gold-500)] font-medium">
                          Current Step
                        </span>
                      )}
                      {isPast && step.completed && (
                        <span className="text-green-400">Completed</span>
                      )}
                      {isFuture && (
                        <span className="text-white/40">Waiting</span>
                      )}
                    </div>
                  </div>
                </div>

                {/* Connector Line */}
                {index < steps.length - 1 && (
                  <div
                    className={`
                    w-8 h-0.5 transition-colors duration-300
                    ${step.completed ? "bg-green-400/50" : "bg-[var(--navy-600)]"}
                  `}
                  />
                )}
              </div>
            );
          })}
        </div>

        {/* Progress Bar */}
        <div className="mt-4">
          <div className="w-full h-1 bg-[var(--navy-700)] rounded-full overflow-hidden">
            <div
              className="h-full bg-gradient-to-r from-[var(--gold-500)] to-[var(--gold-400)] transition-all duration-500 rounded-full"
              style={{
                width: `${((currentStepIndex + 1) / steps.length) * 100}%`,
              }}
            />
          </div>
          <div className="mt-1 text-xs text-white/50 text-right">
            Step {currentStepIndex + 1} of {steps.length}
          </div>
        </div>

        {/* Quick Tips */}
        {currentStepIndex === 0 &&
          (!setonTeam?.data || !opponentTeam?.data) && (
            <div className="mt-3 p-2 bg-[var(--gold-500)]/10 border border-[var(--gold-500)]/20 rounded-lg">
              <p className="text-xs text-[var(--gold-300)]">
                💡 Upload your team rosters to get started. Supported formats:
                Excel (.xlsx), CSV, or JSON
              </p>
            </div>
          )}

        {currentStepIndex === 1 &&
          setonTeam?.data &&
          opponentTeam?.data &&
          !optimizationResults && (
            <div className="mt-3 p-2 bg-blue-500/10 border border-blue-400/20 rounded-lg">
              <p className="text-xs text-blue-300">
                🚀 Both teams loaded! Configure your optimization settings and
                click &quot;Run Optimization&quot;
              </p>
            </div>
          )}
      </div>
    </div>
  );
}
