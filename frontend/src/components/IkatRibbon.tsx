/**
 * Лента подарка в технике икат (абрбанд): полосы с «размытыми» ступенчатыми краями,
 * как у нитей, окрашенных до тканья. Рисуется детерминированно — одинаково на сервере и в браузере.
 */

type Stripe = { color: string; width: number };

const STRIPES: Stripe[] = [
  { color: "var(--saffron)", width: 22 },
  { color: "var(--cobalt)", width: 9 },
  { color: "var(--glaze)", width: 5 },
  { color: "var(--turquoise)", width: 14 },
  { color: "var(--glaze)", width: 5 },
  { color: "var(--cobalt)", width: 9 },
  { color: "var(--saffron)", width: 22 },
];
const STEP = 7;

function random(seed: number): () => number {
  let state = seed;
  return () => {
    state = (state * 1664525 + 1013904223) % 4294967296;
    return state / 4294967296;
  };
}

function edge(x: number, height: number, next: () => number): [number, number][] {
  const points: [number, number][] = [];
  for (let y = 0; y <= height; y += STEP) {
    const shift = Math.round((next() - 0.5) * 7);
    points.push([x + shift, y], [x + shift, Math.min(y + STEP, height)]);
  }
  return points;
}

function stripePolygons(height: number) {
  const next = random(20261008);
  const total = STRIPES.reduce((sum, stripe) => sum + stripe.width, 0);
  const edges: [number, number][][] = [];
  let x = 0;
  edges.push([[0, 0], [0, height]]);
  for (const stripe of STRIPES.slice(0, -1)) {
    x += stripe.width;
    edges.push(edge(x, height, next));
  }
  edges.push([[total, 0], [total, height]]);
  const polygons = STRIPES.map((stripe, index) => {
    const left = edges[index];
    const right = [...edges[index + 1]].reverse();
    return { color: stripe.color, points: [...left, ...right].map(([px, py]) => `${px},${py}`).join(" ") };
  });
  return { total, polygons };
}

export function IkatRibbon({
  orientation = "vertical",
  length = 420,
  className,
}: {
  orientation?: "vertical" | "horizontal";
  length?: number;
  className?: string;
}) {
  const { total, polygons } = stripePolygons(length);
  const vertical = orientation === "vertical";
  return (
    <svg
      className={className}
      viewBox={vertical ? `0 0 ${total} ${length}` : `0 0 ${length} ${total}`}
      preserveAspectRatio="xMidYMid slice"
      aria-hidden="true"
      focusable="false"
    >
      <g transform={vertical ? undefined : `rotate(-90) translate(${-total} 0)`}>
        {polygons.map((polygon, index) => (
          <polygon key={index} points={polygon.points} fill={polygon.color} />
        ))}
      </g>
    </svg>
  );
}
