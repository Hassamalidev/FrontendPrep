/**
 * The shared UI primitives.
 *
 * Small on purpose: this app is mostly reading, choosing and timed writing, so
 * the primitive set is a button, a card, a field, and the three states every
 * data screen has (loading / error / empty). Anything used once lives with its
 * page instead.
 */

import type { ButtonHTMLAttributes, InputHTMLAttributes, ReactNode, TextareaHTMLAttributes } from "react";

import { Alert as AlertIcon, Info, Spinner } from "@/components/icons";

// --- Button ---------------------------------------------------------------

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: "primary" | "secondary" | "ghost" | "danger" | "inverse" | "outline";
  size?: "sm" | "md" | "lg";
  loading?: boolean;
};

const BUTTON_VARIANTS: Record<string, string> = {
  primary: "bg-army-500 text-white hover:bg-army-600 disabled:bg-ink-300",
  secondary: "bg-white text-ink-800 ring-1 ring-ink-200 hover:bg-ink-50 disabled:text-ink-500",
  ghost: "text-ink-600 hover:bg-ink-100 hover:text-ink-800",
  danger: "bg-danger-500 text-white hover:brightness-110",
  // For dark surfaces such as the hero. Passing colour overrides through
  // `className` does not work: Tailwind resolves conflicting utilities by their
  // order in the stylesheet, not in the attribute, so `text-white` from the
  // primary variant silently won and the label rendered white-on-white.
  inverse: "bg-white text-army-600 hover:bg-ink-100",
  outline: "text-white ring-1 ring-white/50 hover:bg-white/10",
};

const BUTTON_SIZES: Record<string, string> = {
  sm: "px-3 py-1.5 text-sm",
  md: "px-4 py-2 text-sm",
  lg: "px-6 py-3 text-base",
};

export function Button({
  variant = "primary",
  size = "md",
  loading = false,
  disabled,
  className = "",
  children,
  ...props
}: ButtonProps) {
  return (
    <button
      // aria-busy rather than swapping the label: a screen reader announcing
      // "Loading" mid-submit is less confusing than the label disappearing.
      aria-busy={loading || undefined}
      disabled={disabled || loading}
      className={`inline-flex items-center justify-center gap-2 rounded-lg font-medium transition
        disabled:cursor-not-allowed ${BUTTON_VARIANTS[variant]} ${BUTTON_SIZES[size]} ${className}`}
      {...props}
    >
      {loading && <Spinner size={16} />}
      {children}
    </button>
  );
}

// --- Card -----------------------------------------------------------------

export function Card({ className = "", children }: { className?: string; children: ReactNode }) {
  return (
    <div className={`rounded-card bg-white ring-1 ring-ink-200/70 ${className}`}>{children}</div>
  );
}

export function CardHeader({ title, subtitle, action }: { title: ReactNode; subtitle?: ReactNode; action?: ReactNode }) {
  return (
    <div className="flex items-start justify-between gap-4 border-b border-ink-100 px-5 py-4">
      <div className="min-w-0">
        {/* Wraps rather than truncates. Several headers carry real content --
            a question stem in the review queue, an SRT situation in a psych
            read-out -- and clipping those makes the screen unusable for the one
            job it has: judging the text. */}
        <h2 className="font-semibold text-balance text-ink-900">{title}</h2>
        {subtitle && <p className="mt-0.5 text-sm text-ink-500">{subtitle}</p>}
      </div>
      {action}
    </div>
  );
}

// --- Form fields ----------------------------------------------------------

type FieldProps = InputHTMLAttributes<HTMLInputElement> & { label: string; error?: string; hint?: string };

export function Field({ label, error, hint, id, className = "", ...props }: FieldProps) {
  const fieldId = id ?? props.name ?? label.toLowerCase().replace(/\s+/g, "-");
  const describedBy = error ? `${fieldId}-error` : hint ? `${fieldId}-hint` : undefined;

  return (
    <div className={className}>
      <label htmlFor={fieldId} className="mb-1.5 block text-sm font-medium text-ink-700">
        {label}
      </label>
      <input
        id={fieldId}
        aria-invalid={error ? true : undefined}
        aria-describedby={describedBy}
        className={`w-full rounded-lg border bg-white px-3 py-2 text-ink-900 placeholder:text-ink-500
          ${error ? "border-danger-500" : "border-ink-200"}`}
        {...props}
      />
      {error && (
        <p id={`${fieldId}-error`} className="mt-1 text-sm text-danger-500">
          {error}
        </p>
      )}
      {!error && hint && (
        <p id={`${fieldId}-hint`} className="mt-1 text-sm text-ink-500">
          {hint}
        </p>
      )}
    </div>
  );
}

type TextAreaProps = TextareaHTMLAttributes<HTMLTextAreaElement> & { label?: string; error?: string };

export function TextArea({ label, error, id, className = "", ...props }: TextAreaProps) {
  const fieldId = id ?? props.name ?? "textarea";
  return (
    <div className={className}>
      {label && (
        <label htmlFor={fieldId} className="mb-1.5 block text-sm font-medium text-ink-700">
          {label}
        </label>
      )}
      <textarea
        id={fieldId}
        aria-invalid={error ? true : undefined}
        className={`w-full rounded-lg border bg-white px-3 py-2 text-ink-900 placeholder:text-ink-500
          ${error ? "border-danger-500" : "border-ink-200"}`}
        {...props}
      />
      {error && <p className="mt-1 text-sm text-danger-500">{error}</p>}
    </div>
  );
}

// --- Feedback -------------------------------------------------------------

export function Alert({ tone = "info", children }: { tone?: "info" | "error" | "success"; children: ReactNode }) {
  const tones = {
    info: "bg-gold-50 text-ink-800",
    error: "bg-danger-50 text-danger-500",
    success: "bg-success-50 text-success-500",
  };
  return (
    <div role={tone === "error" ? "alert" : "status"} className={`flex gap-2 rounded-lg px-4 py-3 text-sm ${tones[tone]}`}>
      {tone === "error" ? <AlertIcon size={18} /> : <Info size={18} />}
      <div className="min-w-0">{children}</div>
    </div>
  );
}

export function Loading({ label = "Loading" }: { label?: string }) {
  return (
    <div role="status" className="flex items-center justify-center gap-3 py-16 text-ink-500">
      <Spinner size={22} />
      <span>{label}...</span>
    </div>
  );
}

export function EmptyState({ title, body, action }: { title: string; body?: string; action?: ReactNode }) {
  return (
    <div className="rounded-card bg-white px-6 py-14 text-center ring-1 ring-ink-200/70">
      <h3 className="font-semibold text-ink-800">{title}</h3>
      {body && <p className="mx-auto mt-1 max-w-md text-sm text-ink-500">{body}</p>}
      {action && <div className="mt-5">{action}</div>}
    </div>
  );
}

export function ErrorState({ error, onRetry }: { error: Error; onRetry?: () => void }) {
  return (
    <div className="rounded-card bg-white px-6 py-12 text-center ring-1 ring-ink-200/70">
      <AlertIcon size={26} className="mx-auto text-danger-500" />
      <h3 className="mt-3 font-semibold text-ink-800">That did not load</h3>
      <p className="mx-auto mt-1 max-w-md text-sm text-ink-500">{error.message}</p>
      {onRetry && (
        <Button variant="secondary" className="mt-5" onClick={onRetry}>
          Try again
        </Button>
      )}
    </div>
  );
}

export function Badge({ tone = "neutral", children }: { tone?: "neutral" | "green" | "amber" | "red"; children: ReactNode }) {
  const tones = {
    neutral: "bg-ink-100 text-ink-600",
    green: "bg-success-50 text-success-500",
    amber: "bg-gold-50 text-gold-500",
    red: "bg-danger-50 text-danger-500",
  };
  return <span className={`rounded-full px-2.5 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}
