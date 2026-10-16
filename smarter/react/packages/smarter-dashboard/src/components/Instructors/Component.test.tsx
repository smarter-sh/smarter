import { render, screen, within } from "@testing-library/react";
import { describe, expect, it } from "vitest";

import Instructors from "@/components/Instructors/Component";

const CATALOG = "https://docs.smarter.sh/smarter-instructors/example-courses";

describe("Instructors", () => {
  it("links to the free course catalog and the instructor guide", () => {
    render(<Instructors />);
    const instructors = screen.getByRole("region", { name: "Instructors" });

    expect(within(instructors).getByRole("link", { name: "Browse the free courses" })).toHaveAttribute(
      "href",
      `${CATALOG}/index.html`,
    );
    expect(within(instructors).getByRole("link", { name: "Instructor Guide" })).toHaveAttribute(
      "href",
      "https://docs.smarter.sh/smarter-instructor.html",
    );
    expect(
      within(instructors)
        .getAllByRole("definition")
        .map((stat) => stat.textContent),
    ).toEqual(["21", "19", "2", "$0"]);
  });

  it("links each of the 21 courses once, ignoring the ribbon's hidden copy", () => {
    render(<Instructors />);
    const courses = within(screen.getByRole("navigation", { name: "Free courses" })).getAllByRole("link");

    expect(courses).toHaveLength(21);
    expect(new Set(courses.map((course) => course.getAttribute("href"))).size).toBe(21);
    expect(within(screen.getByRole("navigation")).getByRole("link", { name: "Kubernetes" })).toHaveAttribute(
      "href",
      `${CATALOG}/micro-courses/kubernetes.html`,
    );
  });
});
