# 공개 API·dataset inventory / Public API and dataset inventory
현재 소스 signature로 생성했습니다. 이 목록은 구현 확인용이며 각 의미·제약은 위키 본문을 따릅니다.

Generated from current source signatures. Consult the guides for semantics and limitations.
## `Archive`

```python
Archive(*, credentials: 'CredentialManager | None' = None, allow_dotenv: 'bool' = False) -> 'None'
artifacts(self, *, source: 'str | None' = None, dataset: 'str | None' = None, norad_id: 'int | None' = None) -> 'pd.DataFrame'
close(self) -> 'None'
coverage(self, *, norad_id: 'int | None' = None, source: 'str | None' = None, dataset: 'str | None' = None) -> 'pd.DataFrame'
credits(self) -> 'list[dict]'
dataset_info(self, source: 'str', dataset: 'str', *, live: 'bool' = False) -> 'dict'
datasets(self, *, source: 'str | None' = None, metric: 'str | None' = None, category: 'str | None' = None, data_scope: 'str | None' = None, object_scope: 'str | None' = None, live: 'bool' = False) -> 'list[dict]'
fetch(self, *, source: 'str', dataset: 'str', archive_raw: 'bool' = True, **params: 'Any') -> 'pd.DataFrame'
get_source(self, name: 'str') -> 'SourceAdapter'
licenses(self) -> 'list[dict]'
msis_density(self, inputs: 'pd.DataFrame', *, parents: 'Iterable[ProductParent]', geomagnetic_activity: 'int' = -1) -> 'pd.DataFrame'
msis_inputs(self, trajectory: 'pd.DataFrame', *, driver_source: 'str', trajectory_parents: 'Iterable[ProductParent]') -> 'tuple[pd.DataFrame, tuple[ProductParent, ...]]'
object(self, *, norad_id=None, cospar_id=None, object_id=None)
objects(self, *, search: 'str | None' = None, norad_id=None, cospar_id=None, source: 'str | None' = None, dataset: 'str | None' = None, properties=None, start=None, end=None, existence: 'str' = 'overlap', object_type: 'str | None' = None, sync: 'bool' = False, limit: 'int | None' = None, offset: 'int' = 0)
orbit(self, *, norad_id: 'int', start: 'str | date', end: 'str | date', source: 'str' = 'spacetrack', sync: 'bool' = True) -> 'pd.DataFrame'
orbit_summary(self, objects, *, start: 'str | date', end: 'str | date', periapsis_km=None, apoapsis_km=None, inclination_deg=None, eccentricity=None, mean_motion=None, min_coverage: 'float | None' = None, orbit_match: 'str' = 'all', source: 'str' = 'spacetrack', sync: 'bool' = False) -> 'pd.DataFrame'
plot(self, data: 'pd.DataFrame', *, kind: 'PlotKind' = 'line', fields: 'str | tuple[str, ...] | list[str] | None' = None, title: 'str | None' = None, legend: 'bool' = True, width: 'int' = 900, height: 'int' = 480) -> 'PlotResult'
plot_timeseries(self, metric: 'str | None' = None, *, fields=None, start, end, source: 'str | None' = None, source_preference=None, dataset: 'str | None' = None, artifact_resolution='all', archive_raw: 'bool' = True, kind: 'PlotKind' = 'line', title: 'str | None' = None, legend: 'bool' = True, width: 'int' = 900, height: 'int' = 480) -> 'PlotResult'
plugin_candidates(self) -> 'list[dict]'
records(self, *, object_id=None, source=None, dataset=None, identity_status=None)
register_http_source(self, *, name: 'str', dataset: 'str', url: 'str', format: 'str' = 'json', root_key: 'str | None' = None, homepage: 'str | None' = None, description_en: 'str' = '', description_ko: 'str' = '') -> 'list[str]'
reindex(self, *, source=None, dataset=None, batch_size: 'int' = 500, progress: 'bool' = True)
reload_sources(self) -> 'list[str]'
search(self, *, norad_id=None, cospar_id=None, name=None, source=None, dataset=None, properties=None, limit=100, offset=0)
source_info(self, name: 'str | None' = None)
sources_available(self) -> 'list[str]'
space_weather(self, *, start, end, fields: 'Iterable[str] | str', source: 'str | None' = None, source_preference: 'Iterable[str] | None' = None, dataset: 'str | None' = None, artifact_resolution: 'ArtifactResolution' = 'all', archive_raw: 'bool' = True) -> 'pd.DataFrame'
timeseries(self, metric: 'str | None' = None, *, fields: 'Iterable[str] | str | None' = None, start, end, source: 'str | None' = None, source_preference: 'Iterable[str] | None' = None, dataset: 'str | None' = None, artifact_resolution: 'ArtifactResolution' = 'all', archive_raw: 'bool' = True) -> 'pd.DataFrame'
trust_source_plugin(self, name: 'str') -> 'list[str]'
unregister_http_source(self, name: 'str', *, dataset: 'str | None' = None) -> 'list[str]'
untrust_source_plugin(self, name: 'str') -> 'list[str]'
window(self, *, start, end, fields: 'Iterable[str] | str', source: 'str | None' = None, source_preference: 'Iterable[str] | None' = None, dataset: 'str | None' = None, artifact_resolution: 'ArtifactResolution' = 'all', archive_raw: 'bool' = True) -> 'ResearchWindow'
```

## `ResearchWindow`

```python
ResearchWindow(data: 'pd.DataFrame', presence: 'pd.DataFrame', missing_reason: 'pd.DataFrame', provenance: 'pd.DataFrame', units: 'dict[str, str]') -> None
to_numpy(self)
```

## `ProductParent`

```python
ProductParent(parent_kind: 'str', parent_id: 'str', role: 'str' = 'input') -> None
```

## `PlotResult`

```python
PlotResult(svg: 'str', data: 'pd.DataFrame', provenance: 'pd.DataFrame') -> None
save(self, path: 'str | Path') -> 'Path'
```

## `CredentialManager`

```python
CredentialManager(*, runtime: 'dict[tuple[str, str], str] | None' = None, allow_dotenv: 'bool' = False, dotenv_path: 'str | Path | None' = None) -> 'None'
clear_runtime(self, provider: 'str', key: 'str') -> 'None'
delete_keyring(provider: 'str', key: 'str') -> 'None'
env_name(provider: 'str', key: 'str') -> 'str'
get(self, provider: 'str', key: 'str', *, env_name: 'str | None' = None, required: 'bool' = False) -> 'str | None'
resolve(self, provider: 'str', key: 'str', *, env_name: 'str | None' = None) -> 'CredentialResult | None'
set_keyring(provider: 'str', key: 'str', value: 'str') -> 'None'
set_runtime(self, provider: 'str', key: 'str', value: 'str') -> 'None'
status(self, provider: 'str', keys: 'tuple[str, ...]') -> 'dict[str, dict[str, object]]'
```

## `ScientificStore`

```python
ScientificStore(con: 'duckdb.DuckDBPyConnection', *, root: 'str | Path | None' = None) -> 'None'
missing_ranges(self, *, metric: 'str', source: 'str', dataset: 'str', transform: 'str', transform_version: 'str', start: 'Any', end: 'Any') -> 'list[tuple[pd.Timestamp, pd.Timestamp]]'
query(self, *, start: 'Any', end: 'Any', metric: 'str | None' = None, source: 'str | None' = None, dataset: 'str | None' = None) -> 'pd.DataFrame'
query_coverage(self, *, metric: 'str', source: 'str', dataset: 'str', transform: 'str', transform_version: 'str', start: 'Any', end: 'Any') -> 'pd.DataFrame'
read_store(self, store_id: 'str') -> 'pd.DataFrame'
record_coverage(self, *, metric: 'str', source: 'str', dataset: 'str', artifact_id: 'str', transform: 'str', transform_version: 'str', requested_start: 'Any', requested_end: 'Any', row_count: 'int', store_id: 'str | None') -> 'str'
write(self, frame: 'pd.DataFrame', *, requested_start: 'Any', requested_end: 'Any') -> 'ScientificFile'
```

## `ProductStore`

```python
ProductStore(con: 'duckdb.DuckDBPyConnection', *, root: 'str | Path | None' = None) -> 'None'
lineage(self, product_id: 'str') -> 'tuple[ProductParent, ...]'
read_product(self, product_id: 'str') -> 'pd.DataFrame'
write(self, frame: 'pd.DataFrame', *, dataset: 'str', metric: 'str', unit: 'str', artifact_kind: 'str', method: 'str', transform: 'str', transform_version: 'str', requested_start: 'Any', requested_end: 'Any', parents: 'Iterable[ProductParent]', parameters: 'dict[str, Any] | None' = None, model_name: 'str | None' = None, model_version: 'str | None' = None) -> 'ProductRecord'
```

## `SourceAdapter`

```python
SourceAdapter()
fetch(self, dataset: 'str', **params: 'Any') -> 'bytes'
iter_normalized_batches(self, dataset: 'str', payload: 'bytes', *, batch_size: 'int' = 1000, **context: 'Any') -> 'Iterator[list[dict]]'
iter_normalized_file(self, dataset: 'str', path: 'str | Path', *, batch_size: 'int' = 1000, **context: 'Any') -> 'Iterator[list[dict]]'
normalize(self, dataset: 'str', payload: 'bytes', **context: 'Any') -> 'list[dict]'
raw_extension_for(self, dataset: 'str', **params: 'Any') -> 'str'
should_index_identity(self, dataset: 'str') -> 'bool'
should_index_identity_request(self, dataset: 'str', **params: 'Any') -> 'bool'
```

## `MSISRun`

```python
MSISRun(data: 'pd.DataFrame', model_name: 'str', model_version: 'str', backend: 'str', backend_version: 'str', geomagnetic_activity: 'int', interpolate_indices: 'bool') -> None
```

```python
build_msis_inputs(trajectory: 'pd.DataFrame', *, f107: 'pd.DataFrame', ap_daily: 'pd.DataFrame', ap_3h: 'pd.DataFrame') -> 'pd.DataFrame'
```

```python
calculate_msis_density(inputs: 'pd.DataFrame', *, geomagnetic_activity: 'int' = -1, backend: 'Any | None' = None) -> 'MSISRun'
```

## 내장 dataset / Built-in datasets

provider-native fetch 지원과 canonical mapping은 다릅니다. / Native fetch support differs from canonical mapping.

| Source | Dataset | Canonical metric |
|---|---|---|
| cdaweb | `omni_hourly` | imf_bt, imf_bx_gse, imf_by_gse, imf_bz_gse, imf_by_gsm, imf_bz_gsm, solar_wind_speed, solar_wind_proton_density, solar_wind_proton_temperature |
| cdaweb | `omni_1min` | — (native fetch) |
| cdaweb | `omni_5min` | — (native fetch) |
| celestrak | `gp` | — (native fetch) |
| celestrak | `satcat` | — (native fetch) |
| discos | `objects` | — (native fetch) |
| donki | `cme` | — (native fetch) |
| donki | `cme_analysis` | — (native fetch) |
| donki | `geomagnetic_storm` | — (native fetch) |
| donki | `interplanetary_shock` | — (native fetch) |
| donki | `solar_flare` | — (native fetch) |
| donki | `sep` | — (native fetch) |
| donki | `magnetopause_crossing` | — (native fetch) |
| donki | `radiation_belt_enhancement` | — (native fetch) |
| donki | `high_speed_stream` | — (native fetch) |
| donki | `wsa_enlil` | — (native fetch) |
| donki | `notifications` | — (native fetch) |
| gcat | `satcat` | — (native fetch) |
| gcat | `satcat100k` | — (native fetch) |
| gcat | `satcat070k` | — (native fetch) |
| gcat | `satcat270k` | — (native fetch) |
| gcat | `satcat700M` | — (native fetch) |
| gcat | `usatcat` | — (native fetch) |
| gcat | `psatcat` | — (native fetch) |
| gcat | `psatcat100k` | — (native fetch) |
| gcat | `psatcat270k` | — (native fetch) |
| gcat | `pauxcat` | — (native fetch) |
| gcat | `pdeepcat` | — (native fetch) |
| gcat | `pftocat` | — (native fetch) |
| gcat | `plcat` | — (native fetch) |
| gcat | `prcat` | — (native fetch) |
| gcat | `ptmpcat` | — (native fetch) |
| gcat | `rcat` | — (native fetch) |
| gcat | `lprcat` | — (native fetch) |
| gcat | `vimcat` | — (native fetch) |
| gfz | `kp` | kp |
| gfz | `ap` | ap |
| gfz | `ap_daily` | ap_daily |
| gfz | `cp` | cp |
| gfz | `c9` | c9 |
| gfz | `hp30` | hp30 |
| gfz | `hp60` | hp60 |
| gfz | `ap30` | ap30 |
| gfz | `ap60` | ap60 |
| gfz | `sunspot` | ssn |
| gfz | `f107_observed` | f107_observed |
| gfz | `f107_adjusted` | f107_adjusted |
| launchlibrary | `payloads` | — (native fetch) |
| launchlibrary | `spacecraft` | — (native fetch) |
| launchlibrary | `spacecraft_configurations` | — (native fetch) |
| launchlibrary | `launches` | — (native fetch) |
| launchlibrary | `agencies` | — (native fetch) |
| launchlibrary | `programs` | — (native fetch) |
| lisird | `eve_bands` | — (native fetch) |
| lisird | `eve_lines` | — (native fetch) |
| lisird | `timed_see_lines` | — (native fetch) |
| lisird | `timed_see_xps` | — (native fetch) |
| lisird | `mgii` | — (native fetch) |
| lisird | `solar_radio` | — (native fetch) |
| lisird | `fism2_daily_bands` | — (native fetch) |
| lisird | `fism2_daily_spectrum` | — (native fetch) |
| lisird | `fism2_flare_bands` | — (native fetch) |
| lisird | `fism2_flare_spectrum` | — (native fetch) |
| noaa | `solar_cycle` | — (native fetch) |
| noaa | `f107_cycle` | — (native fetch) |
| noaa | `sunspots` | — (native fetch) |
| noaa | `f107_recent` | — (native fetch) |
| noaa | `f107_30day` | — (native fetch) |
| noaa | `kp_recent` | — (native fetch) |
| noaa | `dst_recent` | — (native fetch) |
| noaa | `goes_xray_1day` | — (native fetch) |
| noaa | `goes_xray_7day` | — (native fetch) |
| noaa | `goes_xray_flares_7day` | — (native fetch) |
| noaa | `goes_integral_protons_1day` | — (native fetch) |
| noaa | `goes_euvs_1day` | — (native fetch) |
| noaa | `goes_magnetometers_1day` | — (native fetch) |
| noaa | `rtsw_mag_1m` | imf_bt, imf_bx_gse, imf_by_gse, imf_bz_gse |
| noaa | `rtsw_wind_1m` | solar_wind_speed, solar_wind_proton_temperature, solar_wind_proton_density |
| noaa | `alerts` | — (native fetch) |
| nrcan | `f107_measurements` | f107_observed, f107_adjusted, f107_series_d |
| nrcan | `f107_legacy_daily_1947_1996` | f107_observed, f107_adjusted, f107_series_d |
| nrcan | `f107_legacy_measurements_1996_2007` | f107_observed, f107_adjusted, f107_series_d |
| satnogs | `satellites` | — (native fetch) |
| satnogs | `tle` | — (native fetch) |
| satnogs | `tle_historical` | — (native fetch) |
| satnogs | `transmitters` | — (native fetch) |
| satnogs | `optical_observations` | — (native fetch) |
| silso | `sunspot_daily` | ssn |
| silso | `sunspot_monthly` | ssn_monthly |
| silso | `sunspot_monthly_smoothed` | ssn_monthly_smoothed |
| spacetrack | `gp_history` | — (native fetch) |
| swarm | `density_a_acc` | thermosphere_neutral_mass_density |
| swarm | `density_b_acc` | thermosphere_neutral_mass_density |
| swarm | `density_c_acc` | thermosphere_neutral_mass_density |
| swarm | `density_a_pod` | thermosphere_neutral_mass_density, thermosphere_neutral_mass_density_orbit_mean |
| swarm | `density_b_pod` | thermosphere_neutral_mass_density, thermosphere_neutral_mass_density_orbit_mean |
| swarm | `density_c_pod` | thermosphere_neutral_mass_density, thermosphere_neutral_mass_density_orbit_mean |
| wdc_kyoto | `dst_hourly` | dst |
| wdc_kyoto | `ae_hourly` | ae, al, au, ao |
| wdc_kyoto | `ae_minute` | ae, al, au, ao |
| wdc_kyoto | `asysym_minute` | asy_d, asy_h, sym_d, sym_h |
| wdc_kyoto | `kp_ap_3hour` | kp, ap |
| wdc_kyoto | `ap_daily` | ap_daily |
