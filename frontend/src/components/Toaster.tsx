'use client';

import { Toaster as SonnerToaster } from 'sonner'; // TODO: port dependency — requires `sonner` package (added to package.json)

/**
 * Toast notification provider component.
 * Renders toast notifications in the bottom-right corner.
 */
export function Toaster() {
    return (
        <SonnerToaster
            position="bottom-right"
            toastOptions={{
                style: {
                    background: '#0C2340',
                    border: '1px solid #1a3a5c',
                    color: '#fff',
                },
                classNames: {
                    success: 'border-green-500/50',
                    error: 'border-red-500/50',
                    warning: 'border-yellow-500/50',
                    info: 'border-blue-500/50',
                },
            }}
            theme="dark"
            richColors
            closeButton
        />
    );
}
