import { useEffect, useState } from "react";


interface HealthRingProps {
  value: number;
  size?: number;
  strokeWidth?: number;
  trackColor?: string;
  progressColor?: string;
}


export default function HealthRing({
  value,
  size = 92,
  strokeWidth = 8,
  trackColor = "rgba(233,243,255,0.85)",
  progressColor = "#ff5733",
}: HealthRingProps) {
  const [animatedValue, setAnimatedValue] = useState(0);
  const clampedValue = Math.max(0, Math.min(100, value));
  const radius = (size - strokeWidth) / 2;
  const circumference = 2 * Math.PI * radius;

  useEffect(() => {
    let frameId = 0;
    const start = performance.now();
    const duration = 900;

    function animate(now: number) {
      const progress = Math.min((now - start) / duration, 1);
      setAnimatedValue(clampedValue * progress);

      if (progress < 1) {
        frameId = requestAnimationFrame(animate);
      }
    }

    frameId = requestAnimationFrame(animate);
    return () => cancelAnimationFrame(frameId);
  }, [clampedValue]);

  const dashOffset = circumference * (1 - animatedValue / 100);

  return (
    <div
      className="service-health-ring"
      role="img"
      aria-label={`Service health ${Math.round(clampedValue)} percent`}
    >
      <svg
        width={size}
        height={size}
        viewBox={`0 0 ${size} ${size}`}
        className="service-health-ring__svg"
      >
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={trackColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
        />
        <circle
          cx={size / 2}
          cy={size / 2}
          r={radius}
          fill="none"
          stroke={progressColor}
          strokeWidth={strokeWidth}
          strokeLinecap="round"
          strokeDasharray={circumference}
          strokeDashoffset={dashOffset}
          transform={`rotate(-90 ${size / 2} ${size / 2})`}
          className="service-health-ring__progress"
        />
      </svg>
      <div className="service-health-ring__label">
        {Math.round(animatedValue)}%
      </div>
    </div>
  );
}
