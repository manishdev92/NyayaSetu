"use client";

import { useId } from "react";

/** Scales of justice: brass beam, column, chains, and balanced bowls — legible at small sizes. */
export function NyayaSetuLogo({
  className = "h-10 w-10",
  "aria-hidden": ariaHidden = true,
}: {
  className?: string;
  "aria-hidden"?: boolean;
}) {
  const uid = useId().replace(/:/g, "");
  const gBg = `nsl-g-${uid}`;
  const gSheen = `nsl-s-${uid}`;
  const gBrass = `nsl-b-${uid}`;
  const gPillar = `nsl-p-${uid}`;
  const fSh = `nsl-sh-${uid}`;

  return (
    <svg
      className={className}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden={ariaHidden}
    >
      <defs>
        <linearGradient id={gBg} x1="1" y1="0" x2="32" y2="34" gradientUnits="userSpaceOnUse">
          <stop stopColor="#0c0a09" />
          <stop offset="0.38" stopColor="#1c1917" />
          <stop offset="0.7" stopColor="#713f12" />
          <stop offset="1" stopColor="#a16207" />
        </linearGradient>
        <radialGradient id={gSheen} cx="0.3" cy="0.2" r="0.7" gradientUnits="objectBoundingBox">
          <stop stopColor="#fffbeb" stopOpacity="0.28" />
          <stop offset="0.55" stopColor="#fffbeb" stopOpacity="0" />
        </radialGradient>
        <linearGradient id={gBrass} x1="4" y1="7" x2="28" y2="8.5" gradientUnits="userSpaceOnUse">
          <stop stopColor="#fde68a" />
          <stop offset="0.45" stopColor="#fbbf24" />
          <stop offset="1" stopColor="#b45309" />
        </linearGradient>
        <linearGradient id={gPillar} x1="15" y1="8" x2="17" y2="30" gradientUnits="userSpaceOnUse">
          <stop stopColor="#fef3c7" stopOpacity="0.5" />
          <stop offset="0.5" stopColor="#d6d3d1" stopOpacity="0.4" />
          <stop offset="1" stopColor="#a8a29e" stopOpacity="0.35" />
        </linearGradient>
        <filter id={fSh} x="-20%" y="-20%" width="140%" height="140%">
          <feDropShadow
            dx="0"
            dy="0.4"
            stdDeviation="0.35"
            floodColor="#0c0a09"
            floodOpacity="0.45"
          />
        </filter>
      </defs>
      <rect width="32" height="32" rx="7.5" fill={`url(#${gBg})`} />
      <rect width="32" height="32" rx="7.5" fill={`url(#${gSheen})`} />
      <rect
        x="0.4"
        y="0.4"
        width="31.2"
        height="31.2"
        rx="7.1"
        stroke="#fbbf24"
        strokeOpacity="0.28"
        strokeWidth="0.8"
      />
      <rect
        x="3.8"
        y="6.35"
        width="24.4"
        height="1.7"
        rx="0.85"
        fill={`url(#${gBrass})`}
        stroke="#78350f"
        strokeWidth="0.2"
        strokeOpacity="0.35"
      />
      <circle
        cx="16"
        cy="7.2"
        r="1.55"
        fill={`url(#${gBrass})`}
        stroke="#92400e"
        strokeWidth="0.35"
      />
      <circle cx="16" cy="6.9" r="0.4" fill="#fffbeb" fillOpacity="0.55" />
      <line
        x1="16"
        y1="8"
        x2="16"
        y2="24"
        stroke={`url(#${gPillar})`}
        strokeWidth="1.9"
        strokeLinecap="round"
      />
      <line
        x1="16"
        y1="8"
        x2="16"
        y2="24"
        stroke="#ffedd5"
        strokeWidth="0.5"
        strokeLinecap="round"
        strokeOpacity="0.65"
      />
      <g stroke="#e7e5e4" strokeWidth="0.55" strokeLinecap="round" fill="none">
        <line x1="6.2" y1="8.1" x2="6.2" y2="9.2" />
        <line x1="6.2" y1="10" x2="6.2" y2="10.7" />
        <line x1="6.2" y1="11.5" x2="6.2" y2="12.8" />
        <line x1="25.8" y1="8.1" x2="25.8" y2="9.2" />
        <line x1="25.8" y1="10" x2="25.8" y2="10.7" />
        <line x1="25.8" y1="11.5" x2="25.8" y2="12.8" />
      </g>
      <g filter={`url(#${fSh})`}>
        <ellipse cx="6.3" cy="16.45" rx="3.1" ry="0.5" fill="#0c0a09" fillOpacity="0.35" />
        <ellipse cx="25.7" cy="16.45" rx="3.1" ry="0.5" fill="#0c0a09" fillOpacity="0.35" />
      </g>
      <ellipse
        cx="6.3"
        cy="16.1"
        rx="3.2"
        ry="1.6"
        fill="#f5f5f4"
        stroke="#d6d3d1"
        strokeWidth="0.45"
      />
      <ellipse
        cx="25.7"
        cy="16.1"
        rx="3.2"
        ry="1.6"
        fill="#f5f5f4"
        stroke="#d6d3d1"
        strokeWidth="0.45"
      />
      <ellipse
        cx="6.3"
        cy="15.2"
        rx="2.5"
        ry="0.7"
        fill="none"
        stroke="#a16207"
        strokeWidth="0.22"
        strokeOpacity="0.4"
      />
      <ellipse
        cx="25.7"
        cy="15.2"
        rx="2.5"
        ry="0.7"
        fill="none"
        stroke="#a16207"
        strokeWidth="0.22"
        strokeOpacity="0.4"
      />
      <ellipse cx="6.3" cy="15.1" rx="1.1" ry="0.3" fill="#fffbeb" fillOpacity="0.4" />
      <ellipse cx="25.7" cy="15.1" rx="1.1" ry="0.3" fill="#fffbeb" fillOpacity="0.4" />
    </svg>
  );
}

export function NyayaWordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-semibold tracking-tight text-stone-900 ${className}`}>
      Nyaya<span className="text-amber-800">Setu</span>
    </span>
  );
}
