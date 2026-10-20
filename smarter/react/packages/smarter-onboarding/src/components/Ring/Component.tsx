/**
 * The sparkling ring around the element that a hint points to: a glowing outline that pulses, with a few
 * twinkling sparkles on its edge. It doesn't take clicks, so the element stays clickable.
 *
 * :param box: The ring's box, in the window's coordinates.
 * :param shape: "pill" for a link or a button, the spotlight's, or "rounded" for a larger area, the tour's.
 * :param dim: Whether the rest of the page is dimmed, as the tour does.
 */
import type { Box } from "../../lib/position";
import "../styles.css";

const SPARKLES = 6;

function Ring({ box, shape = "pill", dim = false }: { box: Box; shape?: "pill" | "rounded"; dim?: boolean }) {
  return (
    <div
      className={`smarter-onboarding-ring smarter-onboarding-ring-${shape} ${dim ? "smarter-onboarding-ring-dim" : ""}`}
      style={{ top: box.top, left: box.left, width: box.width, height: box.height }}
      aria-hidden="true"
      data-testid="smarter-onboarding-ring"
    >
      {Array.from({ length: SPARKLES }, (_, index) => (
        <span key={index} className="smarter-onboarding-sparkle" />
      ))}
    </div>
  );
}

export default Ring;
