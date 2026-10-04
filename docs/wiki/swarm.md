# Swarm 관측 기반 밀도 / Swarm observation-derived density

VirES HAPI를 통해 A/B/C의 ACC 및 POD dataset 6개를 제공합니다. `density_a_pod` 등 dataset을 명시해야 합니다. ACC는 accelerometer retrieval, POD는 orbit-derived retrieval이며 canonical artifact_kind는 `provider_derived`입니다. MSIS model_output과 구분합니다.

Six A/B/C ACC/POD datasets are available via VirES HAPI. Choose a dataset explicitly. ACC and POD use different retrieval methods and have provider_derived artifact kind, distinct from MSIS model_output.

```python
with Archive() as archive:
    density = archive.timeseries(
        "thermosphere_neutral_mass_density",
        source="swarm",
        dataset="density_a_pod",
        start="2024-05-10",
        end="2024-05-11",
    )
```

POD의 `thermosphere_neutral_mass_density_orbit_mean`은 별도의 provider orbit-mean field입니다. Orbitoby가 직접 평균을 낸 결과가 아닙니다. density 단위는 kg/m^3, geodetic Height_GD는 m, Latitude_GD/Longitude_GD는 degree입니다. MSIS trajectory로 넘길 때만 height / 1000을 명시합니다.

POD orbit-mean density is a separate provider field, not an Orbitoby average. Density is kg/m^3; geodetic height is metres and coordinates are degrees. Explicitly divide height by 1000 for MSIS kilometres.

문서화된 density fill은 결측으로 보존하고 원값·quality_flag·context를 유지합니다. 품질 flag가 있다는 이유로 자동 제거하지 않습니다. 연구자는 flag 의미, 음수/비물리적 density, 위치·시간·coverage를 검토하고 명시적 QC를 정해야 합니다. 정확히 2,880행이어도 모든 행이 사용 가능한 관측이라는 뜻은 아닙니다.

Documented fills become missing values while original values, quality and context remain. Flags do not silently remove records. Researchers must assess flags, nonphysical values, position, time and coverage and define explicit QC. Exactly 2,880 rows do not certify 2,880 usable observations.
