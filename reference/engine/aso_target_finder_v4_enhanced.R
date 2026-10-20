# ==============================================================================
# ASO TARGET FINDER (v4)
#
# USAGE
#   1. source("aso_target_finder_v4.R")      # once per R session
#   2. run_aso("MONDO_0004976")              # any Open Targets disease ID
#
# Optional settings, e.g.:
#   run_aso("MONDO_0004976", min_score = 0.3, rows_to_show = 20, show_legend = TRUE)
#   res <- run_aso("MONDO_0004976")          # keep the tables: res$knockdown, res$shortlist ...
#
# DATA SOURCES (all queried live)
#   Open Targets Platform API
#     - gene-disease associations and scores
#     - gnomAD constraint (LOEUF)
#     - ClinVar variant records (datasource "eva")      -> mechanism from variant types
#     - Gene2Phenotype records                           -> mechanism and inheritance
#     - drug / clinical-candidate records                -> approved drugs, antisense/siRNA drugs
#   ClinicalTrials.gov API (v2)
#     - antisense / oligonucleotide / siRNA trials for the disease, matched to genes
#       by gene symbols appearing in trial titles, interventions and summaries
#
# GENE CATEGORIES
#   knockdown            Gene2Phenotype GoF / dominant-negative, or ClinVar mostly missense
#   splice/upregulation  Gene2Phenotype LoF, or ClinVar mostly truncating
#   ambiguous            mixed evidence
#   modifier             genetic association but no variant-level evidence in ClinVar
#                        or Gene2Phenotype (e.g. GWAS loci); mechanism and direction unknown
#   insufficient data    1-4 ClinVar variants, or no variant lookup
#
# Each run saves CSV files to a subfolder of the working directory named after the
# disease ID, so runs for different diseases never overwrite each other.
#
# OPTIONAL manual override: pass a data frame to `curated`, e.g.
#   run_aso("MONDO_0007739", curated = data.frame(
#     gene_symbol = "HTT", strategy = "knockdown", precedent = "your note here"))
#   strategy is "knockdown" or "splice". Use this for repeat-expansion genes, which
#   ClinVar and Gene2Phenotype cannot classify.
# ==============================================================================

packages_needed <- c("httr", "jsonlite", "dplyr", "digest")
for (pkg in packages_needed) {
  if (!requireNamespace(pkg, quietly = TRUE)) install.packages(pkg)
  library(pkg, character.only = TRUE)
}

# ==============================================================================
# NETWORK LAYER
# ==============================================================================
endpoint <- "https://api.platform.opentargets.org/api/v4/graphql"

# Retries transient failures, prevents hanging, and caches successful responses.
.aso_cache_stats <- new.env(parent = emptyenv())
.aso_cache_stats$hits <- 0L
.aso_cache_stats$misses <- 0L

post_query <- function(q, attempts = 5, timeout_seconds = 60) {
  cache_dir <- getOption("aso.cache_dir", NULL)
  refresh <- isTRUE(getOption("aso.refresh_cache", FALSE))
  ttl_hours <- as.numeric(getOption("aso.cache_ttl_hours", 24))
  cache_file <- NULL
  if (!is.null(cache_dir) && nzchar(cache_dir)) {
    dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)
    cache_file <- file.path(cache_dir, paste0(digest::digest(q, algo = "sha256"), ".json"))
    fresh <- file.exists(cache_file) &&
      as.numeric(difftime(Sys.time(), file.info(cache_file)$mtime, units = "hours")) <= ttl_hours
    if (fresh && !refresh) {
      .aso_cache_stats$hits <- .aso_cache_stats$hits + 1L
      return(paste(readLines(cache_file, warn = FALSE, encoding = "UTF-8"), collapse = "
"))
    }
  }
  .aso_cache_stats$misses <- .aso_cache_stats$misses + 1L
  res <- RETRY(
    "POST", endpoint,
    body = list(query = q), encode = "json",
    times = attempts, pause_base = 1, pause_min = 1, pause_cap = 12,
    timeout(timeout_seconds),
    user_agent("aso-target-finder-r/4.1-guided"),
    quiet = TRUE
  )
  if (status_code(res) != 200) {
    stop("HTTP Error after retries ", status_code(res), ": ",
         content(res, as = "text", encoding = "UTF-8"))
  }
  answer <- content(res, as = "text", encoding = "UTF-8")
  if (!is.null(cache_file)) writeLines(answer, cache_file, useBytes = TRUE)
  answer
}

# Parsed into data frames (flattened); used for tabular results
gql <- function(q) {
  parsed <- fromJSON(post_query(q), flatten = TRUE)
  if (!is.null(parsed$errors)) {
    stop("GraphQL error: ", paste(unlist(parsed$errors$message), collapse = " | "))
  }
  parsed$data
}

# Parsed into plain nested lists; used for introspection, drugs and Gene2Phenotype
gql_list <- function(q) {
  parsed <- fromJSON(post_query(q), simplifyVector = FALSE)
  if (!is.null(parsed$errors)) {
    msgs <- vapply(parsed$errors, function(e) as.character(e$message)[1], character(1))
    stop("GraphQL error: ", paste(msgs, collapse = " | "))
  }
  parsed$data
}

# ClinicalTrials.gov v2 REST API; returns the parsed JSON as nested lists
ct_query <- function(params, attempts = 5, timeout_seconds = 60) {
  cache_dir <- getOption("aso.cache_dir", NULL)
  refresh <- isTRUE(getOption("aso.refresh_cache", FALSE))
  ttl_hours <- as.numeric(getOption("aso.cache_ttl_hours", 24))
  key <- paste0("clinicaltrials-v2|", jsonlite::toJSON(params, auto_unbox = TRUE))
  cache_file <- NULL
  if (!is.null(cache_dir) && nzchar(cache_dir)) {
    dir.create(cache_dir, recursive = TRUE, showWarnings = FALSE)
    cache_file <- file.path(cache_dir, paste0("ct_", digest::digest(key, algo = "sha256"), ".json"))
    fresh <- file.exists(cache_file) &&
      as.numeric(difftime(Sys.time(), file.info(cache_file)$mtime, units = "hours")) <= ttl_hours
    if (fresh && !refresh) {
      .aso_cache_stats$hits <- .aso_cache_stats$hits + 1L
      txt <- paste(readLines(cache_file, warn = FALSE, encoding = "UTF-8"), collapse = "\n")
      return(fromJSON(txt, simplifyVector = FALSE))
    }
  }
  .aso_cache_stats$misses <- .aso_cache_stats$misses + 1L
  res <- RETRY(
    "GET", "https://clinicaltrials.gov/api/v2/studies", query = params,
    times = attempts, pause_base = 1, pause_min = 1, pause_cap = 12,
    timeout(timeout_seconds), user_agent("aso-target-finder-r/4.1-guided"), quiet = TRUE
  )
  if (status_code(res) != 200) stop("ClinicalTrials.gov HTTP Error after retries ", status_code(res))
  txt <- content(res, as = "text", encoding = "UTF-8")
  if (!is.null(cache_file)) writeLines(txt, cache_file, useBytes = TRUE)
  fromJSON(txt, simplifyVector = FALSE)
}

# ==============================================================================
# MAIN FUNCTION
# ==============================================================================
run_aso <- function(disease_id,
                    min_score        = 0.20,   # overall Open Targets association score
                    min_genetic      = 0.10,   # genetic_association score
                    loeuf_intolerant = 0.60,   # LOEUF below this = intolerant of LoF
                    use_variants     = TRUE,   # mechanism from ClinVar variant types
                    use_g2p          = TRUE,   # mechanism + inheritance from Gene2Phenotype
                    check_drugs      = TRUE,   # approved / clinical / antisense drugs (Open Targets)
                    check_trials     = TRUE,   # ASO trials (ClinicalTrials.gov)
                    exclude_approved = FALSE,  # drop genes that already have an approved drug
                    exclude_aso_precedent = FALSE,  # shortlist: drop genes with existing ASO drugs/trials
                    include_modifiers = TRUE,  # shortlist: also list modifier genes (after mechanism-called genes)
                    rows_to_show     = 40,     # rows printed per table (full lists go to CSV)
                    show_legend      = FALSE,  # print a column guide at the end
                    save_csv         = TRUE,
                    output_dir       = file.path(getwd(), disease_id),
                    curated          = NULL,
                    run_mode         = c("full", "quick"),
                    cache_dir        = file.path(getwd(), ".aso_cache"),
                    refresh_cache    = FALSE,
                    cache_ttl_hours  = 24) {

  t0 <- Sys.time()
  run_mode <- match.arg(run_mode)
  stopifnot(is.character(disease_id), length(disease_id) == 1)
  old_aso_options <- options(aso.cache_dir = cache_dir,
                             aso.refresh_cache = refresh_cache,
                             aso.cache_ttl_hours = cache_ttl_hours)
  on.exit(options(old_aso_options), add = TRUE)
  .aso_cache_stats$hits <- 0L
  .aso_cache_stats$misses <- 0L
  if (run_mode == "quick") {
    message("QUICK MODE: variant/drug enrichment is capped at 25 genes and is incomplete.")
  }
  disease_id <- gsub(":", "_", trimws(disease_id))   # accept MONDO:0004976 too
  if (missing(output_dir)) output_dir <- file.path(getwd(), disease_id)

  # optional manual override table
  if (is.null(curated)) {
    curated <- data.frame(gene_symbol = character(), strategy = character(),
                          precedent = character(), stringsAsFactors = FALSE)
  } else {
    for (nm in c("strategy", "precedent")) if (!(nm %in% names(curated))) curated[[nm]] <- NA_character_
    curated <- curated[, c("gene_symbol", "strategy", "precedent"), drop = FALSE]
  }

  # ---- fixed settings --------------------------------------------------------
  DISEASE_ID             <- disease_id
  MIN_ASSOCIATION_SCORE  <- min_score
  MIN_GENETIC_SCORE      <- min_genetic
  LOEUF_INTOLERANT       <- loeuf_intolerant
  MAX_GENES_FOR_VARIANTS <- if (run_mode == "quick") 25 else 300
  EVIDENCE_SIZE          <- 500
  MIN_VARIANTS           <- 5      # LoF + missense pathogenic records needed for a ClinVar call
  LOF_FRACTION_HIGH      <- 0.60   # >= this share of LoF variants -> likely LoF
  LOF_FRACTION_LOW       <- 0.25   # <= this share of LoF variants -> likely GoF
  SPLICE_SITE_FRACTION   <- 0.30   # splice-affecting share of LoF-type variants -> splice-correctable
  MAX_GENES_FOR_DRUGS    <- if (run_mode == "quick") 25 else 300
  PAGE_SIZE              <- 100
  TABLE_WIDTH            <- 130
  ROWS_TO_SHOW           <- rows_to_show
  # Open Targets lumps aptamers, defibrotide and other nucleic-acid drugs under
  # "Oligonucleotide". Only names that look like antisense / siRNA drugs count as
  # ASO precedent: INN stems -rsen (antisense) and -siran (siRNA), the words
  # antisense / siRNA, and Ionis development codes.
  ASO_NAME_PATTERN       <- "(rsen|siran)\\b|sirna|antisense|^ionis|^ion[- ]?[0-9]|^isis[- ]?[0-9]"
  DRUG_LIKE_TYPES        <- c("DRUG", "BIOLOGICAL", "GENETIC", "COMBINATION_PRODUCT")

  # ============================================================================
  # HELPERS
  # ============================================================================
  nz <- function(x, d = "") if (is.null(x) || length(x) == 0) d else x

  fetch_page <- function(idx, size = PAGE_SIZE) {
    q <- sprintf('{
      disease(efoId: "%s") {
        id
        name
        associatedTargets(page: { index: %d, size: %d }) {
          count
          rows {
            target { id approvedSymbol approvedName }
            score
            datatypeScores { id score }
          }
        }
      }
    }', DISEASE_ID, idx, size)
    d <- gql(q)$disease
    if (is.null(d)) {
      stop("Open Targets returned no disease for ID '", DISEASE_ID,
           "'. The ID is probably wrong. Search the disease on platform.opentargets.org ",
           "and copy the ID from the URL (e.g. MONDO_0004976).", call. = FALSE)
    }
    d
  }

  get_dt_score <- function(df, id) {
    if (!is.data.frame(df) || nrow(df) == 0) return(0)
    v <- df$score[df$id == id]
    if (length(v) == 0 || is.na(v[1])) 0 else as.numeric(v[1])
  }

  # Open Targets data release (for reproducibility)
  fetch_ot_version <- function() {
    tryCatch({
      v <- gql_list("{ meta { dataVersion { year month iteration } } }")$meta$dataVersion
      paste(Filter(Negate(is.null), list(v$year, v$month, v$iteration)), collapse = ".")
    }, error = function(e) "unknown")
  }

  # LOEUF (gnomAD LoF oe upper bound) for a batch of Ensembl IDs
  fetch_constraint <- function(ids) {
    ids_json <- paste0('"', ids, '"', collapse = ",")
    q <- sprintf('{ targets(ensemblIds: [%s]) {
      id
      geneticConstraint { constraintType oeUpper }
    } }', ids_json)
    tryCatch({
      t <- gql(q)$targets
      if (is.null(t) || nrow(t) == 0) stop("empty")
      data.frame(
        ensembl_id = t$id,
        loeuf = sapply(t$geneticConstraint, function(df) {
          if (!is.data.frame(df) || nrow(df) == 0) return(NA_real_)
          v <- df$oeUpper[df$constraintType == "lof"]
          if (length(v) == 0) NA_real_ else as.numeric(v[1])
        }),
        stringsAsFactors = FALSE
      )
    }, error = function(e) {
      message("Constraint lookup failed for a batch: ", conditionMessage(e))
      data.frame(ensembl_id = ids, loeuf = NA_real_, stringsAsFactors = FALSE)
    })
  }

  # --- Sequence Ontology terms used to bucket ClinVar variant consequences ----
  LOF_SO_IDS      <- c("SO_0001587", "SO_0001589", "SO_0001574", "SO_0001575",
                       "SO_0002012", "SO_0001893")
  LOF_LABELS      <- c("stop gained", "frameshift variant", "splice acceptor variant",
                       "splice donor variant", "start lost", "transcript ablation")
  SPLICE_SO_IDS   <- c("SO_0001574", "SO_0001575")
  SPLICE_LABELS   <- c("splice acceptor variant", "splice donor variant")
  # Non-canonical splice-affecting variants (not counted as LoF, but many are
  # correctable with splice-switching ASOs): splice region, donor 5th base,
  # donor region, polypyrimidine tract, and intronic (e.g. deep intronic cryptic exons)
  SPLICE_EXTRA_SO_IDS <- c("SO_0001630", "SO_0001787", "SO_0002170", "SO_0002169", "SO_0001627")
  SPLICE_EXTRA_LABELS <- c("splice region variant", "splice donor 5th base variant",
                           "splice donor region variant", "splice polypyrimidine tract variant",
                           "intron variant")
  MISSENSE_SO_IDS <- c("SO_0001583", "SO_0001821", "SO_0001822")
  MISSENSE_LABELS <- c("missense variant", "inframe insertion", "inframe deletion",
                       "protein altering variant")

  col_or_na <- function(df, nm) {
    if (nm %in% names(df)) as.character(df[[nm]]) else rep(NA_character_, nrow(df))
  }

  # Count pathogenic / likely pathogenic ClinVar variants by consequence for one gene
  fetch_variant_counts <- function(ens_id) {
    q <- sprintf('{
      disease(efoId: "%s") {
        evidences(ensemblIds: ["%s"], enableIndirect: true,
                  datasourceIds: ["eva"], size: %d) {
          count
          rows {
            variantFunctionalConsequence { id label }
            clinicalSignificances
          }
        }
      }
    }', DISEASE_ID, ens_id, EVIDENCE_SIZE)

    ev <- gql(q)$disease$evidences
    zero <- data.frame(ensembl_id = ens_id, n_evidence = 0,
                       n_evidence_returned = 0, evidence_truncated = FALSE,
                       n_lof = 0, n_splice = 0, n_splice_extra = 0, n_missense = 0,
                       stringsAsFactors = FALSE)
    if (is.null(ev)) return(zero)

    total <- if (is.null(ev$count)) 0 else as.numeric(ev$count)
    rows  <- ev$rows
    if (!is.data.frame(rows) || nrow(rows) == 0) {
      zero$n_evidence <- total
      zero$evidence_truncated <- total > 0
      return(zero)
    }

    is_path <- if ("clinicalSignificances" %in% names(rows)) {
      sapply(rows$clinicalSignificances, function(x) {
        any(grepl("^(likely )?pathogenic", tolower(trimws(as.character(x)))))
      })
    } else {
      rep(TRUE, nrow(rows))
    }

    so_id  <- gsub(":", "_", col_or_na(rows, "variantFunctionalConsequence.id"))[is_path]
    so_lab <- tolower(gsub("_", " ", col_or_na(rows, "variantFunctionalConsequence.label")))[is_path]

    is_lof    <- so_id %in% LOF_SO_IDS          | so_lab %in% LOF_LABELS
    is_splice <- so_id %in% SPLICE_SO_IDS       | so_lab %in% SPLICE_LABELS
    is_extra  <- so_id %in% SPLICE_EXTRA_SO_IDS | so_lab %in% SPLICE_EXTRA_LABELS
    is_mis    <- so_id %in% MISSENSE_SO_IDS     | so_lab %in% MISSENSE_LABELS

    data.frame(ensembl_id = ens_id, n_evidence = total,
               n_evidence_returned = nrow(rows),
               evidence_truncated = total > nrow(rows),
               n_lof = sum(is_lof), n_splice = sum(is_splice),
               n_splice_extra = sum(is_extra),
               n_missense = sum(is_mis), stringsAsFactors = FALSE)
  }

  # --- Gene2Phenotype: curated mechanism and inheritance ------------------------
  # Per gene: mechanism (LoF / GoF-DN / mixed) from the variant consequence recorded
  # by Gene2Phenotype, and inheritance (recessive / dominant / both) from the allelic
  # requirement. Batched: one request per 25 genes.
  fetch_g2p_batch <- function(ids) {
    ids_json <- paste0('"', ids, '"', collapse = ",")
    mk <- function(with_allelic) sprintf(
      '{ disease(efoId: "%s") { evidences(ensemblIds: [%s], enableIndirect: true,
          datasourceIds: ["gene2phenotype"], size: 500) {
          rows { target { id } variantFunctionalConsequence { id label } %s } } } }',
      DISEASE_ID, ids_json, if (with_allelic) "allelicRequirements" else "")
    ev <- tryCatch(gql_list(mk(TRUE)), error = function(e) gql_list(mk(FALSE)))
    rows <- ev$disease$evidences$rows
    if (length(rows) == 0) return(NULL)

    recs <- lapply(rows, function(r) {
      cons <- tolower(paste(nz(r$variantFunctionalConsequence$id),
                            nz(r$variantFunctionalConsequence$label)))
      allelic <- tolower(paste(unlist(r$allelicRequirements), collapse = " "))
      data.frame(
        ensembl_id = nz(r$target$id, NA_character_),
        is_lof     = grepl("so_0002054|so:0002054|loss.of.function", cons),
        is_gof_dn  = grepl("so_0002053|so:0002053|gain.of.function|so_0002052|so:0002052|dominant.negative", cons),
        is_biall   = grepl("biallelic", allelic),
        is_monoall = grepl("monoallelic", allelic),
        stringsAsFactors = FALSE)
    })
    d <- bind_rows(recs)
    d <- d[!is.na(d$ensembl_id), , drop = FALSE]
    if (nrow(d) == 0) return(NULL)
    do.call(rbind, lapply(split(d, d$ensembl_id), function(g) {
      data.frame(
        ensembl_id = g$ensembl_id[1],
        g2p_mech = if (any(g$is_lof) && any(g$is_gof_dn)) "mixed"
                   else if (any(g$is_lof)) "LoF"
                   else if (any(g$is_gof_dn)) "GoF/DN"
                   else NA_character_,
        inheritance = if (any(g$is_biall) && any(g$is_monoall)) "both"
                      else if (any(g$is_biall)) "recessive"
                      else if (any(g$is_monoall)) "dominant"
                      else NA_character_,
        stringsAsFactors = FALSE)
    }))
  }

  # --- Drug lookup (Open Targets) ----------------------------------------------
  # Open Targets has renamed its drug fields between releases, so the schema is
  # read live (introspection) and the query is built from the fields that exist.
  unwrap_type <- function(t) {
    while (!is.null(t) && is.null(t$name) && !is.null(t$ofType)) t <- t$ofType
    if (is.null(t) || is.null(t$name)) NA_character_ else as.character(t$name)
  }

  type_fields <- function(type_name) {
    q <- sprintf('{ __type(name: "%s") { fields { name type { kind name ofType { kind name ofType { kind name ofType { kind name } } } } } } }',
                 type_name)
    r <- gql_list(q)[["__type"]]
    if (is.null(r) || length(r$fields) == 0) return(character(0))
    nm <- vapply(r$fields, function(f) as.character(f$name), character(1))
    ty <- vapply(r$fields, function(f) unwrap_type(f$type), character(1))
    setNames(ty, nm)
  }

  stage_rank <- function(x) {
    if (is.null(x) || length(x) == 0) return(NA_real_)
    x <- x[[1]]
    if (is.null(x) || is.na(x)) return(NA_real_)
    if (is.numeric(x)) return(min(floor(x), 4))
    s <- toupper(as.character(x))
    if (grepl("APPROV|MARKET", s)) return(4)
    d <- suppressWarnings(as.numeric(unlist(regmatches(s, gregexpr("[0-9]+", s)))))
    if (length(d) > 0) return(min(max(d), 4))
    if (grepl("PRECLIN|EARLY|UNKNOWN|NOT", s)) return(0)
    NA_real_
  }

  stage_label <- function(r) {
    if (is.na(r)) "Unknown stage"
    else if (r >= 4) "Approved"
    else if (r >= 3) "Phase 3"
    else if (r >= 2) "Phase 2"
    else if (r >= 1) "Phase 1"
    else "Early"
  }

  best_stage <- function(rk) if (all(is.na(rk))) NA_real_ else max(rk, na.rm = TRUE)

  # One row of drug info for one gene, from a list of Open Targets drug records
  summarise_drug_rows <- function(rows) {
    empty <- data.frame(n_drugs = 0, drug_max_stage = NA_character_,
                        drug_status = "None found", approved_drugs = "",
                        has_approved_drug = FALSE, oligo_drug = "-", oligo_names = "",
                        aso_drug = "-", aso_names = "",
                        stringsAsFactors = FALSE)
    if (length(rows) == 0) return(empty)

    recs <- lapply(rows, function(r) {
      d  <- r[["drug"]]
      nm <- if (is.null(d[["name"]])) NA_character_ else as.character(d[["name"]])
      ty <- if (is.null(d[["drugType"]])) "" else as.character(d[["drugType"]])
      ranks <- c(stage_rank(r[["maxClinicalStage"]]), stage_rank(r[["clinicalStage"]]),
                 stage_rank(r[["phase"]]), stage_rank(d[["maximumClinicalStage"]]),
                 stage_rank(d[["maximumClinicalTrialPhase"]]))
      if (isTRUE(d[["isApproved"]])) ranks <- c(ranks, 4)
      data.frame(name = nm, type = ty, rank = best_stage(ranks), stringsAsFactors = FALSE)
    })
    recs <- bind_rows(recs)
    recs <- recs[!is.na(recs$name), , drop = FALSE]
    if (nrow(recs) == 0) return(empty)

    per_drug <- do.call(rbind, lapply(split(recs, recs$name), function(g) {
      data.frame(name = g$name[1], type = g$type[1], rank = best_stage(g$rank),
                 stringsAsFactors = FALSE)
    }))

    top <- best_stage(per_drug$rank)
    top_names <- if (is.na(top)) per_drug$name else per_drug$name[!is.na(per_drug$rank) & per_drug$rank == top]
    shown <- paste(head(top_names, 2), collapse = ", ")
    if (length(top_names) > 2) shown <- paste0(shown, " (+", length(top_names) - 2, ")")

    is_oligo <- grepl("oligonucleotide|antisense|sirna", tolower(per_drug$type))
    is_aso   <- is_oligo & grepl(ASO_NAME_PATTERN, tolower(per_drug$name))
    approved_names <- per_drug$name[!is.na(per_drug$rank) & per_drug$rank >= 4]

    data.frame(
      n_drugs           = nrow(per_drug),
      drug_max_stage    = stage_label(top),
      drug_status       = paste0(stage_label(top), ": ", shown),
      approved_drugs    = paste(head(approved_names, 5), collapse = "; "),
      has_approved_drug = length(approved_names) > 0,
      oligo_drug        = if (any(is_oligo)) stage_label(best_stage(per_drug$rank[is_oligo])) else "-",
      oligo_names       = if (any(is_oligo)) paste(head(per_drug$name[is_oligo], 2), collapse = ", ") else "",
      aso_drug          = if (any(is_aso)) stage_label(best_stage(per_drug$rank[is_aso])) else "-",
      aso_names         = if (any(is_aso)) paste(head(per_drug$name[is_aso], 2), collapse = ", ") else "",
      stringsAsFactors  = FALSE
    )
  }

  fetch_drugs_batch <- function(ids, setup) {
    ids_json <- paste0('"', ids, '"', collapse = ",")
    q <- sprintf('{ targets(ensemblIds: [%s]) { id %s } }', ids_json, setup$selection)
    res <- gql_list(q)$targets
    out <- lapply(res, function(t) {
      field <- t[[setup$field]]
      rows  <- if (is.null(field)) list() else field$rows
      cbind(data.frame(ensembl_id = t$id, stringsAsFactors = FALSE),
            summarise_drug_rows(rows))
    })
    bind_rows(out)
  }

  discover_drug_query <- function() {
    tf <- type_fields("Target")
    if (length(tf) == 0) stop("schema introspection returned nothing")

    field <- NULL
    if ("drugAndClinicalCandidates" %in% names(tf)) {
      field <- "drugAndClinicalCandidates"; args <- c("", "(size: 500)")
    } else if ("knownDrugs" %in% names(tf)) {
      field <- "knownDrugs"; args <- c("(size: 200)", "")
    } else {
      stop("Target has neither drugAndClinicalCandidates nor knownDrugs")
    }

    top_fields <- type_fields(tf[[field]])
    if (!("rows" %in% names(top_fields))) stop("no 'rows' field under ", field)
    rf <- type_fields(top_fields[["rows"]])
    if (!("drug" %in% names(rf))) stop("no 'drug' field in ", field, " rows")
    df <- type_fields(rf[["drug"]])

    row_scalars <- intersect(c("maxClinicalStage", "clinicalStage", "phase", "status"), names(rf))
    drug_fields <- intersect(c("id", "name", "drugType", "maximumClinicalStage",
                               "maximumClinicalTrialPhase", "isApproved"), names(df))
    if (!("name" %in% drug_fields)) stop("drug type has no 'name' field")

    probe_id <- "ENSG00000142168"   # SOD1
    for (a in args) {
      sel <- sprintf("%s%s { rows { %s drug { %s } } }",
                     field, a, paste(row_scalars, collapse = " "), paste(drug_fields, collapse = " "))
      setup <- list(field = field, selection = sel, label = paste0("Target.", field))
      ok <- tryCatch({ fetch_drugs_batch(probe_id, setup); TRUE }, error = function(e) FALSE)
      if (ok) return(setup)
    }
    stop("none of the generated drug queries were accepted by the API")
  }

  # --- ClinicalTrials.gov: ASO trials for the condition -------------------------
  parse_trial <- function(s) {
    ps   <- s$protocolSection
    idm  <- ps$identificationModule
    phases <- toupper(as.character(unlist(ps$designModule$phases)))
    nums <- gsub("[^0-9]", "", phases); nums <- nums[nzchar(nums)]
    ints <- nz(ps$armsInterventionsModule$interventions, list())
    int_names <- as.character(unlist(lapply(ints, function(i) c(nz(i$name), unlist(i$otherNames)))))
    int_types <- toupper(as.character(unlist(lapply(ints, function(i) nz(i$type, NA_character_)))))
    # A "drug trial" has at least one drug-like intervention (or interventions with no
    # type recorded). Sampling, in-vitro and observational studies are not drug trials.
    is_drug <- length(ints) > 0 && (all(is.na(int_types)) || any(int_types %in% DRUG_LIKE_TYPES))
    list(
      nct    = nz(idm$nctId),
      title  = nz(idm$briefTitle),
      status = tolower(gsub("_", " ", nz(ps$statusModule$overallStatus, "unknown"))),
      phase  = if (length(nums)) paste0("Ph", paste(nums, collapse = "/")) else "Ph?",
      phase_max = if (length(nums)) max(as.numeric(nums)) else NA_real_,
      is_drug = is_drug,
      interventions = paste(unique(int_names[nzchar(int_names)]), collapse = ", "),
      text   = paste(nz(idm$briefTitle), nz(idm$officialTitle), paste(int_names, collapse = " ")),
      summary = nz(ps$descriptionModule$briefSummary)
    )
  }

  fetch_aso_trials <- function(condition, max_pages = 5) {
    studies <- list(); token <- NULL
    for (p in seq_len(max_pages)) {
      params <- list(`query.cond` = condition,
                     `query.term` = "antisense OR oligonucleotide OR siRNA",
                     pageSize = 100, format = "json")
      if (!is.null(token)) params$pageToken <- token
      js <- ct_query(params)
      studies <- c(studies, js$studies)
      token <- js$nextPageToken
      if (is.null(token)) break
    }
    lapply(studies, parse_trial)
  }

  # Match gene symbols to trials. Strong match: exact (or all-caps) word in the title or
  # intervention names. Weak match: named only in the brief summary.
  match_trials_to_genes <- function(trials, symbols) {
    syms   <- unique(symbols[nchar(symbols) >= 3 & grepl("^[A-Za-z0-9]+$", symbols)])
    sym_up <- toupper(syms)
    tok <- function(x) { t <- unique(unlist(strsplit(x, "[^A-Za-z0-9]+"))); t[nzchar(t)] }
    lapply(trials, function(t) {
      st <- tok(t$text); wk <- tok(t$summary)
      strong <- syms[(syms %in% st) | (sym_up %in% st)]
      weak   <- setdiff(syms[(syms %in% wk) | (sym_up %in% wk)], strong)
      list(strong = strong, weak = weak)
    })
  }

  # --- Text-table printing (plain ASCII so it renders in any R console) --------
  fmt_num   <- function(x, d = 2) ifelse(is.na(x), "-", formatC(x, format = "f", digits = d))
  trunc_str <- function(x, n) {
    x <- as.character(x)
    ifelse(!is.na(x) & nchar(x) > n, paste0(substr(x, 1, n - 3), "..."), x)
  }

  text_table <- function(tab, right = character(0), indent = "  ") {
    tab[] <- lapply(tab, as.character)
    tab[] <- lapply(tab, function(x) ifelse(is.na(x) | x == "", "-", x))
    w <- vapply(seq_along(tab), function(i) max(nchar(tab[[i]]), nchar(names(tab)[i])), numeric(1))
    pad <- function(x, wd, r) format(x, width = wd, justify = if (r) "right" else "left")
    hdr <- paste(vapply(seq_along(tab), function(i) pad(names(tab)[i], w[i], names(tab)[i] %in% right), ""), collapse = "  ")
    rule <- paste(vapply(w, function(wd) strrep("-", wd), ""), collapse = "  ")
    cat(indent, hdr, "\n", indent, rule, "\n", sep = "")
    for (r in seq_len(nrow(tab))) {
      cells <- vapply(seq_along(tab), function(i) pad(tab[[i]][r], w[i], names(tab)[i] %in% right), "")
      cat(indent, paste(cells, collapse = "  "), "\n", sep = "")
    }
  }

  banner <- function(title, sub = NULL) {
    cat("\n", strrep("=", TABLE_WIDTH), "\n", title, "\n", sep = "")
    if (!is.null(sub)) cat(sub, "\n", sep = "")
    cat(strrep("-", TABLE_WIDTH), "\n", sep = "")
  }

  join_parts <- function(...) {
    p <- list(...)
    vapply(seq_along(p[[1]]), function(i)
      paste(Filter(nzchar, vapply(p, function(x) { v <- as.character(x[i]); if (is.na(v)) "" else v }, "")),
            collapse = " | "), "")
  }

  # ============================================================================
  # 1. FETCH ASSOCIATIONS
  # ============================================================================
  message("[1/6] Fetching gene associations for ", DISEASE_ID, " ...")
  first <- fetch_page(0)
  disease_name <- first$name
  total        <- first$associatedTargets$count
  if (is.null(total) || total == 0) stop("0 associated targets found for ", DISEASE_ID, call. = FALSE)

  n_pages  <- ceiling(total / PAGE_SIZE)
  all_rows <- vector("list", n_pages)
  all_rows[[1]] <- first$associatedTargets$rows
  if (n_pages > 1) {
    for (i in 2:n_pages) {
      all_rows[[i]] <- fetch_page(i - 1)$associatedTargets$rows
      if (i %% 10 == 0) message("      page ", i, " of ", n_pages)
      Sys.sleep(0.3)
    }
  }
  rows <- bind_rows(all_rows)

  master <- data.frame(
    gene_symbol   = rows$target.approvedSymbol,
    gene_name     = rows$target.approvedName,
    ensembl_id    = rows$target.id,
    overall_score = as.numeric(rows$score),
    genetic_score = sapply(rows$datatypeScores, get_dt_score, id = "genetic_association"),
    stringsAsFactors = FALSE
  ) %>%
    filter(overall_score >= MIN_ASSOCIATION_SCORE,
           genetic_score >= MIN_GENETIC_SCORE) %>%
    arrange(desc(overall_score))

  if (nrow(master) == 0) {
    stop("No genes passed the score thresholds. Lower min_score / min_genetic and retry.", call. = FALSE)
  }
  message("      ", total, " genes linked; ", nrow(master), " pass the score filters")

  ot_version <- fetch_ot_version()

  # ============================================================================
  # 2. CONSTRAINT (LOEUF)
  # ============================================================================
  message("[2/6] Fetching gene constraint (LOEUF) ...")
  batches <- split(master$ensembl_id, ceiling(seq_along(master$ensembl_id) / 50))
  constraint <- bind_rows(lapply(batches, function(b) { Sys.sleep(0.2); fetch_constraint(b) }))
  if (all(is.na(constraint$loeuf))) {
    warning("No LOEUF values were retrieved. The constraint query may have failed ",
            "or the Open Targets schema changed. LoF-tolerance flags will be unknown.")
  }

  # ============================================================================
  # 3. CLINVAR VARIANT-BASED MECHANISM
  # ============================================================================
  variant_tbl <- data.frame(ensembl_id = character(), n_evidence = numeric(),
                            n_evidence_returned = numeric(), evidence_truncated = logical(),
                            n_lof = numeric(), n_splice = numeric(), n_splice_extra = numeric(),
                            n_missense = numeric(), stringsAsFactors = FALSE)
  if (use_variants) {
    ids <- head(master$ensembl_id, MAX_GENES_FOR_VARIANTS)
    message("[3/6] Classifying mechanism from ClinVar variants (", length(ids), " genes, a few minutes) ...")
    results <- vector("list", length(ids))
    first_error <- NULL
    for (i in seq_along(ids)) {
      results[[i]] <- tryCatch(fetch_variant_counts(ids[i]), error = function(e) {
        if (is.null(first_error)) first_error <<- conditionMessage(e)
        NULL
      })
      if (i %% 25 == 0) message("      ", i, " / ", length(ids))
      Sys.sleep(0.2)
    }
    got <- results[!sapply(results, is.null)]
    if (length(got) > 0) variant_tbl <- bind_rows(got)
    if (!is.null(first_error)) {
      warning("Variant lookup failed for some genes. First error: ", first_error)
    }
    if (nrow(variant_tbl) == 0) {
      warning("No ClinVar variant data retrieved. Genes will rely on Gene2Phenotype or be 'insufficient data'.")
    } else if (all(variant_tbl$n_lof + variant_tbl$n_missense == 0)) {
      warning("Variant queries ran but no LoF/missense variants were counted. ",
              "The evidence field names may differ in the current Open Targets schema.")
    }
    n_truncated <- sum(variant_tbl$evidence_truncated %in% TRUE, na.rm = TRUE)
    if (n_truncated > 0) {
      warning(n_truncated, " gene(s) exceeded the per-gene EVA evidence cap of ",
              EVIDENCE_SIZE, ". Consequence fractions use only returned rows; ",
              "inspect evidence_truncated before interpretation.")
    }
  } else {
    message("[3/6] Skipping ClinVar variant classification")
  }

  # ============================================================================
  # 4. GENE2PHENOTYPE MECHANISM + INHERITANCE
  # ============================================================================
  g2p_tbl <- data.frame(ensembl_id = character(), g2p_mech = character(),
                        inheritance = character(), stringsAsFactors = FALSE)
  if (use_g2p) {
    message("[4/6] Fetching Gene2Phenotype mechanism and inheritance ...")
    ids <- head(master$ensembl_id, MAX_GENES_FOR_VARIANTS)
    gbatches <- split(ids, ceiling(seq_along(ids) / 25))
    g_err <- NULL
    gres <- lapply(gbatches, function(b) {
      Sys.sleep(0.2)
      tryCatch(fetch_g2p_batch(b), error = function(e) {
        if (is.null(g_err)) g_err <<- conditionMessage(e)
        NULL
      })
    })
    gres <- gres[!sapply(gres, is.null)]
    if (length(gres) > 0) g2p_tbl <- bind_rows(gres)
    if (!is.null(g_err)) warning("Gene2Phenotype lookup failed for some batches. First error: ", g_err)
    message("      Gene2Phenotype records found for ", nrow(g2p_tbl),
            " genes (0 is normal for diseases it does not cover)")
  } else {
    message("[4/6] Skipping Gene2Phenotype")
  }

  # ============================================================================
  # 5. DRUG LOOKUP (Open Targets)
  # ============================================================================
  drug_tbl <- data.frame(ensembl_id = character(), n_drugs = numeric(),
                         drug_max_stage = character(), drug_status = character(),
                         approved_drugs = character(), has_approved_drug = logical(),
                         oligo_drug = character(), oligo_names = character(),
                         aso_drug = character(), aso_names = character(),
                         stringsAsFactors = FALSE)
  drug_source <- "not checked"

  if (check_drugs) {
    message("[5/6] Looking up approved / clinical drugs ...")
    setup <- tryCatch(discover_drug_query(), error = function(e) {
      warning("Drug lookup could not be set up: ", conditionMessage(e),
              ". Drug columns will say 'lookup failed'.")
      NULL
    })
    if (!is.null(setup)) {
      ids <- head(master$ensembl_id, MAX_GENES_FOR_DRUGS)
      dbatches <- split(ids, ceiling(seq_along(ids) / 25))
      dres <- lapply(dbatches, function(b) {
        Sys.sleep(0.2)
        tryCatch(fetch_drugs_batch(b, setup), error = function(e) {
          message("Drug lookup failed for a batch: ", conditionMessage(e)); NULL
        })
      })
      dres <- dres[!sapply(dres, is.null)]
      if (length(dres) > 0) {
        drug_tbl    <- bind_rows(dres)
        drug_source <- setup$label
      } else {
        warning("Drug lookup returned no data for any batch.")
        drug_source <- "lookup failed"
      }
    } else {
      drug_source <- "lookup failed"
    }
  } else {
    message("[5/6] Skipping drug lookup")
  }

  # ============================================================================
  # 6. CLINICALTRIALS.GOV: ASO TRIALS
  # ============================================================================
  trials_tbl  <- data.frame()
  gene_trials <- data.frame(gene_symbol = character(), aso_trial_n = numeric(),
                            aso_trial_weak = numeric(), aso_trial_best = character(),
                            aso_trial_ids = character(), stringsAsFactors = FALSE)
  trial_source <- "not checked"

  if (check_trials) {
    message("[6/6] Searching ClinicalTrials.gov for antisense / oligonucleotide trials ...")
    trials <- tryCatch(fetch_aso_trials(disease_name), error = function(e) {
      warning("ClinicalTrials.gov lookup failed: ", conditionMessage(e)); NULL
    })
    if (is.null(trials)) {
      trial_source <- "lookup failed"
    } else {
      trial_source <- sprintf("%d studies", length(trials))
      if (length(trials) > 0) {
        hits <- match_trials_to_genes(trials, master$gene_symbol)
        pm   <- vapply(trials, function(t) t$phase_max, numeric(1))
        ord  <- order(-ifelse(is.na(pm), -1, pm))      # most advanced phase first
        trials <- trials[ord]; hits <- hits[ord]
        trials_tbl <- data.frame(
          nct    = vapply(trials, function(t) t$nct, ""),
          phase  = vapply(trials, function(t) t$phase, ""),
          status = vapply(trials, function(t) t$status, ""),
          type   = vapply(trials, function(t) if (t$is_drug) "drug" else "non-drug", ""),
          genes  = vapply(hits, function(h) paste(c(h$strong, if (length(h$weak)) paste0(h$weak, "?")), collapse = ", "), ""),
          interventions = vapply(trials, function(t) t$interventions, ""),
          title  = vapply(trials, function(t) t$title, ""),
          stringsAsFactors = FALSE)

        # gene-level ASO precedent counts drug trials only
        drug_idx  <- which(vapply(trials, function(t) t$is_drug, logical(1)))
        genes_all <- unique(unlist(lapply(drug_idx, function(i) c(hits[[i]]$strong, hits[[i]]$weak))))
        if (length(genes_all) > 0) {
          gene_trials <- do.call(rbind, lapply(genes_all, function(g) {
            idx <- drug_idx[vapply(drug_idx, function(i) g %in% c(hits[[i]]$strong, hits[[i]]$weak), logical(1))]
            n_weak <- sum(vapply(idx, function(i) !(g %in% hits[[i]]$strong), logical(1)))
            best <- idx[1]   # sorted by phase, so the first hit is the most advanced
            data.frame(gene_symbol = g, aso_trial_n = length(idx), aso_trial_weak = n_weak,
                       aso_trial_best = paste(trials[[best]]$phase, trials[[best]]$status),
                       aso_trial_ids = paste(head(vapply(idx, function(i) trials[[i]]$nct, ""), 3), collapse = ", "),
                       stringsAsFactors = FALSE)
          }))
        }
      }
    }
  } else {
    message("[6/6] Skipping ClinicalTrials.gov")
  }

  # ============================================================================
  # COMBINE, CALL MECHANISM, ASSIGN TRACKS
  # ============================================================================
  message("Building report ...")
  master <- master %>%
    left_join(constraint,  by = "ensembl_id") %>%
    left_join(variant_tbl, by = "ensembl_id") %>%
    left_join(g2p_tbl,     by = "ensembl_id") %>%
    left_join(drug_tbl,    by = "ensembl_id") %>%
    left_join(gene_trials, by = "gene_symbol") %>%
    left_join(curated,     by = "gene_symbol") %>%
    mutate(
      drug_status = ifelse(is.na(drug_status),
                           ifelse(drug_source == "lookup failed", "lookup failed", "not checked"),
                           drug_status),
      lof_intolerant = !is.na(loeuf) & loeuf < LOEUF_INTOLERANT,
      lof_tolerance  = case_when(
        is.na(loeuf)   ~ "unknown",
        lof_intolerant ~ "LoF-intolerant",
        TRUE           ~ "LoF-tolerant"
      ),
      n_classified        = n_lof + n_missense,
      frac_lof            = ifelse(!is.na(n_classified) & n_classified > 0,
                                   n_lof / n_classified, NA_real_),
      # splice-affecting share: canonical + non-canonical splice variants over LoF-type + non-canonical
      frac_splice_related = ifelse(!is.na(n_lof) & !is.na(n_splice_extra) & (n_lof + n_splice_extra) > 0,
                                   (n_splice + n_splice_extra) / (n_lof + n_splice_extra), NA_real_),
      no_variant_evidence = !is.na(n_classified) & n_classified == 0 &
                            !is.na(n_splice_extra) & n_splice_extra == 0,
      clinvar_call = case_when(
        is.na(n_classified) | n_classified < MIN_VARIANTS ~ "insufficient data",
        frac_lof >= LOF_FRACTION_HIGH                     ~ "splice/upregulation",
        frac_lof <= LOF_FRACTION_LOW                      ~ "knockdown",
        TRUE                                              ~ "ambiguous"
      ),
      g2p_call = case_when(
        g2p_mech %in% "LoF"    ~ "splice/upregulation",
        g2p_mech %in% "GoF/DN" ~ "knockdown",
        g2p_mech %in% "mixed"  ~ "ambiguous",
        TRUE                   ~ NA_character_
      ),
      # precedence: manual override > Gene2Phenotype > ClinVar counts > modifier
      final_call = case_when(
        strategy %in% "knockdown" ~ "knockdown",
        strategy %in% "splice"    ~ "splice/upregulation",
        !is.na(g2p_call)          ~ g2p_call,
        no_variant_evidence       ~ "modifier",
        TRUE                      ~ clinvar_call
      ),
      call_source = case_when(
        !is.na(strategy)        ~ "curated",
        !is.na(g2p_call)        ~ "G2P",
        final_call == "modifier" ~ "assoc only",
        TRUE                    ~ "ClinVar"
      ),
      splice_correctable = final_call == "splice/upregulation" &
        !is.na(frac_splice_related) & frac_splice_related >= SPLICE_SITE_FRACTION,
      flag = case_when(
        is.na(strategy) & !is.na(g2p_call) & clinvar_call != "insufficient data" &
          clinvar_call != g2p_call                                              ~ "ClinVar and G2P disagree",
        final_call == "knockdown" & inheritance %in% "recessive"                ~ "recessive (G2P): knockdown unlikely to help",
        final_call == "knockdown" & lof_intolerant                              ~ "LoF-intolerant: full knockdown risky",
        final_call == "splice/upregulation" & inheritance %in% "recessive"      ~ "recessive LoF (G2P); do not knock down",
        final_call == "splice/upregulation" & inheritance %in% "dominant" & lof_intolerant ~ "dominant LoF (G2P): haploinsufficiency",
        final_call == "splice/upregulation" & inheritance %in% "dominant"       ~ "dominant LoF (G2P)",
        final_call == "splice/upregulation" & is.na(inheritance) & lof_tolerance == "LoF-tolerant" ~ "likely recessive LoF; do not knock down",
        final_call == "splice/upregulation" & is.na(inheritance) & lof_intolerant ~ "possible haploinsufficiency",
        final_call == "modifier"                                                ~ "association only; effect direction unknown",
        TRUE                                                                    ~ ""
      ),
      note = case_when(
        final_call == "knockdown" & lof_intolerant ~
          "Caution: LoF-intolerant gene. Full knockdown may be toxic; consider partial or allele-specific.",
        final_call == "knockdown" ~
          "Knockdown plausible if disease mechanism is toxic gain of function.",
        final_call == "splice/upregulation" & lof_tolerance == "LoF-tolerant" ~
          "Likely recessive LoF. Do NOT knock down. Splice correction only if variants affect splicing.",
        final_call == "splice/upregulation" & lof_intolerant ~
          "Likely haploinsufficiency. Upregulation or splice correction.",
        final_call == "splice/upregulation" ~
          "Likely LoF disease; no constraint data.",
        final_call == "ambiguous" ~
          "Mixed evidence. Mechanism unclear; review manually.",
        final_call == "modifier" ~
          "Genetic association without variant-level evidence (e.g. a GWAS locus). Mechanism and direction of effect unknown; review the locus.",
        TRUE ~
          "Too little variant evidence. Classify manually (repeat expansions and non-coding mechanisms are invisible here)."
      ),
      aso_part = ifelse(!is.na(aso_drug) & aso_drug != "-",
                        paste0("Drug: ", ifelse(!is.na(aso_names) & aso_names != "", paste0(aso_names, " "), ""),
                               "(", aso_drug, ")"), ""),
      trial_part = ifelse(!is.na(aso_trial_n) & aso_trial_n > 0,
                          paste0("Trials: ", aso_trial_n, " (best ", aso_trial_best,
                                 ifelse(!is.na(aso_trial_weak) & aso_trial_weak > 0,
                                        paste0("; ", aso_trial_weak, " via summary text"), ""), ")"), ""),
      curated_part = ifelse(!is.na(precedent) & precedent != "", paste0("Manual: ", precedent), ""),
      aso_precedent = join_parts(aso_part, trial_part, curated_part),
      has_aso_precedent = nzchar(aso_precedent)
    ) %>%
    select(-aso_part, -trial_part, -curated_part)

  master <- master %>% mutate(
    confidence_tier = case_when(
      !is.na(strategy) ~ "Manual override—verify",
      evidence_truncated %in% TRUE ~ "Capped evidence—manual review",
      grepl("disagree", flag, ignore.case = TRUE) ~ "Conflicting evidence",
      !is.na(g2p_call) & clinvar_call == g2p_call ~ "Convergent G2P + ClinVar",
      !is.na(g2p_call) ~ "Gene2Phenotype evidence",
      final_call == "modifier" ~ "Association only",
      is.na(n_classified) | n_classified < MIN_VARIANTS ~ "Insufficient evidence",
      final_call == "ambiguous" ~ "Conflicting evidence",
      n_classified >= 20 & pmin(abs(frac_lof - LOF_FRACTION_LOW),
                                abs(frac_lof - LOF_FRACTION_HIGH)) >= 0.15 ~ "Strong heuristic evidence",
      n_classified >= 10 & pmin(abs(frac_lof - LOF_FRACTION_LOW),
                                abs(frac_lof - LOF_FRACTION_HIGH)) >= 0.05 ~ "Moderate heuristic evidence",
      TRUE ~ "Limited heuristic evidence"
    ),
    confidence_reason = case_when(
      !is.na(strategy) ~ "A user-supplied manual override determined the mechanism; verify its primary sources.",
      evidence_truncated %in% TRUE ~ "The EVA response exceeded the row cap; consequence fractions may be incomplete.",
      grepl("disagree", flag, ignore.case = TRUE) ~ "Gene2Phenotype and ClinVar imply different mechanism tracks.",
      !is.na(g2p_call) & clinvar_call == g2p_call ~ "Independent Gene2Phenotype and ClinVar classifications agree.",
      !is.na(g2p_call) ~ "The mechanism comes from Gene2Phenotype; review its allelic requirement and source panel.",
      final_call == "modifier" ~ "Association evidence exists, but direction and causal mechanism are unknown.",
      is.na(n_classified) | n_classified < MIN_VARIANTS ~ "Fewer than five classified pathogenic records were available.",
      final_call == "ambiguous" ~ "The LoF fraction lies between the automated mechanism thresholds.",
      confidence_tier == "Strong heuristic evidence" ~ "At least 20 classified records and strong separation from a decision threshold.",
      confidence_tier == "Moderate heuristic evidence" ~ "At least 10 classified records and clear threshold separation.",
      TRUE ~ "The call clears a threshold but has limited count or threshold separation."
    )
  )

  if (exclude_approved) master <- master %>% filter(!(has_approved_drug %in% TRUE))

  controls         <- master %>% filter(has_aso_precedent)
  knockdown_cands  <- master %>% filter(final_call == "knockdown")
  splice_cands     <- master %>% filter(final_call == "splice/upregulation")
  ambiguous_cands  <- master %>% filter(final_call == "ambiguous")
  modifier_cands   <- master %>% filter(final_call == "modifier")
  insufficient     <- master %>% filter(final_call == "insufficient data")

  # Priority view: mechanism-called genes first, then modifiers; no approved drug on the gene
  drug_ok <- !(drug_source %in% c("not checked", "lookup failed"))
  shortlist <- master %>%
    filter(final_call %in% c("knockdown", "splice/upregulation", if (include_modifiers) "modifier")) %>%
    { if (drug_ok) filter(., !(has_approved_drug %in% TRUE)) else . } %>%
    { if (exclude_aso_precedent) filter(., !has_aso_precedent) else . } %>%
    mutate(tier = ifelse(final_call == "modifier", 2, 1)) %>%
    arrange(tier, desc(genetic_score), desc(overall_score)) %>%
    select(-tier)

  track_summary <- data.frame(
    track = c("knockdown", "splice/upregulation", "ambiguous", "modifier", "insufficient data"),
    genes = c(nrow(knockdown_cands), nrow(splice_cands), nrow(ambiguous_cands),
              nrow(modifier_cands), nrow(insufficient)),
    stringsAsFactors = FALSE
  )
  metadata <- list(
    implementation = "aso_target_finder_v4_enhanced",
    implementation_version = "4.1-guided",
    run_timestamp_utc = format(Sys.time(), tz = "UTC", usetz = TRUE),
    disease_id = DISEASE_ID,
    disease_name = disease_name,
    open_targets_release = ot_version,
    endpoint = endpoint,
    drug_source = drug_source,
    trial_source = if (check_trials) "ClinicalTrials.gov API v2" else "not checked",
    linked_genes = total,
    passing_genes = nrow(master),
    evidence_cap_per_gene = EVIDENCE_SIZE,
    evidence_truncated_genes = sum(master$evidence_truncated %in% TRUE, na.rm = TRUE),
    parameters = list(
      min_score = MIN_ASSOCIATION_SCORE, min_genetic = MIN_GENETIC_SCORE,
      loeuf_intolerant = LOEUF_INTOLERANT, use_variants = use_variants,
      use_g2p = use_g2p, check_drugs = check_drugs, check_trials = check_trials,
      exclude_approved = exclude_approved, exclude_aso_precedent = exclude_aso_precedent,
      include_modifiers = include_modifiers,
      max_genes_for_variants = MAX_GENES_FOR_VARIANTS,
      max_genes_for_drugs = MAX_GENES_FOR_DRUGS,
      min_variants = MIN_VARIANTS, lof_fraction_high = LOF_FRACTION_HIGH,
      lof_fraction_low = LOF_FRACTION_LOW,
      splice_site_fraction = SPLICE_SITE_FRACTION,
      enable_indirect_evidence = TRUE,
      run_mode = run_mode,
      cache_ttl_hours = cache_ttl_hours
    ),
    cache = list(directory = cache_dir, refresh_requested = refresh_cache,
                 hits = .aso_cache_stats$hits, misses = .aso_cache_stats$misses),
    track_counts = setNames(as.list(track_summary$genes), track_summary$track),
    r_version = R.version.string,
    package_versions = list(
      httr = as.character(packageVersion("httr")),
      jsonlite = as.character(packageVersion("jsonlite")),
      dplyr = as.character(packageVersion("dplyr")),
      digest = as.character(packageVersion("digest"))
    ),
    caveats = c(
      "Hypothesis generation only; not a clinical decision tool.",
      "Any user-supplied manual overrides require primary-source verification.",
      "Gene2Phenotype calls depend on its current panels and allelic-requirement annotations.",
      "Missense-heavy evidence does not establish gain of function.",
      "Drug approval is target-centric and may be for another indication.",
      "ClinicalTrials.gov matching is text-based; summary-text-only gene matches are weak evidence.",
      "enableIndirect=true includes ontology-related disease evidence.",
      "Genes exceeding the EVA evidence cap use a truncated consequence sample."
    )
  )

  # ============================================================================
  # REPORT
  # ============================================================================
  mech_table <- function(df, show_splice = FALSE) {
    tab <- data.frame(
      Gene    = df$gene_symbol,
      Score   = fmt_num(df$overall_score),
      Genetic = fmt_num(df$genetic_score),
      LOEUF   = fmt_num(df$loeuf),
      `LoF/Mis` = ifelse(!is.na(df$n_classified) & df$n_classified > 0,
                         paste0(df$n_lof, "/", df$n_missense), "-"),
      Inherit = ifelse(is.na(df$inheritance), "-", df$inheritance),
      `Drug status`   = trunc_str(df$drug_status, 24),
      `ASO precedent` = trunc_str(df$aso_precedent, 34),
      Basis   = df$call_source,
      check.names = FALSE, stringsAsFactors = FALSE
    )
    if (show_splice) {
      tab[["Splice-site"]] <- ifelse(is.na(df$frac_splice_related), "-",
                                     paste0(ifelse(df$splice_correctable, "yes", "no"), " ",
                                            round(100 * df$frac_splice_related), "%"))
    }
    tab[["Flag"]] <- trunc_str(df$flag, 44)
    tab
  }
  num_cols <- c("Score", "Genetic", "LOEUF", "LoF/Mis")

  simple_table <- function(df, n) {
    d <- head(df, n)
    tab <- data.frame(Gene = d$gene_symbol, Score = fmt_num(d$overall_score),
                      Genetic = fmt_num(d$genetic_score), LOEUF = fmt_num(d$loeuf),
                      `LoF tolerance` = d$lof_tolerance,
                      `Drug status` = trunc_str(d$drug_status, 30),
                      `ASO precedent` = trunc_str(d$aso_precedent, 40),
                      check.names = FALSE, stringsAsFactors = FALSE)
    text_table(tab, right = c("Score", "Genetic", "LOEUF"))
  }

  show_track <- function(df, title, sub, show_splice = FALSE, n = ROWS_TO_SHOW) {
    banner(sprintf("%s  (n = %d)", title, nrow(df)), sub)
    if (nrow(df) == 0) { cat("  none\n"); return(invisible(NULL)) }
    text_table(mech_table(head(df, n), show_splice), right = num_cols)
    if (nrow(df) > n) cat(sprintf("  ... showing %d of %d; full list in the CSV file\n", n, nrow(df)))
  }

  show_simple_track <- function(df, title, sub, n = 25) {
    banner(sprintf("%s  (n = %d)", title, nrow(df)), sub)
    if (nrow(df) == 0) { cat("  none\n"); return(invisible(NULL)) }
    simple_table(df, n)
    if (nrow(df) > n) cat(sprintf("  ... showing %d of %d; full list in the CSV file\n", n, nrow(df)))
  }

  # ---- Header ----------------------------------------------------------------
  cat("\n", strrep("=", TABLE_WIDTH), "\n", sep = "")
  cat("ASO TARGET FINDER  |  ", toupper(disease_name), "  (", DISEASE_ID, ")\n", sep = "")
  cat(strrep("=", TABLE_WIDTH), "\n", sep = "")
  cat(sprintf("  Run date: %s    Open Targets release: %s\n", format(Sys.Date()), ot_version))
  cat(sprintf("  Drug data: %s    ClinicalTrials.gov: %s    Gene2Phenotype genes: %s\n",
              drug_source, trial_source, if (use_g2p) nrow(g2p_tbl) else "not used"))
  cat(sprintf("  Genes linked to this disease:   %d\n", total))
  cat(sprintf("  Passing filters:                %d   (overall >= %.2f and genetic >= %.2f)\n",
              nrow(master), MIN_ASSOCIATION_SCORE, MIN_GENETIC_SCORE))
  cat("\n")

  summ_row <- function(label, df) {
    data.frame(
      Track = label,
      Genes = nrow(df),
      `Approved drug`  = if (drug_ok) sum(df$has_approved_drug %in% TRUE) else NA,
      `ASO precedent`  = sum(df$has_aso_precedent),
      `No drug found`  = if (drug_ok) sum(df$drug_status == "None found") else NA,
      check.names = FALSE, stringsAsFactors = FALSE)
  }
  summ <- bind_rows(
    summ_row("Knockdown (likely toxic GoF)", knockdown_cands),
    summ_row("Splice / upregulation (likely LoF)", splice_cands),
    summ_row("Ambiguous (mixed evidence)", ambiguous_cands),
    summ_row("Modifier (association only, no variants)", modifier_cands),
    summ_row("Insufficient data (1-4 variants)", insufficient)
  )
  text_table(summ, right = c("Genes", "Approved drug", "ASO precedent", "No drug found"))
  cat(sprintf("\n  Mechanism source: G2P %d, ClinVar %d, manual override %d (of %d genes)\n",
              sum(master$call_source == "G2P"),
              sum(master$call_source == "ClinVar" & !(master$final_call %in% "insufficient data")),
              sum(master$call_source == "curated"), nrow(master)))
  cat(sprintf("  Splice-correctable (splice-affecting variants >= %.0f%% of LoF-type + splice-region/intronic): %d of %d splice/upregulation genes\n",
              100 * SPLICE_SITE_FRACTION, sum(splice_cands$splice_correctable), nrow(splice_cands)))
  tracks_total <- nrow(knockdown_cands) + nrow(splice_cands) + nrow(ambiguous_cands) +
    nrow(modifier_cands) + nrow(insufficient)
  cat(sprintf("  Check: tracks sum to %d, passing genes = %d  -> %s\n",
              tracks_total, nrow(master), ifelse(tracks_total == nrow(master), "OK", "MISMATCH")))
  if (!drug_ok) cat("  WARNING: drug lookup did not run or failed; drug columns are not reliable.\n")
  if (trial_source == "lookup failed") cat("  WARNING: ClinicalTrials.gov lookup failed; ASO precedent uses Open Targets drugs only.\n")

  # ---- Positive controls (from the databases) ----------------------------------
  banner(sprintf("POSITIVE CONTROLS  (n = %d)", nrow(controls)),
         "Genes with an antisense/siRNA-type drug in Open Targets or an interventional ASO trial on ClinicalTrials.gov.")
  if (nrow(controls) > 0) {
    cc <- head(controls, ROWS_TO_SHOW)
    tab <- data.frame(Gene = cc$gene_symbol,
                      Score = fmt_num(cc$overall_score),
                      Genetic = fmt_num(cc$genetic_score),
                      LOEUF = fmt_num(cc$loeuf),
                      `Drug status` = trunc_str(cc$drug_status, 30),
                      `ASO precedent` = trunc_str(cc$aso_precedent, 70),
                      check.names = FALSE, stringsAsFactors = FALSE)
    text_table(tab, right = c("Score", "Genetic", "LOEUF"))
    if (nrow(controls) > ROWS_TO_SHOW) cat(sprintf("  ... showing %d of %d; full list in the CSV file\n", ROWS_TO_SHOW, nrow(controls)))
  } else cat("  none\n")

  # ---- ASO trials for the condition ----------------------------------------------
  banner(sprintf("ASO TRIALS ON CLINICALTRIALS.GOV FOR THIS CONDITION  (n = %d)", nrow(trials_tbl)),
         paste0("Genes = passing genes named in the title or interventions ('?' = named only in the summary). ",
                "'non-drug' studies (sampling, in vitro) do not count as ASO precedent."))
  if (nrow(trials_tbl) > 0) {
    tt <- head(trials_tbl, ROWS_TO_SHOW)
    tab <- data.frame(`NCT ID` = tt$nct, Phase = tt$phase, Status = tt$status, Type = tt$type,
                      Genes = trunc_str(tt$genes, 18),
                      Interventions = trunc_str(tt$interventions, 30),
                      Title = trunc_str(tt$title, 56),
                      check.names = FALSE, stringsAsFactors = FALSE)
    text_table(tab)
    if (nrow(trials_tbl) > ROWS_TO_SHOW) cat(sprintf("  ... showing %d of %d; full list in the CSV file\n", ROWS_TO_SHOW, nrow(trials_tbl)))
  } else cat("  none found\n")

  # ---- Priority shortlist ------------------------------------------------------
  banner(sprintf("PRIORITY SHORTLIST  (n = %d)", nrow(shortlist)),
         paste0(if (drug_ok) "Knockdown, splice and modifier genes with no approved drug on the gene" else "Knockdown, splice and modifier genes (drug filter not applied)",
                if (exclude_aso_precedent) ", no ASO precedent" else "",
                ". Mechanism-called genes first, then modifiers; ranked by genetic evidence."))
  if (nrow(shortlist) > 0) {
    sl <- head(shortlist, 15)
    tab <- mech_table(sl)
    tab <- cbind(Track = ifelse(sl$final_call == "knockdown", "knockdown",
                         ifelse(sl$final_call == "modifier", "modifier", "splice/upreg")), tab,
                 stringsAsFactors = FALSE)
    text_table(tab, right = num_cols)
    if (nrow(shortlist) > 15) cat(sprintf("  ... showing 15 of %d; full list in the CSV file\n", nrow(shortlist)))
  } else cat("  none\n")

  # ---- Tracks --------------------------------------------------------------------
  show_track(knockdown_cands, "KNOCKDOWN CANDIDATES",
             "Gene2Phenotype gain-of-function / dominant-negative, or ClinVar variants mostly missense/inframe.")
  show_track(splice_cands, "SPLICE / UPREGULATION CANDIDATES",
             "Gene2Phenotype loss-of-function, or ClinVar variants mostly truncating. Splice-site = splice-affecting share.",
             show_splice = TRUE)
  show_track(ambiguous_cands, "AMBIGUOUS", "Mixed evidence.", n = 25)
  show_simple_track(modifier_cands, "MODIFIER / ASSOCIATION-ONLY GENES",
                    "Genetic association but no variant-level evidence in ClinVar or Gene2Phenotype (e.g. GWAS loci). Mechanism and direction of effect unknown.")
  show_simple_track(insufficient, "INSUFFICIENT DATA",
                    sprintf("No Gene2Phenotype record and 1-%d usable ClinVar variants (or no variant lookup); mechanism not called.", MIN_VARIANTS - 1))

  # ---- Optional legend -----------------------------------------------------------
  if (show_legend) {
    cat("\n", strrep("=", TABLE_WIDTH), "\nCOLUMN GUIDE\n", strrep("-", TABLE_WIDTH), "\n", sep = "")
    cat("  Score          Overall Open Targets association with the disease (0-1).\n")
    cat("  Genetic        Genetic evidence only (0-1).\n")
    cat("  LOEUF          gnomAD tolerance to losing one copy. Below 0.60 = intolerant.\n")
    cat("  LoF/Mis        Pathogenic ClinVar records that are loss-of-function / missense.\n")
    cat("  Inherit        Inheritance from Gene2Phenotype (dominant / recessive / both), when recorded.\n")
    cat("  Drug status    Most advanced drug found for the gene as a target (any indication).\n")
    cat("  ASO precedent  Antisense/siRNA-type drug in Open Targets, and/or interventional ASO trials on ClinicalTrials.gov.\n")
    cat("  Basis          Where the call came from: G2P, ClinVar counts, manual override, or association only.\n")
    cat("  Splice-site    Share of LoF-type variants that affect splicing (canonical, region, intronic) and whether it passes the cutoff.\n")
  }
  cat(strrep("=", TABLE_WIDTH), "\n", sep = "")

  # ============================================================================
  # SAVE CSV FILES
  # ============================================================================
  if (save_csv) {
    dir.create(output_dir, showWarnings = FALSE, recursive = TRUE)
    csv_order <- c("gene_symbol", "gene_name", "ensembl_id", "final_call", "call_source",
                   "overall_score", "genetic_score", "loeuf", "lof_tolerance",
                   "n_evidence", "n_evidence_returned", "evidence_truncated",
                   "n_lof", "n_missense", "n_splice", "n_splice_extra", "frac_lof",
                   "frac_splice_related", "splice_correctable",
                   "confidence_tier", "confidence_reason",
                   "g2p_mech", "inheritance", "clinvar_call",
                   "drug_status", "drug_max_stage", "has_approved_drug", "approved_drugs",
                   "aso_drug", "aso_names", "oligo_drug", "oligo_names", "n_drugs",
                   "aso_precedent", "aso_trial_n", "aso_trial_weak", "aso_trial_best", "aso_trial_ids",
                   "flag", "note")
    tidy <- function(df) {
      keep <- intersect(csv_order, names(df))
      df[, c(keep, setdiff(names(df), keep)), drop = FALSE]
    }
    write.csv(tidy(master),          file.path(output_dir, "all_candidates_annotated.csv"),       row.names = FALSE)
    write.csv(tidy(knockdown_cands), file.path(output_dir, "knockdown_candidates.csv"),           row.names = FALSE)
    write.csv(tidy(splice_cands),    file.path(output_dir, "splice_upregulation_candidates.csv"), row.names = FALSE)
    write.csv(tidy(ambiguous_cands), file.path(output_dir, "ambiguous_candidates.csv"),           row.names = FALSE)
    write.csv(tidy(modifier_cands),  file.path(output_dir, "modifier_candidates.csv"),            row.names = FALSE)
    write.csv(tidy(insufficient),    file.path(output_dir, "insufficient_data.csv"),              row.names = FALSE)
    write.csv(tidy(controls),        file.path(output_dir, "positive_controls.csv"),              row.names = FALSE)
    write.csv(tidy(shortlist),       file.path(output_dir, "priority_shortlist.csv"),             row.names = FALSE)
    n_files <- 8
    if (nrow(trials_tbl) > 0) {
      write.csv(trials_tbl, file.path(output_dir, "aso_trials_for_condition.csv"), row.names = FALSE)
      n_files <- 9
    }
    write.csv(track_summary,            file.path(output_dir, "run_summary.csv"),                    row.names = FALSE)
    write_json(metadata,                file.path(output_dir, "run_metadata.json"),
               pretty = TRUE, auto_unbox = TRUE, null = "null")
    cat("Saved", n_files, "candidate/trial CSV files plus run_summary.csv and run_metadata.json to:",
        normalizePath(output_dir, winslash = "/", mustWork = FALSE), "\n")
  }
  mins <- round(as.numeric(difftime(Sys.time(), t0, units = "mins")), 1)
  cat("Finished in", mins, "min\n")

  invisible(list(disease = disease_name, disease_id = DISEASE_ID, all = master,
                 knockdown = knockdown_cands, splice = splice_cands,
                 ambiguous = ambiguous_cands, modifier = modifier_cands,
                 insufficient = insufficient, controls = controls,
                 shortlist = shortlist, trials = trials_tbl,
                 track_summary = track_summary, metadata = metadata,
                 output_dir = if (save_csv) output_dir else NA_character_))
}

# Standalone compact report: independent of the long console transcript.
write_aso_report <- function(res,
                             file = file.path(res$output_dir, "concise_report.html"),
                             top_n = 15) {
  if (is.null(res$metadata)) stop("Result has no enhanced metadata; rerun with the enhanced source.")
  esc <- function(x) {
    x <- gsub("&", "&amp;", as.character(x), fixed = TRUE)
    x <- gsub("<", "&lt;", x, fixed = TRUE)
    x <- gsub(">", "&gt;", x, fixed = TRUE)
    x
  }
  html_table <- function(df) {
    if (nrow(df) == 0) return("<p>None</p>")
    head_row <- paste0("<tr>", paste0("<th>", esc(names(df)), "</th>", collapse = ""), "</tr>")
    body <- apply(df, 1, function(row) paste0("<tr>", paste0("<td>", esc(row), "</td>", collapse = ""), "</tr>"))
    paste0("<table>", head_row, paste(body, collapse = ""), "</table>")
  }
  top <- head(res$shortlist, top_n)
  wanted <- intersect(c("gene_symbol", "final_call", "confidence_tier", "call_source", "overall_score",
                        "genetic_score", "g2p_mech", "inheritance", "loeuf", "n_lof", "n_missense",
                        "evidence_truncated", "drug_status", "aso_precedent", "flag"), names(top))
  detail_cols <- intersect(c("gene_symbol", "confidence_reason", "note"), names(top))
  shortlist_html <- sub("<table>", "<table id='shortlist'>",
                        html_table(top[, wanted, drop = FALSE]), fixed = TRUE)
  caveats <- paste0("<li>", esc(res$metadata$caveats), "</li>", collapse = "")
  html <- c(
    "<!doctype html><html><head><meta charset='utf-8'><title>ASO Target Finder report</title>",
    "<style>body{font:15px system-ui;max-width:1180px;margin:32px auto;padding:0 18px;color:#18202a}table{border-collapse:collapse;width:100%;margin:12px 0 28px}th,td{border:1px solid #ccd3da;padding:7px;text-align:left;vertical-align:top}th{background:#eef3f7;position:sticky;top:0}code{background:#f3f5f7;padding:2px 4px}.warn{background:#fff4d6;padding:14px;border-left:5px solid #e6a700}input{padding:8px;width:min(420px,90%);margin:8px 0}</style></head><body>",
    paste0("<h1>ASO Target Finder: ", esc(res$disease), "</h1>"),
    paste0("<p><b>Disease ID:</b> <code>", esc(res$disease_id), "</code><br><b>Run:</b> ", esc(res$metadata$run_timestamp_utc),
           "<br><b>Open Targets release:</b> ", esc(res$metadata$open_targets_release),
           "<br><b>Passing genes:</b> ", esc(res$metadata$passing_genes), "</p>"),
    "<div class='warn'><b>Research-use warning:</b> hypothesis generation only. Review every candidate, G2P/ClinVar disagreement, weak trial match, and manual override.</div>",
    "<h2>Track summary</h2>", html_table(res$track_summary),
    paste0("<h2>Priority shortlist (top ", top_n, ")</h2><p><input id='filter' placeholder='Filter genes, tracks, confidence or drug status'></p>"), shortlist_html,
    "<h2>Why each confidence tier was assigned</h2>", html_table(top[, detail_cols, drop = FALSE]),
    "<h2>How to interpret this report</h2><dl><dt><b>LoF</b></dt><dd>Loss of function; it does not automatically imply that upregulation is feasible.</dd><dt><b>GoF hypothesis</b></dt><dd>A missense-heavy pattern can motivate review for toxic gain of function, but does not prove it.</dd><dt><b>G2P</b></dt><dd>Gene2Phenotype mechanism and inheritance annotations take precedence over the ClinVar count heuristic.</dd><dt><b>Modifier</b></dt><dd>Association evidence without enough directional variant evidence; do not infer knockdown or upregulation.</dd><dt><b>ASO precedent</b></dt><dd>Combines Open Targets drug records with text-matched interventional ClinicalTrials.gov studies; summary-only matches are weak.</dd><dt><b>LOEUF</b></dt><dd>A constraint metric used as a safety flag, not as the mechanism classifier.</dd><dt><b>Indirect evidence</b></dt><dd>Ontology-related diseases improve recall while reducing specificity.</dd><dt><b>Confidence tier</b></dt><dd>A transparent heuristic for triage, not a calibrated probability.</dd></dl>",
    "<h2>Important caveats</h2>", paste0("<ul>", caveats, "</ul>"),
    "<script>document.getElementById('filter').addEventListener('input',function(){let q=this.value.toLowerCase();document.querySelectorAll('#shortlist tr').forEach((r,i)=>{if(i)r.style.display=r.innerText.toLowerCase().includes(q)?'':'none'})})</script>",
    "</body></html>"
  )
  writeLines(html, file, useBytes = TRUE)
  normalizePath(file, winslash = "/", mustWork = FALSE)
}

cat('Loaded v4 enhanced edition. Run:  run_aso("MONDO_0004976")\n')
