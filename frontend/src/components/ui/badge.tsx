import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const badgeVariants = cva(
  "inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-mono font-medium transition-colors",
  {
    variants: {
      variant: {
        default: "border-blueprint/40 bg-blueprint/10 text-blueprint",
        annotation: "border-annotation/40 bg-annotation/10 text-annotation",
        success: "border-success/40 bg-success/10 text-success",
        danger: "border-danger/40 bg-danger/10 text-danger",
        neutral: "border-ink-600 bg-ink-700 text-paper-dim",
      },
    },
    defaultVariants: { variant: "neutral" },
  }
);

export interface BadgeProps extends React.HTMLAttributes<HTMLDivElement>, VariantProps<typeof badgeVariants> {}

function Badge({ className, variant, ...props }: BadgeProps) {
  return <div className={cn(badgeVariants({ variant }), className)} {...props} />;
}

export { Badge, badgeVariants };
