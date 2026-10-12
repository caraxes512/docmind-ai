import * as React from "react";
import { cn } from "@/lib/utils";

export type TextareaProps = React.TextareaHTMLAttributes<HTMLTextAreaElement>;

const Textarea = React.forwardRef<HTMLTextAreaElement, TextareaProps>(({ className, ...props }, ref) => (
  <textarea
    ref={ref}
    className={cn(
      "flex min-h-[120px] w-full rounded border border-ink-600 bg-ink-900 px-3 py-2 text-sm text-paper placeholder:text-paper-dim focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-blueprint disabled:opacity-50 font-mono",
      className
    )}
    {...props}
  />
));
Textarea.displayName = "Textarea";

export { Textarea };
