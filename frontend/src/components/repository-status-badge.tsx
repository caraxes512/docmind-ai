import { Badge } from "@/components/ui/badge";
import type { RepositoryStatus } from "@/lib/types";

const STATUS_CONFIG: Record<RepositoryStatus, { label: string; variant: "default" | "success" | "danger" | "neutral" }> = {
  pending: { label: "Pending", variant: "neutral" },
  scanning: { label: "Scanning", variant: "default" },
  parsing: { label: "Parsing", variant: "default" },
  embedding: { label: "Embedding", variant: "default" },
  ready: { label: "Ready", variant: "success" },
  failed: { label: "Failed", variant: "danger" },
};

export function RepositoryStatusBadge({ status }: { status: RepositoryStatus }) {
  const config = STATUS_CONFIG[status];
  return <Badge variant={config.variant}>{config.label}</Badge>;
}
