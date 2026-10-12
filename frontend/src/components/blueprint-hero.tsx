const NODES = [
  { id: "auth", x: 60, y: 40, w: 130, h: 40, label: "auth/" },
  { id: "api", x: 240, y: 40, w: 130, h: 40, label: "api/" },
  { id: "models", x: 60, y: 140, w: 130, h: 40, label: "models/" },
  { id: "payments", x: 240, y: 140, w: 130, h: 40, label: "payments/" },
  { id: "components", x: 150, y: 220, w: 130, h: 40, label: "components/" },
];

const EDGES = [
  { from: [190, 60], to: [240, 60], delay: "0.2s" },
  { from: [125, 80], to: [125, 140], delay: "0.4s" },
  { from: [305, 80], to: [305, 140], delay: "0.6s" },
  { from: [190, 160], to: [240, 160], delay: "0.8s" },
  { from: [180, 180], to: [200, 220], delay: "1.0s" },
];

// Positioned and measured against a 460x300 viewBox -- each rect's right/
// bottom edge is checked to stay within bounds and clear of node boxes.
const ANNOTATIONS = [
  { x: 270, y: 18, label: "Explains auth flow", delay: "1.4s" },
  { x: 250, y: 195, label: "Documents payment logic", delay: "1.8s" },
  { x: 15, y: 203, label: "Maps DB relationships", delay: "2.2s" },
];

export function BlueprintHero() {
  return (
    <div className="relative w-full max-w-xl">
      <svg
        viewBox="0 0 460 300"
        className="w-full"
        role="img"
        aria-label="Diagram of DocMind AI annotating a repository's folder structure with explanatory callouts"
      >
        {EDGES.map((edge, i) => (
          <line
            key={i}
            x1={edge.from[0]}
            y1={edge.from[1]}
            x2={edge.to[0]}
            y2={edge.to[1]}
            className="blueprint-line"
            style={{ "--delay": edge.delay } as React.CSSProperties}
            stroke="#5FB8C9"
            strokeWidth={1.5}
          />
        ))}

        {NODES.map((node) => (
          <g key={node.id}>
            <rect
              x={node.x}
              y={node.y}
              width={node.w}
              height={node.h}
              rx={4}
              fill="#161C2C"
              stroke="#5FB8C9"
              strokeWidth={1.5}
            />
            <text
              x={node.x + node.w / 2}
              y={node.y + node.h / 2}
              textAnchor="middle"
              dominantBaseline="central"
              fill="#5FB8C9"
              fontSize="12"
              fontFamily="var(--font-plex-mono)"
            >
              {node.label}
            </text>
          </g>
        ))}

        {ANNOTATIONS.map((a, i) => {
          const rectWidth = a.label.length * 6.2 + 16;
          return (
            <g key={i} className="annotation-pin" style={{ "--delay": a.delay } as React.CSSProperties}>
              <circle cx={a.x} cy={a.y} r={4} fill="#E8A857" />
              <rect x={a.x + 10} y={a.y - 12} width={rectWidth} height={24} rx={12} fill="#E8A857" />
              <text
                x={a.x + 18}
                y={a.y}
                dominantBaseline="central"
                fill="#0D1220"
                fontSize="11"
                fontFamily="var(--font-plex-mono)"
                fontWeight={500}
              >
                {a.label}
              </text>
            </g>
          );
        })}
      </svg>
    </div>
  );
}
