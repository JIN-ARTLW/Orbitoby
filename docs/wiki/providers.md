# 데이터 Provider / Data providers

Orbitoby v0.1.1에는 15개의 built-in source adapter가 등록되어 있습니다. 아래 표의 `status`는 Orbitoby 내부 분류이며, 모든 기간·dataset의 live 가용성을 보증하지 않습니다.

Orbitoby v0.1.1 registers 15 built-in source adapters. The `status` below is Orbitoby's internal classification and does not guarantee live availability for every period or dataset.

| Source | 상태 / Status | 인증 / Auth | 주요 범위 / Scope |
|---|---|---|---|
| `cdaweb` | experimental | none | NASA SPDF CDAWeb HAPI, OMNI solar wind/IMF/geomagnetic |
| `celestrak` | stable | none | satellite catalogue, GP orbital elements |
| `discos` | restricted | token | ESA DISCOS object/physical metadata |
| `donki` | stable | none | NASA DONKI space-weather events/models/notifications |
| `gcat` | stable | none | General Catalog of Artificial Space Objects |
| `gfz` | stable | none | Kp, ap/Ap, Hpo, solar indices |
| `launchlibrary` | experimental | none | launch/mission/agency/spacecraft metadata |
| `lisird` | experimental | none | LASP LISIRD solar irradiance and indices |
| `noaa` | stable | none | NOAA SWPC solar/geospace products |
| `nrcan` | stable | none | DRAO / Space Weather Canada F10.7 |
| `satnogs` | experimental | none | satellite, TLE, transmitter, observation metadata |
| `silso` | stable | none | International Sunspot Number v2 |
| `spacetrack` | restricted | account | authenticated historical GP data |
| `swarm` | experimental | none | ESA Swarm thermospheric density via VirES HAPI |
| `wdc_kyoto` | experimental | none | Dst, AE, ASY/SYM, Kp/ap via WDC Kyoto HAPI |

## 등록 source 확인 / Inspect registered sources

```python
from orbitoby import Archive

with Archive() as archive:
    print(archive.sources_available())
    print(archive.source_info("gfz"))
```

`source_info()`는 title, homepage, docs URL, auth, status, categories, host allowlist, dataset 목록과 policy metadata를 반환합니다.

`source_info()` returns title, homepage, documentation URL, auth mode, status, categories, host allowlist, datasets, and policy metadata.

## Curated dataset 탐색 / Curated dataset discovery

```python
with Archive() as archive:
    rows = archive.datasets(source="gfz")
    for row in rows:
        print(row)
```

전체 built-in dataset inventory와 public API signature는 [API inventory](api-inventory.md)를 참고하세요.

See [API inventory](api-inventory.md) for the full built-in dataset inventory and public signatures.

## 주요 provider별 dataset / Notable datasets

### CDAWeb

`omni_hourly`, `omni_1min`, `omni_5min`

OMNI solar-wind/IMF/geomagnetic series를 HAPI로 접근합니다.

Provides HAPI access to OMNI solar-wind, IMF, and geomagnetic series.

### CelesTrak

`gp`, `satcat`

현재 catalogue와 orbital-element data를 제공합니다. 기간 population은 SATCAT의 launch/decay assertions를 이용합니다.

Provides catalogue and orbital-element data. Period population queries use launch/decay assertions from SATCAT.

### ESA DISCOS

`objects`

토큰 인증이 필요합니다. Citation이 요구되는 restricted source로 취급합니다.

Requires a token. Orbitoby treats it as a restricted source with citation requirements.

### NASA DONKI

`cme`, `cme_analysis`, `geomagnetic_storm`, `interplanetary_shock`, `solar_flare`, `sep`, `magnetopause_crossing`, `radiation_belt_enhancement`, `high_speed_stream`, `wsa_enlil`, `notifications`

사건·모델·알림 자료용 provider입니다.

Provider for event, model, and notification data.

### GCAT

`satcat`, `satcat100k`, `satcat070k`, `satcat270k`, `satcat700M`, `usatcat`, `psatcat`, `psatcat100k`, `psatcat270k`, `pauxcat`, `pdeepcat`, `pftocat`, `plcat`, `prcat`, `ptmpcat`, `rcat`, `lprcat`, `vimcat`

인공 우주물체와 관련 metadata catalogue입니다.

Catalogue of artificial space objects and related metadata.

### GFZ

`kp`, `ap`, `ap_daily`, `cp`, `c9`, `hp30`, `hp60`, `ap30`, `ap60`, `sunspot`, `f107_observed`, `f107_adjusted`

Orbitoby v0.1.1에서 가장 중요한 canonical space-weather source 중 하나입니다. 등록 policy는 CC BY 4.0이며 citation required입니다.

One of the principal canonical space-weather sources in v0.1.1. Registered policy metadata is CC BY 4.0 with citation required.

### Launch Library 2

`payloads`, `spacecraft`, `spacecraft_configurations`, `launches`, `agencies`, `programs`

발사·임무·기관·우주선 metadata를 제공합니다.

Provides launch, mission, agency, and spacecraft metadata.

### LISIRD

`eve_bands`, `eve_lines`, `timed_see_lines`, `timed_see_xps`, `mgii`, `solar_radio`, `fism2_daily_bands`, `fism2_daily_spectrum`, `fism2_flare_bands`, `fism2_flare_spectrum`

태양복사·태양지수 계열입니다.

Solar irradiance and solar-index series.

### NOAA SWPC

`solar_cycle`, `f107_cycle`, `sunspots`, `f107_recent`, `f107_30day`, `kp_recent`, `dst_recent`, `goes_xray_1day`, `goes_xray_7day`, `goes_xray_flares_7day`, `goes_integral_protons_1day`, `goes_euvs_1day`, `goes_magnetometers_1day`, `rtsw_mag_1m`, `rtsw_wind_1m`, `alerts`

rolling/near-real-time products가 포함됩니다. 장기간 archive와 같은 의미로 간주하면 안 됩니다.

Includes rolling and near-real-time products; do not assume they are equivalent to long-term archives.

### NRCan / DRAO F10.7

`f107_measurements`, `f107_legacy_daily_1947_1996`, `f107_legacy_measurements_1996_2007`

관측 F10.7과 legacy products를 제공합니다.

Provides observed F10.7 and legacy products.

### SatNOGS

`satellites`, `tle`, `tle_historical`, `transmitters`, `optical_observations`

위성·무선·TLE/관측 metadata provider입니다.

Satellite/radio/TLE/observation metadata provider.

### SILSO

`sunspot_daily`, `sunspot_monthly`, `sunspot_monthly_smoothed`

등록 policy는 CC BY-NC 4.0이며 citation required, commercial use restricted입니다.

Registered policy metadata is CC BY-NC 4.0 with citation required and commercial use restricted.

### Space-Track

`gp_history`

계정 인증이 필요한 historical orbital-element source입니다.

Authenticated historical orbital-element source.

### ESA Swarm / VirES

`density_a_acc`, `density_b_acc`, `density_c_acc`, `density_a_pod`, `density_b_pod`, `density_c_pod`

관측 기반 provider-derived thermospheric density입니다. 등록 policy는 citation required이며 redistribution은 restricted로 표시됩니다.

Observation-derived thermospheric density. Registered policy metadata requires citation and marks redistribution as restricted.

### WDC Kyoto

`dst_hourly`, `ae_hourly`, `ae_minute`, `asysym_minute`, `kp_ap_3hour`, `ap_daily`

지자기 index를 제공합니다. 등록 policy는 citation required, commercial use restricted입니다.

Provides geomagnetic indices. Registered policy metadata marks citation as required and commercial use as restricted.

## 중요한 원칙 / Important boundary

Source가 등록되어 있다는 사실은 다음을 의미하지 않습니다.

A registered source does **not** imply:

- 모든 dataset에 canonical mapping이 존재함 / every dataset has a canonical mapping
- 모든 기간이 live로 조회됨 / all periods are live-queryable
- license/redistribution 판단을 Orbitoby가 대신함 / Orbitoby replaces your licensing judgement
- 실험적 provider가 stable provider와 동일한 보증을 가짐 / experimental providers have stable-level guarantees

연구/배포 전에는 `source_info()`, provider 원문 약관, citation requirement를 확인하세요.

Before research publication or redistribution, review `source_info()`, the provider's own terms, and citation requirements.
