import { Badge } from "@/components/ui/badge";

export function QualityScoreBadge({ score }: { score: number }) {
  const variant = score >= 80 ? "success" : score >= 50 ? "annotation" : "danger";
  return <Badge variant={variant}>Quality {Math.round(score)}</Badge>;
}
