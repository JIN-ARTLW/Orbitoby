# Orbitoby — 19,540 plotted objects physical-spec metadata FULL JOIN

## Scientific and data model contract

The left-hand universe consists of the distinct **actually plotted** NORAD IDs in
`~/Desktop/Orbitoby_low550_aligned_plots/satellite_monthly_le550.csv`.
For the user's recent run this should be **19,540**, but the code verifies the
actual number rather than assuming it. All IDs are preserved, including when
GCAT has no match, values are missing, or multiple GCAT catalogs conflict.

GCAT is read from the authoritative `satcat.tsv` and `satcat100k.tsv` source
catalogs through the already installed `orbitoby.physical_specs` adapter.
Exact NORAD ID is the *only join key*. Object-name fuzzy matching is forbidden.

**Field semantics:** Launch and dry mass are catalogue metadata (not necessarily
current orbital mass); length/diameter/span/shape are geometry descriptors; GCAT
`MassFlag ?` indicates an estimate. Solar array deployment, external total surface
area and attitude-dependent drag projected area remain `unknown`/missing until
supported by separately documented mission evidence. ESA DISCOS geometric
cross-sections cannot be automatically substituted for operational drag areas.

## Install on Mac

1. Extract the patch ZIP in `~/Downloads`. The previous physical-spec adapter
   commit `88e69e0` must already be present locally.
2. Ensure you are on your PR branch, not protected `main`:

```bash
cd ~/code/orbitoby
git branch --show-current
```

3. Run installer (no auto-push):

```bash
bash ~/Downloads/Orbitoby_PhysicalSpecs_FullJoin_v1/APPLY_TEST_MAC.command
```

## Execute full join over 19,540 plotted objects

```bash
cd ~/code/orbitoby
uv run --group dev python scripts/orbitoby_join_all_physical_specs.py \
  --plot-dir ~/Desktop/Orbitoby_low550_aligned_plots \
  --out ~/Desktop/Orbitoby_PhysicalSpecs_FullJoin \
  --expected-count 19540
```

The first run retrieves and locally caches the two GCAT TSV sources. The output
will be placed on Desktop, not in Git. On reruns the source TSV files are reused;
pass `--refresh-gcat` if you explicitly need to refresh official source data.

If the plotted universe has changed from 19,540, do not merely change the
expected number without checking the plot's original `run_manifest.json`.

### Optional enrichment

To add an institutionally authorized **already downloaded** ESA DISCOS CSV export
containing exact `norad_id` and standardized `discos_mass_kg`, `discos_xsect_avg_m2`,
`discos_xsect_min_m2`, etc. columns, add:

```bash
--discos-csv /path/to/authorized_discos_export.csv
```

This option **does not make bulk DISCOS requests**, and does not imply an ESA
API token exists. It does not automatically prove physical drag area or panel
configuration. The legacy optional DISCOS API connector remains separate and
rate-limited. Use a research-appropriate API plan and respect terms if extending.

For fields verified in individual mission documents, add:

```bash
--manual-evidence /path/to/checked_satellite_specs.csv
```

Template: `docs/physical_specs_manual_evidence_template.csv` from previous patch.

## Output files

- `physical_specs_all_plotted_norad_left_join.csv`: exactly one row **per plotted NORAD ID**, including missing matches
- `physical_specs_unmatched_or_ambiguous.csv`: absent/ambiguous GCAT correspondence
- `physical_specs_catalog_partial_candidates.csv`: matched GCAT payload, positive catalog launch mass and body length/diameter; **not** automatically trustworthy drag parameters
- `physical_specs_strict_documented_candidates.csv`: source-URL completeness gate; may be empty
- `physical_specs_coverage_report.csv`: match counts, missing data and field availability
- `gcat_ambiguous_source_rows.csv`: all conflicting catalogue rows, not arbitrarily resolved
- `physical_specs_full_join_manifest.json`: input hashes, source URLs, file SHA256, sample-count requirements, caveats
- `source_cache/`: cached GCAT raw files; **do not add to Git**

## Quality gates

- Assert count equals 19,540 before claiming complete join of the user's plotted sample.
- Assert each input NORAD ID occurs exactly once and all output IDs match.
- Never fill unknown physical attributes with zero or derived guessed values.
- Do not claim that the 19,540 plotted objects are all real satellites if source
  catalog classification is unverified; verify against GCAT `Type` first character
  `P` for payloads; conflicting classifications are excluded from research cohort.
- Group identifiers based on *current* CelesTrak subsets can miss deorbited
  historical CubeSats. Do not treat the CubeSat count as ground truth.
- `first_tle_altitude_eligibility_audit.csv` is joined for traceability; do not
  equate first available TLE altitude with measured launch orbit.

## GitHub protected main branch and regression CI failures

The screenshot from Nov 1 shows four **Python 3.12 / 3.13 regression** checks
failed on both push and PR, while wheel/Colab checks passed. Those two events
represent two test environment versions, not four distinct identified root
causes. The screenshot does not contain failure logs.

Open the failed GitHub Actions job and inspect the first substantive error.
Locally run before committing/pushing:

```bash
cd ~/code/orbitoby
uv run --group dev pytest -q
uv run --group dev python -m compileall -q src/orbitoby scripts/orbitoby_join_all_physical_specs.py
git status --short
```

Since main is protected, push to a feature branch and update its PR, not main.
Only source code, docs, and tests belong in the PR, **not** the 19,540-row CSV,
third-party GCAT raw files, large TLE archives, or ESA authentication details.

Useful reference: https://planet4589.org/space/gcat/web/cat/cols.html
