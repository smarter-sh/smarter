/**
 * Render Recharts charts at a fixed size in tests. jsdom has no layout, so a ResponsiveContainer
 * measures 0 x 0 and draws nothing: no axes, ticks or bars, and none of their formatters run.
 * Bars, lines and areas are drawn without their animations, which would delay them.
 *
 * Replace ResponsiveContainer in a test file with:
 *
 *     vi.mock("recharts", async (importOriginal) =>
 *       (await import("@test/recharts")).withFixedSize(await importOriginal()),
 *     );
 */
import { cloneElement, isValidElement, type ReactNode } from "react";

export const CHART_WIDTH = 800;
export const CHART_HEIGHT = 400;

type ContainerProps = { children?: ReactNode; height?: number | string };

type Series = typeof import("recharts").Bar;

/** The series component, drawn without its animation. */
function withoutAnimation(Component: Series): Series {
  const Unanimated = (props: Record<string, unknown>) => <Component {...props} isAnimationActive={false} />;
  return Unanimated as unknown as Series;
}

export function withFixedSize<T extends object>(recharts: T): T {
  function ResponsiveContainer({ children, height }: ContainerProps) {
    const size = { width: CHART_WIDTH, height: typeof height === "number" ? height : CHART_HEIGHT };
    return (
      <div style={size}>
        {isValidElement(children) ? cloneElement(children as React.ReactElement<typeof size>, size) : children}
      </div>
    );
  }
  const { Bar, Line, Area } = recharts as unknown as Record<"Bar" | "Line" | "Area", Series>;
  return {
    ...recharts,
    ResponsiveContainer,
    Bar: withoutAnimation(Bar),
    Line: withoutAnimation(Line),
    Area: withoutAnimation(Area),
  };
}
