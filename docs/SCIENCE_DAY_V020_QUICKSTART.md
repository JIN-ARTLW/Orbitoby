# Orbitoby v0.2.0 — Science Day Quick Start

**범위:** 이 안내서는 Science Day용 실사용 기능을 설명합니다. 별도로 존재하는 연구용 Archive API를 변경하지 않습니다.

## 1. 첫 사용

```python
import orbitoby as ob

study = ob.study('2024-01-01', '2025-01-01')

# 스타링크를 포함한 카탈로그 탐색. 카탈로그 스냅샷은 과거 궤도 기록이 아닙니다.
satellites = study.catalog('starlink')
satellites.show()

# 특정 위성 선택; NORAD 번호는 예시이며 로컬 카탈로그에 존재해야 합니다.
chosen = study.catalog('all').find('SWARM')
chosen.show()

# 관측 기반 장기 태양활동 자료. 연구기간은 study()에서 설정합니다.
solar = study.solar('F10.7')
solar.show()
solar.where(above=200).show()
solar.plot(highlight=('2024-01-01', '2024-06-01'), above=200).save('activity.svg')
solar.plot(above=200).save('activity.png')
solar.export('solar_research_bundle')
solar.sources().show()
```

## 2. 역사적 궤도 자료와 카탈로그의 구분

`study.catalog('all')`은 **위성 식별자와 GP 스냅샷의 집합**입니다. 이 명령만으로 모든 위성의 역사적 GP_HISTORY을 다운로드하지 않습니다. 실제 궤도 기록은 기존 `study.orbit()`에서 가져옵니다.

```python
study = ob.study('2019-11-01', '2019-12-01')
orbit = study.orbit(22, sync=False)  # 캐시에 실제 자료가 있을 때
orbit.plot('mean_motion').save('mean_motion.svg')
orbit.sources().show()
```

원하는 위성을 카탈로그에서 선택한 후 개수를 제한하여 조회할 수도 있습니다.

```python
chosen = study.catalog('all').find(22)
orbit = study.orbit(*chosen.ids, sync=False)
```

## 3. 분석 및 출력

- `solar.where(start='2024-05-01', end='2024-06-01')`: UTC `[start, end)` 기간 선택
- `solar.where(above=200)` / `solar.where(below=100)`: 관측값 임계값 선택(경계 포함)
- `solar.plot(highlight=('2024-01-01','2024-07-01'))`: 원본 데이터를 없애지 않고 기간 음영 표시
- `solar.export('output_dir')`: CSV·PNG·SVG, 각각의 `.sources.json`, SHA-256이 있는 `bundle_manifest.json`을 한 번에 저장
- `study.catalog('starlink').export('catalog_dir')`: 위성 카탈로그 CSV·출처 명세 저장(타임시리즈가 아니므로 그림 없음)
- `solar.export('large_output', parquet=True)`: Parquet 추가 저장(필요한 드라이버 설치 확인)

모든 결과의 `.sources()`에서 **실제로 기여한 출처**를 확인합니다. 출처가 없는 관측 기록을 만들거나, 결측을 조용히 보간하지 않습니다.

## 4. 물리량·데이터 제품의 의미

- 캐나다 NRCan F10.7: `study.solar('F10.7')` (observed); `study.solar('F10.7 adjusted')`는 태양-지구 거리 보정 제품
- WDC SILSO: `study.solar('SSN')` (평활된 월간 흑점수; provisional 여부 확인)
- GFZ Potsdam: `study.solar('Kp')`, `study.solar('ap (3h)')`, `study.solar('daily Ap')`
- 기존 `study.weather('Dst')`는 기존 Orbitoby 엔진의 제공처 설정을 따릅니다. Kyoto 제품과의 과학적 동등성을 자동으로 가정하지 않습니다.
- 극대/극소기는 SILSO의 공인 주기 테이블 또는 사용자가 지정한 연구기간을 참조합니다. **F10.7 200 이상 = 극대기**라고 자동 판정하지 않습니다.
- 카탈로그의 현재 GP와 SpaceX SupGP는 서로 다른 제품이며, 역사적 관측을 대신하지 않습니다.

## 5. 제한 사항

- 카탈로그 규모와 최신 epoch는 제공처마다 다르며, 카탈로그를 조회한 시점과 연구기간의 위성 존재 여부를 혼동하지 마세요.
- Space-Track 인증, 제공처 응답, 서비스 약관은 사용자가 별도로 확인해야 합니다.
- F10.7 일별/현대 제품의 중복 날짜는 명시적 우선순위로 정리됩니다. 시간축 자동 보간·출처 혼합은 없습니다.
- 0.2.0 릴리스는 PyPI 배포와 구분됩니다. 테스트된 wheel을 만든 뒤 별도 승인·GitHub CI 확인이 필요합니다.
