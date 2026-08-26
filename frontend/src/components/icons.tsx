/**
 * Inline SVG icons.
 *
 * This replaces an icon package. The app needs about twenty glyphs; the usual
 * library ships fifteen hundred as individual files, which on Windows made
 * `npm install` fail repeatedly with ENOTEMPTY. Inlining the handful we use
 * removes a dependency, a build-time tree-shaking question and an install
 * hazard, at the cost of this one file.
 *
 * All paths are 24x24 on a `currentColor` stroke, so they inherit text colour
 * and size from their container like a font glyph would.
 */

import type { SVGProps } from "react";

type IconProps = SVGProps<SVGSVGElement> & { size?: number };

function Icon({ size = 20, children, ...props }: IconProps) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
      focusable="false"
      {...props}
    >
      {children}
    </svg>
  );
}

export const ChevronRight = (p: IconProps) => (
  <Icon {...p}><path d="m9 18 6-6-6-6" /></Icon>
);

export const ChevronLeft = (p: IconProps) => (
  <Icon {...p}><path d="m15 18-6-6 6-6" /></Icon>
);

export const Menu = (p: IconProps) => (
  <Icon {...p}><path d="M4 6h16M4 12h16M4 18h16" /></Icon>
);

export const Close = (p: IconProps) => (
  <Icon {...p}><path d="M18 6 6 18M6 6l12 12" /></Icon>
);

export const Check = (p: IconProps) => (
  <Icon {...p}><path d="M20 6 9 17l-5-5" /></Icon>
);

export const Clock = (p: IconProps) => (
  <Icon {...p}><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></Icon>
);

export const Flag = (p: IconProps) => (
  <Icon {...p}><path d="M4 21V4h11l-1.5 4L15 12H4" /></Icon>
);

export const Target = (p: IconProps) => (
  <Icon {...p}><circle cx="12" cy="12" r="9" /><circle cx="12" cy="12" r="5" /><circle cx="12" cy="12" r="1" /></Icon>
);

export const Brain = (p: IconProps) => (
  <Icon {...p}>
    <path d="M9.5 4a2.5 2.5 0 0 0-2.5 2.5A2.5 2.5 0 0 0 5 9v1a2.5 2.5 0 0 0 1 4v1.5A2.5 2.5 0 0 0 8.5 18H9" />
    <path d="M14.5 4A2.5 2.5 0 0 1 17 6.5 2.5 2.5 0 0 1 19 9v1a2.5 2.5 0 0 1-1 4v1.5A2.5 2.5 0 0 1 15.5 18H15" />
    <path d="M12 4v16" />
  </Icon>
);

export const Users = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="9" cy="8" r="3" />
    <path d="M3 20a6 6 0 0 1 12 0" />
    <path d="M16 6.5a3 3 0 0 1 0 5.5M17 20a6 6 0 0 0-2-4.5" />
  </Icon>
);

export const Book = (p: IconProps) => (
  <Icon {...p}><path d="M4 5a2 2 0 0 1 2-2h13v16H6a2 2 0 0 0-2 2z" /><path d="M4 17h15" /></Icon>
);

export const Trophy = (p: IconProps) => (
  <Icon {...p}>
    <path d="M7 4h10v5a5 5 0 0 1-10 0z" />
    <path d="M7 6H4v1a3 3 0 0 0 3 3M17 6h3v1a3 3 0 0 1-3 3" />
    <path d="M10 14v3h4v-3M8 20h8" />
  </Icon>
);

export const Run = (p: IconProps) => (
  <Icon {...p}>
    <circle cx="15" cy="5" r="1.5" />
    <path d="m13 21 1.5-5L11 13l1-5 4 3 3 .5" />
    <path d="m11 13-3 2-2 5" />
  </Icon>
);

export const Chart = (p: IconProps) => (
  <Icon {...p}><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" /></Icon>
);

export const Logout = (p: IconProps) => (
  <Icon {...p}><path d="M9 21H5a2 2 0 0 1-2-2V5a2 2 0 0 1 2-2h4" /><path d="m16 17 5-5-5-5M21 12H9" /></Icon>
);

export const User = (p: IconProps) => (
  <Icon {...p}><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></Icon>
);

export const Alert = (p: IconProps) => (
  <Icon {...p}><circle cx="12" cy="12" r="9" /><path d="M12 8v5M12 16h.01" /></Icon>
);

export const Info = (p: IconProps) => (
  <Icon {...p}><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></Icon>
);

export const Spinner = ({ size = 20, className = "", ...p }: IconProps) => (
  <svg
    width={size}
    height={size}
    viewBox="0 0 24 24"
    fill="none"
    className={`animate-spin ${className}`}
    aria-hidden="true"
    {...p}
  >
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="2.5" opacity="0.2" />
    <path d="M21 12a9 9 0 0 0-9-9" stroke="currentColor" strokeWidth="2.5" strokeLinecap="round" />
  </svg>
);
