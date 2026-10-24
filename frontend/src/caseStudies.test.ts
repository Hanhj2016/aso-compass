import { describe, expect, it } from "vitest";
import { DEFAULT_CASE, EDUCATIONAL_CASES, PUBLISHED_CASES, findCaseBySlug } from "./caseStudies";

describe("educational case manifest", () => {
  it("publishes only the versioned ALS fixture", () => {
    expect(EDUCATIONAL_CASES).toHaveLength(6);
    expect(PUBLISHED_CASES.map(caseStudy => caseStudy.slug)).toEqual(["als"]);
    expect(DEFAULT_CASE.teaching_candidates).toEqual(["SOD1", "TARDBP", "FUS"]);
    expect(DEFAULT_CASE.fixture_file).toBe("als-v4.1.json");
  });

  it("keeps unreviewed curriculum cases disconnected from fixture loading", () => {
    const planned = EDUCATIONAL_CASES.filter(caseStudy => caseStudy.status === "planned");
    expect(planned).toHaveLength(5);
    expect(planned.every(caseStudy => caseStudy.fixture_file === null && caseStudy.example_id === null)).toBe(true);
    expect(findCaseBySlug("huntington-disease")?.review_status).toBe("pending");
  });
});
