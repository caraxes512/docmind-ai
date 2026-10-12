"use client";

import { useEffect, useId, useRef, useState } from "react";

// mermaid is loaded lazily (dynamic import) rather than imported at module
// scope, since it's a sizeable client-only library that has no reason to be
// in the initial bundle for pages that don't render diagrams.
export function MermaidDiagram({ source }: { source: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const [error, setError] = useState<string | null>(null);
  const diagramId = useId().replace(/:/g, "");

  useEffect(() => {
    let isCancelled = false;

    async function render() {
      try {
        const mermaid = (await import("mermaid")).default;
        mermaid.initialize({
          startOnLoad: false,
          theme: "dark",
          themeVariables: {
            background: "#161C2C",
            primaryColor: "#161C2C",
            primaryBorderColor: "#5FB8C9",
            primaryTextColor: "#EDEEF2",
            lineColor: "#5FB8C9",
            fontFamily: "var(--font-plex-mono)",
          },
        });
        const { svg } = await mermaid.render(`mermaid-${diagramId}`, source);
        if (!isCancelled && containerRef.current) {
          containerRef.current.innerHTML = svg;
        }
      } catch (err) {
        if (!isCancelled) {
          setError(err instanceof Error ? err.message : "Failed to render diagram");
        }
      }
    }

    render();
    return () => {
      isCancelled = true;
    };
  }, [source, diagramId]);

  if (error) {
    return (
      <div className="rounded border border-danger/40 bg-danger/5 p-4 text-sm text-danger">
        Couldn&apos;t render this diagram: {error}
      </div>
    );
  }

  return <div ref={containerRef} className="flex justify-center overflow-x-auto rounded bg-ink-800 p-4" />;
}
