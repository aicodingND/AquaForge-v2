'use client';

/**
 * Skeleton loading components for professional loading states
 */

interface SkeletonProps {
    className?: string;
}

export function Skeleton({ className = '' }: SkeletonProps) {
    return (
        <div
            className={`animate-pulse bg-[#1a3a5c] rounded ${className}`}
        />
    );
}

export function TeamCardSkeleton() {
    return (
        <div className="rounded-xl border border-[#1a3a5c] bg-[#0C2340]/30 p-5">
            <div className="flex items-start justify-between mb-4">
                <div className="space-y-2">
                    <Skeleton className="h-3 w-16" />
                    <Skeleton className="h-5 w-32" />
                    <Skeleton className="h-3 w-24" />
                </div>
                <Skeleton className="h-5 w-5 rounded" />
            </div>

            <div className="grid grid-cols-2 gap-3 mb-4">
                <div className="bg-[#0C2340]/50 rounded-lg p-3">
                    <Skeleton className="h-6 w-12 mb-1" />
                    <Skeleton className="h-3 w-16" />
                </div>
                <div className="bg-[#0C2340]/50 rounded-lg p-3">
                    <Skeleton className="h-6 w-12 mb-1" />
                    <Skeleton className="h-3 w-16" />
                </div>
            </div>

            <div className="flex flex-wrap gap-1.5">
                {[1, 2, 3, 4].map((i) => (
                    <Skeleton key={i} className="h-5 w-16 rounded-full" />
                ))}
            </div>
        </div>
    );
}

export function ResultsTableSkeleton() {
    return (
        <div className="space-y-4">
            {/* Score Banner Skeleton */}
            <div className="rounded-xl bg-[#0C2340]/50 p-6">
                <Skeleton className="h-4 w-24 mx-auto mb-3" />
                <div className="flex items-center justify-center gap-4">
                    <div className="text-center">
                        <Skeleton className="h-8 w-12 mb-1" />
                        <Skeleton className="h-3 w-8" />
                    </div>
                    <Skeleton className="h-6 w-4" />
                    <div className="text-center">
                        <Skeleton className="h-8 w-12 mb-1" />
                        <Skeleton className="h-3 w-12" />
                    </div>
                </div>
            </div>

            {/* Table Skeleton */}
            <div className="glass-card rounded-xl overflow-hidden">
                <div className="bg-[#0C2340] px-4 py-3">
                    <div className="flex gap-4">
                        <Skeleton className="h-4 w-8" />
                        <Skeleton className="h-4 w-24" />
                        <Skeleton className="h-4 w-32" />
                        <Skeleton className="h-4 w-32" />
                        <Skeleton className="h-4 w-16" />
                    </div>
                </div>
                <div className="divide-y divide-[#1a3a5c]">
                    {[1, 2, 3, 4, 5].map((i) => (
                        <div key={i} className="px-4 py-3 flex gap-4">
                            <Skeleton className="h-4 w-8" />
                            <Skeleton className="h-4 w-24" />
                            <Skeleton className="h-4 w-32" />
                            <Skeleton className="h-4 w-32" />
                            <Skeleton className="h-4 w-16" />
                        </div>
                    ))}
                </div>
            </div>
        </div>
    );
}

export function FileUploadSkeleton() {
    return (
        <div className="space-y-2">
            <Skeleton className="h-4 w-24" />
            <div className="border-2 border-dashed border-[#1a3a5c] rounded-xl p-8">
                <div className="flex flex-col items-center gap-3">
                    <Skeleton className="h-10 w-10 rounded" />
                    <Skeleton className="h-4 w-40" />
                    <Skeleton className="h-3 w-24" />
                </div>
            </div>
        </div>
    );
}
