/**
 * Service avatars, drawn rather than photographed.
 *
 * The previous site's officer photographs were 2.2 MB of PNG for five images.
 * On a free tier that is bandwidth the platform pays for on every cold visit,
 * and it buys a picture the reader looks at once. These are a few hundred bytes
 * each, scale to any size without a second asset, recolour with the service
 * palette, and stay sharp on the cheap Android screens most candidates use.
 *
 * Each is a shoulders-up figure in that service's uniform, distinguished the
 * way the real ones are: the Army's beret and khaki, the PAF's peaked cap and
 * blue, the Navy's white cap and tunic.
 */

type Props = { service: string; size?: number; className?: string };

const PALETTE: Record<string, { coat: string; trim: string; cap: string; badge: string }> = {
  army: { coat: "#6f7a53", trim: "#55603f", cap: "#2f5d3a", badge: "#b8912f" },
  air_force: { coat: "#2c4f7c", trim: "#22406a", cap: "#1c3f6e", badge: "#c9d4e4" },
  navy: { coat: "#f2f3f5", trim: "#d7dbe2", cap: "#12405a", badge: "#b8912f" },
  common: { coat: "#8a8a80", trim: "#6b6b62", cap: "#4e4e47", badge: "#b8912f" },
};

export function ServiceAvatar({ service, size = 96, className = "" }: Props) {
  const colour = PALETTE[service] ?? PALETTE.common;
  const navy = service === "navy";

  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 96 96"
      role="img"
      aria-hidden="true"
      className={className}
    >
      {/* shoulders */}
      <path
        d="M14 96c0-19 15-30 34-30s34 11 34 30z"
        fill={colour.coat}
      />
      {/* lapel shadow, so the tunic reads as clothing rather than a blob */}
      <path d="M48 66 38 96h20z" fill={colour.trim} />
      {/* rank slides */}
      <rect x="20" y="76" width="12" height="4" rx="2" fill={colour.badge} />
      <rect x="64" y="76" width="12" height="4" rx="2" fill={colour.badge} />

      {/* neck and head */}
      <rect x="42" y="52" width="12" height="12" rx="4" fill="#c99b73" />
      <circle cx="48" cy="40" r="16" fill="#dcaf85" />

      {navy ? (
        <>
          {/* peaked cap, white crown */}
          <path d="M30 32a18 18 0 0 1 36 0v3H30z" fill="#ffffff" />
          <rect x="28" y="33" width="40" height="6" rx="3" fill={colour.cap} />
          <path d="M26 39h44a4 4 0 0 1-4 4H30a4 4 0 0 1-4-4z" fill="#1a1a19" />
        </>
      ) : service === "air_force" ? (
        <>
          {/* peaked cap, coloured crown */}
          <path d="M30 32a18 18 0 0 1 36 0v3H30z" fill={colour.cap} />
          <rect x="28" y="33" width="40" height="6" rx="3" fill={colour.trim} />
          <path d="M26 39h44a4 4 0 0 1-4 4H30a4 4 0 0 1-4-4z" fill="#1a1a19" />
        </>
      ) : (
        /* beret, worn pulled to one side as it is on parade */
        <path d="M28 34c0-11 9-18 20-18s20 5 20 13c0 3-3 5-8 5H28z" fill={colour.cap} />
      )}

      {/* cap or beret badge */}
      <circle cx={service === "army" ? 34 : 48} cy={service === "army" ? 28 : 31} r="3" fill={colour.badge} />
    </svg>
  );
}

/** A circular framed version, for lists and cards. */
export function ServiceBadge({ service, size = 56 }: { service: string; size?: number }) {
  const colour = PALETTE[service] ?? PALETTE.common;
  return (
    <span
      className="inline-grid place-items-center overflow-hidden rounded-full ring-1 ring-ink-200"
      style={{ width: size, height: size, background: `${colour.coat}22` }}
    >
      <ServiceAvatar service={service} size={size} />
    </span>
  );
}
