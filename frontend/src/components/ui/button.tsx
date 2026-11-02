import type { ButtonHTMLAttributes, ReactNode } from "react";
import { cn } from "../../lib/utils";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const variantStyles: Record<Variant, string> = {
  primary:
    "bg-text text-bg border border-transparent hover:bg-text/90 focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2",
  secondary:
    "bg-surface text-text border border-border hover:bg-raised focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2",
  ghost: "bg-transparent text-text border border-transparent hover:bg-raised focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2",
  danger: "bg-surface text-negative border border-border hover:bg-raised focus-visible:outline-2 focus-visible:outline-negative focus-visible:outline-offset-2",
};

const sizeStyles: Record<Size, string> = {
  sm: "h-[28px] px-2.5 text-xs",
  md: "h-[34px] px-3.5 text-sm",
  lg: "h-11 px-5 text-sm",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
}

export function Button({ className, variant = "secondary", size = "md", type = "button", ...props }: ButtonProps) {
  return (
    <button
      type={type}
      className={cn(
        "inline-flex items-center justify-center gap-2 rounded-full border font-medium transition-colors focus-visible:outline-2 focus-visible:outline-offset-2 disabled:pointer-events-none disabled:opacity-50",
        variantStyles[variant],
        sizeStyles[size],
        className,
      )}
      {...props}
    />
  );
}

export function IconButton({
  className,
  label,
  children,
  ...props
}: ButtonHTMLAttributes<HTMLButtonElement> & { label: string; children: ReactNode }) {
  return (
    <button
      type="button"
      aria-label={label}
      title={label}
      className={cn(
        "inline-flex h-[30px] w-[30px] items-center justify-center rounded-full border border-transparent bg-transparent text-muted transition-colors hover:bg-raised hover:text-text focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2",
        className,
      )}
      {...props}
    >
      {children}
    </button>
  );
}
