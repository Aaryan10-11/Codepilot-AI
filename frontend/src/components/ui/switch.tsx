import type { ComponentProps } from "react";
import { cn } from "../../lib/utils";

export interface SwitchProps extends Omit<ComponentProps<"button">, "onChange"> {
  checked: boolean;
  onChange?: (checked: boolean) => void;
}

export function Switch({ checked, onChange, className, ...props }: SwitchProps) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={() => onChange?.(!checked)}
      className={cn(
        "relative h-[20px] w-[36px] shrink-0 rounded-full border border-border bg-surface transition-colors focus-visible:outline-2 focus-visible:outline-accent focus-visible:outline-offset-2",
        checked && "border-transparent bg-text",
        className,
      )}
      {...props}
    >
      <span
        className={cn(
          "absolute top-[2px] h-[16px] w-[16px] rounded-full bg-muted transition-transform",
          checked && "translate-x-[16px] bg-bg",
        )}
      />
    </button>
  );
}
