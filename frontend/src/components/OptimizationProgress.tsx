/**
 * Animated Progress Component for Optimization Streaming
 *
 * Displays real-time progress with stage indicators and animations
 */

'use client';

import { motion } from 'framer-motion'; // TODO: port dependency — requires `framer-motion` package (added to package.json)

interface Props {
    stage: string;
    progress: number;
    message: string;
    details?: string;
    currentIter?: number;
    maxIters?: number;
    onCancel?: () => void;
}

const stageColors = {
    idle: 'from-gray-500 to-gray-400',
    init: 'from-blue-500 to-blue-400',
    validate: 'from-purple-500 to-purple-400',
    optimizing: 'from-gold-accent to-yellow-400',
    finalizing: 'from-green-500 to-green-400',
    complete: 'from-green-600 to-green-500',
    error: 'from-red-500 to-red-400',
};

const stageIcons = {
    idle: '⏸️',
    init: '🚀',
    validate: '✅',
    optimizing: '⚡',
    finalizing: '🎯',
    complete: '✨',
    error: '❌',
};

export function OptimizationProgress({
    stage,
    progress,
    message,
    details,
    currentIter,
    maxIters,
    onCancel
}: Props) {
    if (stage === 'idle') return null;

    const stageKey = stage as keyof typeof stageColors;

    return (
        <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -20 }}
            className="bg-navy-darker/90 backdrop-blur-sm rounded-xl p-6 border border-navy-light"
        >
            <div className="flex items-center justify-between mb-4">
                <div className="flex items-center gap-3">
                    <span className="text-2xl">{stageIcons[stageKey] || '⚙️'}</span>
                    <div>
                        <h3 className="text-white font-semibold text-lg">{message}</h3>
                        {details && (
                            <p className="text-white/60 text-sm mt-1">{details}</p>
                        )}
                        {currentIter !== undefined && maxIters && (
                            <p className="text-white/40 text-xs mt-1">
                                Iteration {currentIter.toLocaleString()} / {maxIters.toLocaleString()}
                            </p>
                        )}
                    </div>
                </div>
                {stage !== 'complete' && stage !== 'error' && onCancel && (
                    <button
                        onClick={onCancel}
                        className="text-white/60 hover:text-white text-sm px-3 py-1 rounded hover:bg-white/10 transition"
                    >
                        Cancel
                    </button>
                )}
            </div>

            {/* Progress Bar */}
            <div className="relative h-3 bg-navy-light rounded-full overflow-hidden">
                <motion.div
                    className={`absolute inset-y-0 left-0 bg-gradient-to-r ${stageColors[stageKey]}`}
                    initial={{ width: 0 }}
                    animate={{ width: `${progress}%` }}
                    transition={{ duration: 0.3, ease: 'easeOut' }}
                />

                {/* Shimmer effect for active progress */}
                {stage !== 'complete' && stage !== 'error' && (
                    <motion.div
                        className="absolute inset-0 bg-gradient-to-r from-transparent via-white/20 to-transparent"
                        animate={{ x: ['-100%', '200%'] }}
                        transition={{ repeat: Infinity, duration: 1.5, ease: 'linear' }}
                    />
                )}
            </div>

            <div className="flex justify-between mt-2 text-sm text-white/60">
                <span className="capitalize">{stage.replace('_', ' ')}</span>
                <span>{progress}%</span>
            </div>

            {/* Success message */}
            {stage === 'complete' && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="mt-4 p-3 bg-green-500/10 border border-green-500/30 rounded-lg"
                >
                    <p className="text-green-400 text-sm font-medium">
                        🎉 Optimization completed successfully!
                    </p>
                </motion.div>
            )}

            {/* Error message */}
            {stage === 'error' && (
                <motion.div
                    initial={{ opacity: 0, scale: 0.95 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="mt-4 p-3 bg-red-500/10 border border-red-500/30 rounded-lg"
                >
                    <p className="text-red-400 text-sm font-medium">
                        {message}
                    </p>
                </motion.div>
            )}
        </motion.div>
    );
}
