import { useEffect, useRef, useState } from "react";
import { gettext, interpolate } from "@smarter/common";

/** How healthy the platform is: every check passes, at least half do, or fewer. */
export type HealthLevel = "healthy" | "degraded" | "down";

interface HealthRingProps {
  value: number;
  level: HealthLevel;
  size?: number;
  strokeWidth?: number;
}

/** The score the ring showed last, kept across page loads, so that it animates only when the score changes. */
const LAST_VALUE_KEY = "smarter_service_health_ring";

/** The score the ring showed last, or null if it never showed one, or storage can't be read. */
function readLastValue(): number | null {
  try {
    const value = window.localStorage.getItem(LAST_VALUE_KEY);
    const number = value === null ? NaN : Number(value);
    return Number.isFinite(number) ? number : null;
  } catch {
    return null;
  }
}

function writeLastValue(value: number): void {
  try {
    window.localStorage.setItem(LAST_VALUE_KEY, String(value));
  } catch {
    // storage is full or blocked: the ring animates from 0 on every page load, as it would the first time.
  }
}

/** True when the user asked the browser for less motion. */
function prefersReducedMotion(): boolean {
  return typeof window.matchMedia === "function" && window.matchMedia("(prefers-reduced-motion: reduce)").matches;
}

export default function HealthRing({ value, level, size = 76, strokeWidth = 7 }: HealthRingProps) {
  const clampedValue = Math.max(0, Math.min(100, value));
  const reducedMotion = prefersReducedMotion();
  // the ring starts from the score it showed last, and animates only to a different one.
  const [animatedValue, setAnimatedValue] = useState(() => readLastValue() ?? 0);
  const shown = useRef(animatedValue);
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  useEffect(() => {
    writeLastValue(clampedValue);
    if (reducedMotion || shown.current === clampedValue) return;
    let frameId = 0;
    const from = shown.current;
    const start = performance.now();
    const duration = 900;

    function animate(now: number) {
      const progress = Math.min((now - start) / duration, 1);
      shown.current = from + (clampedValue - from) * progress;
      setAnimatedValue(shown.current);

      if (progress < 1) {
        frameId = requestAnimationFrame(animate);
      }
    }

    frameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameId);
  }, [clampedValue, reducedMotion]);

  // under reduced motion, show the final value without animating to it.
  const shownValue = reducedMotion ? clampedValue : animatedValue;
  const dashOffset = circumference * (1 - shownValue / 100);

  return (
    <div
      className={`service-health-ring service-health-ring-${level}`}
      role="img"
      aria-label={interpolate(gettext("Service health %(clampedValue)s percent"), {
        clampedValue: Math.round(clampedValue),
      })}
    >
      <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="service-health-ring__svg">
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          className="service-health-ring__track"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className="service-health-ring__progress"
        />
      </svg>
      <div className="service-health-ring__label">
        <span className="service-health-ring__value">{Math.round(shownValue)}%</span>
        {/* Translators: a caption under a percentage, e.g. "75%" over "healthy": the share of health checks that pass. */}
        <span className="service-health-ring__caption">{gettext("healthy")}</span>
      </div>
    </div>
  );
}
