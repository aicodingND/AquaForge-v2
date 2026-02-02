'use client';

import { ReactNode } from 'react';

interface ErrorContext {
  code: string;
  message: string;
  suggestion?: string;
  recovery?: {
    action: string;
    label: string;
  };
}

interface ErrorDisplayProps {
  error: string | null;
  context?: ErrorContext;
  onDismiss?: () => void;
  className?: string;
}

export function getErrorContext(error: string | Error | null): ErrorContext | null {
  if (!error) return null;

  const errorStr = error instanceof Error ? error.message : error;
  const errorLower = errorStr.toLowerCase();

  // File format errors
  if (errorLower.includes('file type') || errorLower.includes('format')) {
    return {
      code: 'INVALID_FORMAT',
      message: 'Unsupported file format',
      suggestion: 'AquaForge supports Excel (.xlsx), CSV, and JSON files for swimmer data.',
      recovery: {
        action: 'convert',
        label: 'How to convert your file'
      }
    };
  }

  // File size errors
  if (errorLower.includes('too large') || errorLower.includes('size')) {
    return {
      code: 'FILE_TOO_LARGE',
      message: 'File is too large',
      suggestion: 'Maximum file size is 10MB. Consider splitting large rosters into smaller files.',
      recovery: {
        action: 'split',
        label: 'Split large file'
      }
    };
  }

  // Network errors
  if (errorLower.includes('network') || errorLower.includes('connection') || errorLower.includes('timeout')) {
    return {
      code: 'NETWORK_ERROR',
      message: 'Connection problem',
      suggestion: 'Check your internet connection and try again. Large files may take longer to upload.',
      recovery: {
        action: 'retry',
        label: 'Try uploading again'
      }
    };
  }

  // Parsing errors
  if (errorLower.includes('parse') || errorLower.includes('invalid') || errorLower.includes('format')) {
    return {
      code: 'PARSE_ERROR',
      message: 'Could not read file data',
      suggestion: 'Make sure your file has the correct columns: Swimmer Name, Event, Time, and optional Grade.',
      recovery: {
        action: 'template',
        label: 'Download template'
      }
    };
  }

  // Generic upload errors
  if (errorLower.includes('upload') || errorLower.includes('failed')) {
    return {
      code: 'UPLOAD_FAILED',
      message: 'Upload could not be completed',
      suggestion: 'This might be a temporary issue. Please try again or contact support if the problem persists.',
      recovery: {
        action: 'retry',
        label: 'Try again'
      }
    };
  }

  // Fallback
  return {
    code: 'UNKNOWN_ERROR',
    message: errorStr,
    suggestion: 'Something went wrong. Please try again or contact support if this continues.',
    recovery: {
      action: 'retry',
      label: 'Try again'
    }
  };
}

export default function ErrorDisplay({ error, context, onDismiss, className = '' }: ErrorDisplayProps) {
  const errorContext = context || getErrorContext(error);

  if (!errorContext) return null;

  const getErrorIcon = () => {
    switch (errorContext.code) {
      case 'INVALID_FORMAT':
        return '📄';
      case 'FILE_TOO_LARGE':
        return '📏';
      case 'NETWORK_ERROR':
        return '🌐';
      case 'PARSE_ERROR':
        return '🔍';
      default:
        return '⚠️';
    }
  };

  const getErrorColor = () => {
    switch (errorContext.code) {
      case 'NETWORK_ERROR':
        return 'text-orange-400 border-orange-400/20 bg-orange-500/10';
      case 'PARSE_ERROR':
        return 'text-yellow-400 border-yellow-400/20 bg-yellow-500/10';
      default:
        return 'text-red-400 border-red-400/20 bg-red-500/10';
    }
  };

  const handleRecovery = () => {
    switch (errorContext.recovery?.action) {
      case 'convert':
        window.open('https://support.aquaforge.ai/hc/en-us/articles/360020123400-Convert-your-files-to-supported-formats', '_blank');
        break;
      case 'split':
        // Open file split modal or provide instructions
        alert('To split a large file:\n1. Open your file in Excel\n2. Copy half the rows to a new sheet\n3. Save both files separately\n4. Upload them one at a time');
        break;
      case 'template':
        // Download template file
        const link = document.createElement('a');
        link.href = '/templates/swimmer-template.xlsx';
        link.download = 'aquaforge-template.xlsx';
        link.click();
        break;
      case 'retry':
        onDismiss?.(); // Clear error to allow retry
        break;
      default:
        break;
    }
  };

  return (
    <div className={`mt-3 p-4 rounded-lg border ${getErrorColor()} ${className}`}>
      <div className="flex items-start gap-3">
        {/* Error Icon */}
        <span className="text-lg flex-shrink-0 mt-0.5">
          {getErrorIcon()}
        </span>

        {/* Error Content */}
        <div className="flex-1 min-w-0">
          {/* Error Title */}
          <h4 className="font-semibold text-sm mb-1">
            {errorContext.message}
          </h4>

          {/* Error Description */}
          <p className="text-xs opacity-90 mb-3 leading-relaxed">
            {errorContext.suggestion}
          </p>

          {/* Recovery Action */}
          {errorContext.recovery && (
            <div className="flex items-center gap-2 flex-wrap">
              <button
                onClick={handleRecovery}
                className="inline-flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium bg-white/10 hover:bg-white/20 rounded-md transition-colors border border-white/20"
              >
                {errorContext.recovery.action === 'retry' && '🔄'}
                {errorContext.recovery.action === 'convert' && '📚'}
                {errorContext.recovery.action === 'split' && '✂️'}
                {errorContext.recovery.action === 'template' && '📋'}
                {errorContext.recovery.label}
              </button>

              {/* Additional help link */}
              <button
                onClick={() => window.open('https://support.aquaforge.ai', '_blank')}
                className="text-xs opacity-70 hover:opacity-100 transition-opacity underline"
              >
                Need more help?
              </button>
            </div>
          )}

          {/* Error Code (for debugging) */}
          <div className="mt-2 text-xs opacity-50 font-mono">
            Code: {errorContext.code}
          </div>
        </div>

        {/* Dismiss Button */}
        {onDismiss && (
          <button
            onClick={onDismiss}
            className="flex-shrink-0 p-1 rounded hover:bg-white/10 transition-colors opacity-60 hover:opacity-100"
            aria-label="Dismiss error"
          >
            <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clipRule="evenodd" />
            </svg>
          </button>
        )}
      </div>
    </div>
  );
}
