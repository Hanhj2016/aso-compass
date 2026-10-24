import rawManifest from "./caseManifest.json";
import type { EducationalCase, EducationalCaseManifest } from "./types";

const manifest = rawManifest as EducationalCaseManifest;

if (manifest.schema_version !== "educational-case-manifest-v1") {
  throw new Error("Unsupported educational case manifest schema");
}

const seenSlugs = new Set<string>();
for (const caseStudy of manifest.cases) {
  if (seenSlugs.has(caseStudy.slug)) throw new Error(`Duplicate educational case slug: ${caseStudy.slug}`);
  seenSlugs.add(caseStudy.slug);
  if (caseStudy.status === "published") {
    if (!caseStudy.example_id || !caseStudy.fixture_file || !caseStudy.fixture_version || !caseStudy.engine_version || !caseStudy.reviewer || caseStudy.review_status !== "published" || Object.keys(caseStudy.source_releases).length === 0) {
      throw new Error(`Published educational case is incomplete: ${caseStudy.case_id}`);
    }
    if (caseStudy.teaching_candidates.length < 3 || caseStudy.teaching_candidates.length > 5) {
      throw new Error(`Published educational case must have three to five teaching candidates: ${caseStudy.case_id}`);
    }
  } else if (caseStudy.example_id || caseStudy.fixture_file || caseStudy.teaching_candidates.length > 0 || caseStudy.review_status !== "pending" || caseStudy.reviewer) {
    throw new Error(`Planned educational case exposes unreviewed fixture data: ${caseStudy.case_id}`);
  }
}

export const EDUCATIONAL_CASES: readonly EducationalCase[] = manifest.cases;
export const PUBLISHED_CASES = EDUCATIONAL_CASES.filter(caseStudy => caseStudy.status === "published");
const defaultCase = PUBLISHED_CASES[0];
if (!defaultCase) throw new Error("At least one published educational case is required");
export const DEFAULT_CASE: EducationalCase = defaultCase;

export function findCaseBySlug(slug: string | null): EducationalCase | undefined {
  return EDUCATIONAL_CASES.find(caseStudy => caseStudy.slug === slug);
}
