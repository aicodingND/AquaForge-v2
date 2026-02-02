"use client";

import { create } from "zustand";
import { useEffect, useCallback } from "react";

interface Toast {
  id: string;
  type: "success" | "error" | "warning" | "info";
  message: string;
  duration?: number;
}

interface ToastStore {
  toasts: Toast[];
  addToast: (toast: Omit<Toast, "id">) => void;
  removeToast: (id: string) => void;
}

const useToastStore = create<ToastStore>((set) => ({
  toasts: [],
  addToast: (toast) => {
    const id = Math.random().toString(36).substring(2, 9);
    set((state) => ({
      toasts: [...state.toasts.slice(-2), { ...toast, id }], // Keep max 3 toasts
    }));
  },
  removeToast: (id) => {
    set((state) => ({
      toasts: state.toasts.filter((toast) => toast.id !== id),
    }));
  },
}));

const toastIcons = {
  success: "✓",
  error: "✕",
  warning: "⚠",
  info: "ℹ",
};

const toastStyles = {
  success: {
    bg: "rgba(16, 185, 129, 0.15)",
    border: "var(--success)",
    color: "var(--success)",
  },
  error: {
    bg: "rgba(239, 68, 68, 0.15)",
    border: "var(--error)",
    color: "var(--error)",
  },
  warning: {
    bg: "rgba(245, 158, 11, 0.15)",
    border: "var(--warning)",
    color: "var(--warning)",
  },
  info: {
    bg: "rgba(59, 130, 246, 0.15)",
    border: "var(--info)",
    color: "var(--info)",
  },
};

interface ToastItemProps {
  toast: Toast;
  onClose: (id: string) => void;
}

function ToastItem({ toast, onClose }: ToastItemProps) {
  const style = toastStyles[toast.type];

  useEffect(() => {
    const duration = toast.duration ?? 5000;
    const timer = setTimeout(() => {
      onClose(toast.id);
    }, duration);

    return () => clearTimeout(timer);
  }, [toast.id, toast.duration, onClose]);

  return (
    <div
      role="alert"
      aria-live="polite"
      className="toast-item"
      style={{
        display: "flex",
        alignItems: "center",
        gap: "0.75rem",
        padding: "1rem 1.25rem",
        minWidth: "320px",
        maxWidth: "480px",
        background: style.bg,
        border: `1px solid ${style.border}`,
        borderRadius: "var(--radius-md)",
        boxShadow: "var(--shadow-lg)",
        backdropFilter: "blur(12px)",
        animation: "slideInFromRight 0.3s cubic-bezier(0.34, 1.56, 0.64, 1)",
        marginBottom: "0.75rem",
      }}
    >
      {/* Icon */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: "24px",
          height: "24px",
          borderRadius: "50%",
          background: style.color,
          color: "var(--navy-900)",
          fontSize: "0.875rem",
          fontWeight: "bold",
          flexShrink: 0,
        }}
      >
        {toastIcons[toast.type]}
      </div>

      {/* Message */}
      <div
        style={{
          flex: 1,
          color: "rgba(255, 255, 255, 0.95)",
          fontSize: "0.875rem",
          lineHeight: "1.5",
        }}
      >
        {toast.message}
      </div>

      {/* Close button */}
      <button
        onClick={() => onClose(toast.id)}
        aria-label="Close notification"
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          width: "20px",
          height: "20px",
          padding: 0,
          background: "transparent",
          border: "none",
          color: "rgba(255, 255, 255, 0.5)",
          cursor: "pointer",
          fontSize: "1.125rem",
          lineHeight: 1,
          transition: "color var(--transition-fast)",
          flexShrink: 0,
        }}
        onMouseEnter={(e) => {
          e.currentTarget.style.color = "rgba(255, 255, 255, 0.9)";
        }}
        onMouseLeave={(e) => {
          e.currentTarget.style.color = "rgba(255, 255, 255, 0.5)";
        }}
      >
        ×
      </button>

      <style jsx>{`
        @keyframes slideInFromRight {
          from {
            opacity: 0;
            transform: translateX(100%);
          }
          to {
            opacity: 1;
            transform: translateX(0);
          }
        }
      `}</style>
    </div>
  );
}

export function ToastContainer() {
  const { toasts, removeToast } = useToastStore();

  return (
    <div
      aria-label="Notifications"
      style={{
        position: "fixed",
        bottom: "1.5rem",
        right: "1.5rem",
        zIndex: 9999,
        display: "flex",
        flexDirection: "column",
        alignItems: "flex-end",
        pointerEvents: "none",
      }}
    >
      <div
        style={{
          pointerEvents: "auto",
        }}
      >
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onClose={removeToast} />
        ))}
      </div>
    </div>
  );
}

export function useToast() {
  const { addToast } = useToastStore();

  const toast = {
    success: useCallback(
      (message: string, duration?: number) => {
        addToast({ type: "success", message, duration });
      },
      [addToast]
    ),
    error: useCallback(
      (message: string, duration?: number) => {
        addToast({ type: "error", message, duration });
      },
      [addToast]
    ),
    warning: useCallback(
      (message: string, duration?: number) => {
        addToast({ type: "warning", message, duration });
      },
      [addToast]
    ),
    info: useCallback(
      (message: string, duration?: number) => {
        addToast({ type: "info", message, duration });
      },
      [addToast]
    ),
  };

  return { toast };
}
