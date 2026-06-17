import React from "react";

export function ArcoinMascot({ size = 120, className = "" }) {
  return (
    <svg width={size} height={size} viewBox="0 0 200 200" className={`mascot-wiggle ${className}`} xmlns="http://www.w3.org/2000/svg" aria-label="Arco - mascote Arcoins">
      <defs>
        <radialGradient id="coinGrad" cx="35%" cy="30%" r="70%">
          <stop offset="0%" stopColor="#FFE39A" />
          <stop offset="60%" stopColor="#FFBE0B" />
          <stop offset="100%" stopColor="#E5A900" />
        </radialGradient>
      </defs>
      <circle cx="100" cy="100" r="82" fill="url(#coinGrad)" stroke="#073B4C" strokeWidth="6" />
      <circle cx="100" cy="100" r="68" fill="none" stroke="#073B4C" strokeWidth="3" strokeDasharray="2 5" opacity="0.35" />
      <text x="100" y="118" textAnchor="middle" fontFamily="Fredoka, sans-serif" fontWeight="700" fontSize="68" fill="#073B4C">₡</text>
      <circle cx="72" cy="70" r="6" fill="#073B4C" />
      <circle cx="128" cy="70" r="6" fill="#073B4C" />
      <circle cx="74" cy="68" r="2" fill="#fff" />
      <circle cx="130" cy="68" r="2" fill="#fff" />
      <circle cx="65" cy="95" r="6" fill="#FF006E" opacity="0.55" />
      <circle cx="135" cy="95" r="6" fill="#FF006E" opacity="0.55" />
      <path d="M 80 140 Q 100 158 120 140" stroke="#073B4C" strokeWidth="4" fill="none" strokeLinecap="round" />
      <g opacity="0.85">
        <path d="M 160 40 l 3 -10 l 3 10 l 10 3 l -10 3 l -3 10 l -3 -10 l -10 -3 z" fill="#fff" />
      </g>
    </svg>
  );
}

export function ArcSymbol({ className = "" }) {
  return <span className={`arc-symbol ${className}`}>₡</span>;
}
