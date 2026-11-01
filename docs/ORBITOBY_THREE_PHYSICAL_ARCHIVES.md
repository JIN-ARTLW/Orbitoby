# Orbitoby three-source physical archive — API and scientific contract

This module integrates **officially supported collection methods** for the maximum data **actually exposed to this account**. It does not claim every historical object's metadata is available from each provider.

## Sources and limits

| Provider | Automated method | Scope | Access / conditions |
|---|---|---|---|
| Jonathan McDowell GCAT | Official `https://planet4589.org/space/gcat/tsv/cat/{catalog}.tsv` downloads | 4 main physical/object+payload TSVs by default; expanded named GCAT object/payload files with `all` | Each original column retained; estimated quantity flags retained; JCAT-only rows never force-matched to ambiguous NORAD IDs |
| ESA DISCOS | Authenticated `GET https://discosweb.esoc.esa.int/api/objects?page[size]=100&page[number]=N`, `Authorization: Bearer ...`, `DiscosWeb-Api-Version: 2` | Paginated *accessible* object records | Explicit `--discos-max-pages`; one request per page; stop on 429/permission error, checkpoint; run again to resume. Full scope depends on ESA permission and quota. |
| KeepTrack | Authenticated `GET https://api.keeptrack.space/v4/sats/brief`, `X-API-Key: ...` | **Whole currently active brief catalog**, not every historical detailed satellite | Single bulk call; ETag cache. Do not iterate `/v4/sat/{id}` or `/v4/sats/{id}` for all. For comprehensive detailed bulk, get written approval from `admin@keeptrack.space` and import the authorized bulk JSON file. License CC BY-NC 4.0 applies to API data. |

**Official sources**: [GCAT](https://planet4589.org/space/gcat/web/cat/index.html), [DISCOSweb](https://discosweb.esoc.esa.int/), [KeepTrack API v4](https://api.keeptrack.space/v4/docs).

**Data licenses differ from the Orbitoby Python code license.** Do not publish or redistribute collected data without checking provider-specific rights. Credit ESA DISCOS as requested in their service page. KeepTrack is non-commercial CC BY-NC 4.0. Do not commit tokens or `physical_archives.sqlite3`/raw snapshots to GitHub without deliberately reviewing licenses and volume.

## Public Python API

```python
import orbitoby as ob

with ob.physics('~/Desktop/Orbitoby_Physical_Archives') as physical:
    print(physical.sources())         # provider item/NORAD counts
    print(physical.state())           # complete/pending per provider scope
    print(physical.coverage())        # reported physical-field coverage
    satellite = physical.get(35694)   # ALL GCAT/DISCOS/KeepTrack records + raw fields
    print(satellite['records'])       # raw fields and URLs, no information silently omitted
    print(satellite['properties'])    # explicitly normalized evidence + caveats

    ids = physical.select(required=('launch_mass_kg','cross_section_geo_avg_m2'))
    # NOTE: this does NOT mean Cd or an accurate ballistic coefficient is known.
    print(len(ids))

    print(physical.raw(35694,'discos'))
    print(physical.find_raw('discos','attributes.mass',limit=10))
    print(physical.collisions('catalog_mass_kg',relative_tolerance=0.05))
    print(physical.export_wide('~/Desktop/physics_wide.csv'))
```

### Supported normalized physical fields

- GCAT: `launch_mass_kg`, `dry_mass_kg`, `body_length_m`, `body_diameter_m`, `body_span_m`, `shape`, `mass_flag`, `dry_mass_flag`, `object_type`.
- DISCOS: `catalog_mass_kg`, `cross_section_geo_avg_m2`, `cross_section_geo_min_m2`, `cross_section_geo_max_m2`, `shape`, `body_width_m`, `body_height_m`, `body_depth_m`, `body_diameter_m`, `body_span_m`, `object_class`.
- KeepTrack brief: source-provided `rcs_category`, `object_class`, `satellite_name`, `launch_date`, `purpose`, and explicit unit-bearing keys in authorized detailed exports (`mass_kg`, `dry_mass_kg`, `length_m`, `diameter_m`, `span_m`, `power_w`). **Every additional original key** is still available in `records[].raw` and `find_raw()`.

`B = m/(Cd * A_drag)` is **never** auto-filled using RCS, GCAT nominal dimensions, DISCOS `xSectAvg` or TLE `BSTAR`. A complete scientific model requires an epoch-consistent mass, relevant attitude/environment-dependent drag area and Cd or an independently published ballistic coefficient with defined convention and uncertainty.

## CLI

The `--db` global option comes before the subcommand. Set tokens on your computer only, in hidden input prompts or a local credential store:

```zsh
cd ~/code/orbitoby
read -rs 'ORBITOBY_DISCOS_TOKEN?DISCOS token: '; echo; export ORBITOBY_DISCOS_TOKEN
read -rs 'ORBITOBY_KEEPTRACK_API_KEY?KeepTrack API key: '; echo; export ORBITOBY_KEEPTRACK_API_KEY

# Small online validation before large downloads
uv run --group dev python scripts/orbitoby_physics.py sync --gcat standard --keeptrack --discos pages --discos-max-pages 2

# Remaining GCAT catalogs; additional DISCOS pages (preserves previous page cursor)
uv run --group dev python scripts/orbitoby_physics.py sync --gcat all --discos pages --discos-max-pages 10

# Continue DISCOS pages by repeating the command *after* checking ESA quota
uv run --group dev python scripts/orbitoby_physics.py sync --discos pages --discos-max-pages 10

# Local queries
uv run --group dev python scripts/orbitoby_physics.py status
uv run --group dev python scripts/orbitoby_physics.py get 35694 --no-raw
uv run --group dev python scripts/orbitoby_physics.py get 35694 --provider discos
uv run --group dev python scripts/orbitoby_physics.py select --require launch_mass_kg --require cross_section_geo_avg_m2
uv run --group dev python scripts/orbitoby_physics.py find-raw --provider discos --field attributes.mass

# Whole Orbitoby catalog coverage audit, no altitude, TLE, orbit, date or epoch filters
uv run --group dev python scripts/orbitoby_physics.py audit --out ~/Desktop/physics_provider_audit.json

# Flat analysis tables: do NOT silently choose one provider's mass over another
uv run --group dev python scripts/orbitoby_physics.py export-wide --out ~/Desktop/physics_all_sources_wide.csv
uv run --group dev python scripts/orbitoby_physics.py export --out ~/Desktop/physics_long_evidence.csv

unset ORBITOBY_DISCOS_TOKEN ORBITOBY_KEEPTRACK_API_KEY
```

**KeepTrack bulk detailed metadata**: permitted only once the provider supplies/authorizes a detailed file. Such files are not obtained by iterating single-satellite endpoints.

```zsh
uv run --group dev python scripts/orbitoby_physics.py sync --keeptrack-approved-file ~/Downloads/approved_keeptrack_metadata.json
```

## Outputs and audit

- `~/Desktop/Orbitoby_Physical_Archives/physical_archives.sqlite3`: queryable raw+normalized source records (not automatically published).
- `snapshots/{gcat,discos,keeptrack}/*.gz`: compressed, content-addressed response bodies.
- `receipts` SQL table: source URL, SHA256, row counts, timestamp, collection scope.
- `state` SQL table: exact source/collection mode, cursor, successful request count, completion and errors.
- `audit` JSON: number of reference NORAD IDs found/missing from each source, including missing IDs.
- `export-wide`: per-source columns, incompatible quantities never consolidated; conflicting values within a source are separated by ` | ` rather than arbitrarily selected.
- `export`: long-form per-field source evidence.

**Meaning of completion**: `discos` complete only means the server's last *accessible* page was reached. `keeptrack` complete only means the **active bulk brief feed** was received, not that all historical detailed metadata is available. GCAT `all` means the named GCAT TSV files were processed; not that every field is experimentally verified.

## Limitations / validation work needed

1. Tested locally with synthetic provider responses, not authenticated production API responses. Real DISCOS page schema and quota behavior must be smoke-tested on the user's account.
2. Provider identity/classification differences and uncertain JCAT↔NORAD matches must be audited before deriving a strict cohort.
3. KeepTrack v4 `brief` is **not** a full historical detailed metadata download. Bulk detailed access requires provider consent (`admin@keeptrack.space`). The module never automates disallowed per-object scraping.
4. `xSectAvg` is geometric area, not measured in-flight projected aerodynamic area. RCS is radar cross section; TLE BSTAR is not a physical drag coefficient.
5. Original GCAT `MassFlag` values are retained; a missing estimation marker is not proof of a measured mass.
6. CSV exports and local DB may contain protected/licensed data. KeepTrack API: attribution + no commercial usage. ESA DISCOS: source acknowledgment required; follow terms.
7. This adapter is intentionally independent of orbit decay analysis. Only after finding a physics-complete cohort should TLE/solar data be joined by NORAD ID.
