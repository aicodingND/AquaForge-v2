/**
 * Loading Skeleton Components
 * Professional placeholder UI while data loads
 */

'use client';

export function TableSkeleton({ rows = 5 }: { rows?: number }) {
    return (
        <div className="space-y-2 animate-pulse">
            {[...Array(rows)].map((_, i) => (
                <div key={i} className="flex gap-4">
                    <div className="h-12 bg-navy-light/30 rounded flex-1" />
                    <div className="h-12 bg-navy-light/30 rounded w-32" />
                    <div className="h-12 bg-navy-light/30 rounded w-20" />
                </div>
            ))}
        </div>
    );
}

export function CardSkeleton() {
    return (
        <div className="bg-navy-darker rounded-xl p-6 border border-navy-light animate-pulse">
            <div className="h-6 bg-navy-light/30 rounded w-1/3 mb-4" />
            <div className="space-y-3">
                <div className="h-4 bg-navy-light/30 rounded" />
                <div className="h-4 bg-navy-light/30 rounded w-5/6" />
                <div className="h-4 bg-navy-light/30 rounded w-4/6" />
            </div>
        </div>
    );
}

export function ChartSkeleton() {
    return (
        <div className="bg-navy-darker rounded-xl p-6 border border-navy-light">
            <div className="h-6 bg-navy-light/30 rounded w-1/4 mb-6 animate-pulse" />
            <div className="h-64 bg-navy-light/10 rounded animate-pulse" />
        </div>
    );
}

export function HeaderSkeleton() {
    return (
        <div className="flex items-center justify-between p-6 animate-pulse">
            <div className="h-8 bg-navy-light/30 rounded w-48" />
            <div className="flex gap-3">
                <div className="h-10 bg-navy-light/30 rounded w-24" />
                <div className="h-10 bg-navy-light/30 rounded w-24" />
            </div>
        </div>
    );
}
