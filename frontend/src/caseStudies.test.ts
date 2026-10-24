import { describe, expect, it } from "vitest";
import { DEFAULT_CASE, EDUCATIONAL_CASES, PUBLISHED_CASES, findCaseBySlug } from "./caseStudies";

describe("educational case manifest", () => {
  it("publishes the six versioned educational fixtures", () => {
    expect(EDUCATIONAL_CASES).toHaveLength(6);
    expect(PUBLISHED_CASES).toHaveLength(6);
    expect(DEFAULT_CASE.teaching_candidates).toEqual(["SOD1", "TARDBP", "FUS"]);
    expect(DEFAULT_CASE.fixture_file).toBe("als-v4.1.json");
  });

  it("records a reviewed sparse-result exception without changing thresholds", () => {
    const huntington = findCaseBySlug("huntington-disease");
    expect(huntington?.review_status).toBe("published");
    expect(huntington?.teaching_candidates).toEqual(["HTT", "SLC2A3"]);
    expect(huntington?.candidate_count_exception).toMatch(/unchanged default thresholds/i);
  });
});
