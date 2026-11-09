/* eslint-disable @next/next/no-img-element */

/** PLATO wordmark: thin, widely-tracked letters with the "A" drawn as a laser apex (Λ). */
export function Wordmark({ className = "" }: { className?: string }) {
  return (
    <span className={`font-light tracking-[0.42em] text-ice ${className}`} aria-label="PLATO">
      PL<span className="relative text-cyan [text-shadow:0_0_12px_rgba(94,231,255,0.8)]">Λ</span>TO
    </span>
  );
}

export function Mark({ size = 36 }: { size?: number }) {
  return (
    <img
      src="/plato-mark.png"
      alt=""
      width={size}
      height={size}
      className="rounded-full ring-1 ring-cyan/25 shadow-glow-sm"
      style={{ width: size, height: size }}
    />
  );
}
