/**
 * Toggle Switch Component
 *
 * Reusable toggle switch with consistent styling.
 */

interface ToggleProps {
  enabled: boolean;
  onChange: (enabled: boolean) => void;
  label?: string;
  description?: string;
  disabled?: boolean;
  size?: "sm" | "md";
}

export default function Toggle({
  enabled,
  onChange,
  label,
  description,
  disabled = false,
  size = "md",
}: ToggleProps) {
  const sizeClasses = {
    sm: { track: "w-10 h-5", thumb: "w-4 h-4", translate: "translate-x-5" },
    md: { track: "w-12 h-6", thumb: "w-5 h-5", translate: "translate-x-6" },
  };

  const { track, thumb, translate } = sizeClasses[size];

  return (
    <div className="flex items-center justify-between">
      {(label || description) && (
        <div>
          {label && <p className="text-white font-medium text-sm">{label}</p>}
          {description && (
            <p className="text-xs text-white/40">{description}</p>
          )}
        </div>
      )}
      <button
        type="button"
        onClick={() => !disabled && onChange(!enabled)}
        disabled={disabled}
        aria-label={label ? `Toggle ${label}` : "Toggle switch"}
        title={label ? `Toggle ${label}` : "Toggle switch"}
        className={`${track} rounded-full transition-colors ${
          enabled ? "bg-(--gold-500)" : "bg-(--navy-500)"
        } ${disabled ? "opacity-50 cursor-not-allowed" : "cursor-pointer"}`}
      >
        <div
          className={`${thumb} rounded-full bg-white shadow-md transform transition-transform ${
            enabled ? translate : "translate-x-0.5"
          }`}
        />
      </button>
    </div>
  );
}
