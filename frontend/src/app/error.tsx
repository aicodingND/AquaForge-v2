"use client";

import { useEffect } from "react";
import Link from "next/link";

interface ErrorProps {
  error: Error & { digest?: string };
  reset: () => void;
}

export default function Error({ error, reset }: ErrorProps) {
  useEffect(() => {
    console.error("Error boundary caught:", error);
  }, [error]);

  return (
    <div className="min-h-screen bg-[var(--navy-900)] flex items-center justify-center p-4">
      <div className="glass-card max-w-md w-full p-8 text-center space-y-6">
        <div className="space-y-2">
          <div className="text-6xl">⚠️</div>
          <h1 className="text-2xl font-bold text-[var(--gold-600)]">
            Something Went Wrong
          </h1>
        </div>

        <div className="bg-[var(--navy-800)] border border-[var(--error)] rounded-lg p-4">
          <p className="text-sm text-[var(--error)] font-mono break-words">
            {error.message || "An unexpected error occurred"}
          </p>
        </div>

        <div className="flex flex-col gap-3">
          <button
            onClick={reset}
            className="w-full px-6 py-3 bg-[var(--gold-600)] hover:bg-[var(--gold-500)] text-[var(--navy-900)] font-semibold rounded-lg transition-colors"
          >
            Try Again
          </button>

          <Link
            href="/"
            className="w-full px-6 py-3 bg-[var(--navy-700)] hover:bg-[var(--navy-600)] text-[var(--gold-400)] font-semibold rounded-lg transition-colors inline-block"
          >
            Go Home
          </Link>
        </div>
      </div>
    </div>
  );
}
