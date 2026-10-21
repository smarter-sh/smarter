import { describe, expect, it } from "vitest";

import { leafTree, lockedTree, stackademyTree } from "@/mocks/resourceTree";
import { branchIds, childId, countResources, depth, ROOT_ID } from "@/components/ResourceTree/tree";

describe("tree", () => {
  it("counts a resource that appears twice once", () => {
    // the Provider, and its Secret, are under the LLMClient and under its plugin.
    expect(countResources(stackademyTree)).toBe(9);
    expect(countResources(leafTree)).toBe(1);
  });

  it("counts a resource without a record locator", () => {
    expect(countResources({ ...leafTree, children: [{ ...leafTree, recordLocator: null }] })).toBe(2);
  });

  it("measures the levels below the root", () => {
    expect(depth(stackademyTree)).toBe(3);
    expect(depth(lockedTree)).toBe(1);
    expect(depth(leafTree)).toBe(0);
  });

  it("lists the resources that use others, except the root", () => {
    // Provider (0.2), SqlPlugin (0.3), its Provider (0.3.0) and its SqlConnection (0.3.1).
    expect(branchIds(stackademyTree)).toEqual(["0.2", "0.3", "0.3.0", "0.3.1"]);
    expect(branchIds(leafTree)).toEqual([]);
    expect(childId(ROOT_ID, 2)).toBe("0.2");
  });
});
