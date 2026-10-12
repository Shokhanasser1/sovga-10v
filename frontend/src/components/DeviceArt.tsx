/** Рисованные силуэты устройств — пока в каталоге нет фотографий. */

export type DeviceKind = "phone" | "tablet" | "case" | "charger" | "audio" | "watch" | "glass" | "powerbank";

const KIND_BY_CATEGORY: Record<string, DeviceKind> = {
  smartphones: "phone",
  tablets: "tablet",
  cases: "case",
  chargers: "charger",
  headphones: "audio",
  smartwatches: "watch",
  "screen-protectors": "glass",
  "power-banks": "powerbank",
};

const DEFAULT_COLOR: Record<DeviceKind, string> = {
  phone: "#2b2f3a",
  tablet: "#7d828a",
  case: "#1d1f24",
  charger: "#f2f2ee",
  audio: "#f2f2ee",
  watch: "#2b2f3a",
  glass: "#e4ecef",
  powerbank: "#2b2f3a",
};

export function kindFor(categorySlug: string): DeviceKind {
  return KIND_BY_CATEGORY[categorySlug] ?? "phone";
}

function isLight(hex: string): boolean {
  const value = Number.parseInt(hex.slice(1), 16);
  const r = (value >> 16) & 255;
  const g = (value >> 8) & 255;
  const b = value & 255;
  return 0.299 * r + 0.587 * g + 0.114 * b > 160;
}

const OUTLINE = "rgb(20 26 46 / 0.18)";

function Phone({ color }: { color: string }) {
  return (
    <>
      <rect x="58" y="16" width="84" height="208" rx="18" fill={color} stroke={OUTLINE} />
      <rect x="68" y="28" width="38" height="38" rx="11" fill="#000" opacity="0.16" />
      <circle cx="79" cy="39" r="7" fill="#0d1018" />
      <circle cx="95" cy="39" r="7" fill="#0d1018" />
      <circle cx="79" cy="55" r="7" fill="#0d1018" />
    </>
  );
}

function Tablet({ color }: { color: string }) {
  return (
    <>
      <rect x="22" y="36" width="156" height="180" rx="16" fill={color} stroke={OUTLINE} />
      <circle cx="42" cy="56" r="8" fill="#0d1018" />
    </>
  );
}

function Case({ color }: { color: string }) {
  return (
    <>
      <rect x="54" y="12" width="92" height="216" rx="22" fill={color} stroke={OUTLINE} />
      <rect x="64" y="24" width="46" height="46" rx="13" fill="var(--glaze)" />
      <rect x="146" y="70" width="4" height="34" rx="2" fill={color} />
    </>
  );
}

function Charger({ color }: { color: string }) {
  return (
    <>
      <rect x="78" y="50" width="10" height="38" rx="3" fill="#b9bfc8" />
      <rect x="112" y="50" width="10" height="38" rx="3" fill="#b9bfc8" />
      <rect x="54" y="84" width="92" height="108" rx="20" fill={color} stroke={OUTLINE} />
      <rect x="86" y="160" width="28" height="9" rx="4.5" fill="#141a2e" opacity="0.7" />
    </>
  );
}

function Audio({ color }: { color: string }) {
  return (
    <>
      <circle cx="80" cy="70" r="17" fill={color} stroke={OUTLINE} />
      <rect x="76" y="70" width="9" height="42" rx="4.5" fill={color} stroke={OUTLINE} />
      <circle cx="120" cy="70" r="17" fill={color} stroke={OUTLINE} />
      <rect x="115" y="70" width="9" height="42" rx="4.5" fill={color} stroke={OUTLINE} />
      <rect x="46" y="124" width="108" height="86" rx="34" fill={color} stroke={OUTLINE} />
      <line x1="50" y1="152" x2="150" y2="152" stroke={OUTLINE} strokeWidth="2" />
    </>
  );
}

function Watch({ color }: { color: string }) {
  return (
    <>
      <rect x="74" y="14" width="52" height="60" rx="10" fill="#141a2e" opacity="0.75" />
      <rect x="74" y="166" width="52" height="60" rx="10" fill="#141a2e" opacity="0.75" />
      <rect x="56" y="64" width="88" height="112" rx="26" fill={color} stroke={OUTLINE} />
      <rect x="64" y="72" width="72" height="96" rx="20" fill="#0d1018" />
      <rect x="144" y="96" width="7" height="22" rx="3.5" fill={color} stroke={OUTLINE} />
    </>
  );
}

function Glass({ color }: { color: string }) {
  return (
    <>
      <rect x="58" y="16" width="84" height="208" rx="18" fill={color} opacity="0.75" stroke={OUTLINE} />
      <rect x="88" y="24" width="24" height="7" rx="3.5" fill="#141a2e" opacity="0.25" />
      <line x1="70" y1="120" x2="128" y2="62" stroke="#fff" strokeWidth="6" opacity="0.7" />
      <line x1="72" y1="146" x2="130" y2="88" stroke="#fff" strokeWidth="3" opacity="0.6" />
    </>
  );
}

function PowerBank({ color }: { color: string }) {
  return (
    <>
      <rect x="54" y="30" width="92" height="180" rx="20" fill={color} stroke={OUTLINE} />
      <rect x="88" y="40" width="24" height="8" rx="4" fill="#0d1018" opacity="0.6" />
      {[0, 1, 2, 3].map((dot) => (
        <circle key={dot} cx={82 + dot * 12} cy="168" r="3.5" fill="#7fd6a1" opacity={dot < 3 ? 1 : 0.3} />
      ))}
    </>
  );
}

const SHAPES = {
  phone: Phone,
  tablet: Tablet,
  case: Case,
  charger: Charger,
  audio: Audio,
  watch: Watch,
  glass: Glass,
  powerbank: PowerBank,
};

const LABEL_Y: Partial<Record<DeviceKind, number>> = {
  tablet: 196,
  audio: 186,
  charger: 132,
  watch: 124,
  powerbank: 140,
};

export function DeviceArt({
  kind,
  color,
  label,
  className,
}: {
  kind: DeviceKind;
  color?: string;
  label?: string;
  className?: string;
}) {
  const fill = color ?? DEFAULT_COLOR[kind];
  const Shape = SHAPES[kind];
  const labelY = LABEL_Y[kind] ?? 200;
  return (
    <svg className={className} viewBox="0 0 200 240" role="img" aria-label={label ?? ""}>
      <Shape color={fill} />
      {label && (
        <text
          x="100"
          y={labelY}
          textAnchor="middle"
          fontSize="11"
          fontFamily="var(--font-body)"
          fill={isLight(fill) && kind !== "watch" ? "#586378" : "rgb(255 255 255 / 0.7)"}
        >
          {label}
        </text>
      )}
    </svg>
  );
}
