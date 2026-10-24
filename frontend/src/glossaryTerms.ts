export type TermDefinition = {
  label: string;
  plain: string;
  biology: string;
  app: string;
  mistake: string;
};

export const TERMS = {
  loeuf: {
    label: "LOEUF",
    plain: "A population-based estimate of how tolerant a gene is to loss-of-function variants; lower values indicate less tolerance.",
    biology: "Genes depleted of loss-of-function variants in population data may be dosage-sensitive or important for normal function.",
    app: "ASO Compass uses LOEUF as safety context and a review flag. It does not choose the mechanism track.",
    mistake: "A low LOEUF does not prove that a target is undruggable, and a high LOEUF does not prove that knockdown is safe.",
  },
  gof: {
    label: "GoF",
    plain: "Gain of function: a variant gives a gene product increased, new, or abnormally active function.",
    biology: "Disease can arise from harmful activity rather than from too little normal function.",
    app: "A curated G2P GoF annotation can support a knockdown direction, subject to safety and manual review.",
    mistake: "GoF does not mean that every variant in the gene acts the same way or that full knockdown is safe.",
  },
  dn: {
    label: "DN",
    plain: "Dominant negative: an altered gene product interferes with the normal product.",
    biology: "One altered copy can disrupt the function of the product made by the unaffected copy.",
    app: "A curated G2P DN annotation can support a knockdown direction, but allele specificity and residual normal function still matter.",
    mistake: "DN is not simply another name for dominant inheritance, and it does not automatically justify non-selective knockdown.",
  },
  haploinsufficiency: {
    label: "haploinsufficiency",
    plain: "One working copy of a gene does not produce enough normal function.",
    biology: "Reducing functional dosage to roughly one copy can contribute to disease.",
    app: "ASO Compass treats dominant loss-of-function evidence as a warning against indiscriminate knockdown and as support for restoration-oriented review.",
    mistake: "It does not prove that upregulation or splice correction is feasible, effective, or safe.",
  },
  capped: {
    label: "evidence capped",
    plain: "The source contained more records than the run was configured to retrieve.",
    biology: "The observed evidence mixture may not represent the complete set of known records.",
    app: "ASO Compass marks the candidate for manual review and warns that calculated consequence fractions may be incomplete.",
    mistake: "Capped does not mean negative, low quality, or absent evidence; it means the retrieval was truncated.",
  },
  reviewStatus: {
    label: "review status",
    plain: "ClinVar's indication of the review and consensus supporting a submitted or aggregate classification.",
    biology: "Expert-panel review, multiple agreeing submitters, a single submitter, and conflicting submissions carry different evidentiary context.",
    app: "New ASO Compass runs retain the review-status text returned through Open Targets EVA and summarize its coverage. Older bundled examples may not contain it.",
    mistake: "A pathogenic label without its review status, condition, submitter evidence, and date should not be treated as equally certain in every context.",
  },
  lof: {
    label: "LoF",
    plain: "Loss of function: a variant is expected to reduce or remove normal gene-product function.",
    biology: "Loss of normal function may contribute to disease, but the effect depends on gene, allele, inheritance, transcript, and condition.",
    app: "ASO Compass uses categorized consequence counts and curated G2P mechanism evidence to infer a research direction.",
    mistake: "A predicted LoF consequence is not automatically a pathogenic classification or proof of haploinsufficiency.",
  },
} satisfies Record<string, TermDefinition>;

export type TermKey = keyof typeof TERMS;
