"""Beginner-facing help backed by the currently installed Easy API."""

import difflib
import importlib
import inspect

_TOPICS = {
    "start": """
연구 시작하기
    import orbitoby as ob
    study = ob.study("2024-05-10", "2024-05-20")

연구기간은 UTC [start, end)입니다.
종료 날짜는 포함하지 않습니다.
""",
    "weather": """
우주환경 자료

    study.weather("Kp")
    study.weather("F10.7", "Kp", "Dst").plot()

현재 확인된 쉬운 이름: Kp, Dst, F10.7
자료에 없는 시각을 임의로 보간하지 않습니다.
""",
    "kp": """
Kp — 행성 지자기 지수

3시간 단위의 지자기 활동 지수입니다.
기본 연결: GFZ의 Kp 제품
단위: 무차원

    study.weather("Kp")
    study.weather("Kp", source="GFZ")

실제 조회 기간과 제품 출처는 결과의 info()/sources()로 확인하세요.
""",
    "dst": """
Dst — 지자기 폭풍 관련 지수

기본 연결: WDC Kyoto
단위: nT

    study.weather("Dst")

제공 기관과 원 관측망은 서로 다른 개념입니다.
""",
    "f10.7": """
F10.7 — 10.7 cm 태양 전파 플럭스

현재 쉬운 문법은 observed F10.7 제품을 선택합니다.
기본 연결: GFZ
단위: sfu

    study.weather("F10.7")

Observed와 adjusted 제품을 임의로 혼합하지 않습니다.
""",
    "satellites": """
인공위성 목록

    satellites = study.satellites()
    satellites.show()
    chosen = satellites.pick(39452)

위성 목록의 존재 정보와 실제 과거 궤도 epoch는 다릅니다.
""",
    "orbit": """
과거 궤도 자료

    orbit = study.orbit(39452)
    orbit.show()
    orbit.plot()
    orbit.plot("inclination")
    orbit.check(altitude=(300, 700), coverage=0.8).show()

실제 orbital element epoch만 사용합니다.
관측되지 않은 시각의 궤도를 자동 생성하지 않습니다.
Space-Track 인증이 필요할 수 있습니다.
""",
    "coverage": """
궤도 Coverage

관측 기간 중 실제 궤도 레코드가 존재하는 UTC 날짜의 비율입니다.
전체 시간에서 연속 관측된 비율과 다릅니다.

    orbit.check(coverage=0.8).show()
""",
    "swarm": """
Swarm 관측 기반 자료

    observed = study.swarm("A").density()
    trajectory = study.swarm("A").trajectory()
    observed.plot()

A/B/C는 서로 다른 Swarm 위성을 의미합니다.
관측 기반 제품과 수치 모델 결과를 구분합니다.
""",
    "density": """
중성 대기 밀도: 관측 기반 제품과 모델 출력

    observed = study.swarm("A").density()
    modeled = study.msis("A")
    observed.compare(modeled).plot()

Swarm 제품은 관측 기반 파생 자료입니다.
MSIS 결과는 수치 모델 출력입니다.
두 결과의 생산 방식과 입력 출처가 같다는 뜻이 아닙니다.
""",
    "msis": """
NRLMSIS 밀도 모델

    inputs = study.msis_inputs("A")
    inputs.show()
    modeled = study.msis("A")

실제 위성 궤적과 F10.7/Ap 등의 입력이 필요합니다.
모델 계산에는 선택적 models 설치 구성이 필요할 수 있습니다.
실제 입력 출처와 모델 계보는 결과 sources()/info()에서 확인합니다.
""",
    "align": """
실제 시각을 기준으로 정렬

    aligned = study.align(weather, observed)
    aligned.show()
    aligned.save("research.csv")

UTC 타임스탬프의 정확한 합집합을 사용합니다.
보간, 리샘플링, 결측값 자동 채우기는 하지 않습니다.
""",
    "compare": """
두 과학 결과의 비교

    comparison = observed.compare(modeled)
    comparison.show()
    comparison.plot()

같은 물리량과 호환 단위를 먼저 확인합니다.
다른 물리량 사이의 물리적 오차를 임의로 계산하지 않습니다.
""",
    "plot": """
그래프 그리기

    study.weather("Kp").plot()
    observed.compare(modeled).plot()
    orbit.plot("inclination")

SVG 그림에는 원본 제품, 데이터 역할, 상세 출처와
모델이 실제 사용한 입력 출처를 연결해 표시합니다.
""",
    "save": """
결과 저장하기

    result.save("research.csv")
    result.plot().save("figure.svg")

현재 결과 종류에 따라 생성되는 보조 메타데이터 파일이 다릅니다.
공통 내보내기 정책의 통합 검증은 아직 남아 있습니다.
""",
    "sources": """
데이터 출처 확인하기

    result.sources().show()
    result.sources().open()

결과에 실제 기여한 제공처와 관측·생산 기원을 구분합니다.

전체 등록 기관: ob.sources().show()
""",
    "gfz": """
GFZ — 우주환경 데이터 제공처

현재 확인된 쉬운 연결:
    study.weather("Kp", source="GFZ")
    study.weather("F10.7", source="GFZ")

GFZ라는 제공처명만으로 원 관측 장비를 결정하지 않습니다.
등록된 GFZ 자료는 ob.datasets(source='GFZ').show()로 확인합니다.
""",
    "provenance": """
과학적 출처와 계보

    result.sources().show()
    figure = result.plot()
    figure.sources().show()

데이터를 내려받은 곳, 원 관측 기원,
가공 제품 생산자, 모델 계산과 입력을 구분합니다.
""",
    "data": """
데이터 탐색

현재 확인된 쉬운 데이터 이름:
    Kp, Dst, F10.7, Swarm density, MSIS density

전체 provider-native 데이터 탐색:
    ob.datasets().show()
    study.data("kp", source="GFZ")

등록된 provider-native 제품을 선택합니다.
반환값은 어댑터 정규화 레코드이며,
자동으로 canonical 시계열이라고 해석하지 않습니다.

미구현 기능의 자료를 사용 가능한 것처럼 표시하지 않습니다.
""",
    "artifacts": """
저장된 원본 자료 확인

    ob.artifacts().show()
    ob.artifacts(source="GFZ").show()

현재 로컬 아카이브에 보존된 원본 자료의 목록입니다.
내부 파일 경로·개인 요청정보는 기본 화면에서 제외합니다.
등록된 전체 데이터셋 목록은 ob.datasets().show()를 사용합니다.
""",
    "plugins": """
추가 데이터 제공 플러그인 탐색

    ob.plugins().show()

발견된 후보 목록이며 신뢰 또는 실행 승인을 뜻하지 않습니다.
아직 플러그인 신뢰·해제의 초보자용 명령은 구현 전입니다.
""",
    "credits": """
기관별 기여·인용 정보

    ob.credits().show()

등록된 제공기관의 명칭과 공식 홈페이지 정보를 표시합니다.
현재 연구 결과에 실제로 사용된 자료는 result.sources()로 확인합니다.
""",
    "licenses": """
데이터 이용 조건 확인

    ob.licenses().show()
    ob.source("GFZ").info()

등록된 기관의 라이선스와 정책을 표시합니다.
정책이 unknown이면 이용이 허용되었다는 뜻이 아닙니다.
""",
    "login": """
인증 및 계정 연결

    ob.login("Space-Track")

서버에서 인증 성공을 확인한 다음 사용합니다.
비밀번호를 코드 셀에 직접 입력하지 않습니다.
숨김 입력, 기존 보안 설정 또는 Colab Secrets를 이용합니다.

기존 자격증명을 바꾸고 싶으면:
    ob.login("Space-Track", prompt=True)

Orbitoby는 이 명령으로 영구 자격증명 저장을 추가하지 않습니다.
""",
}


_INDEX = (
    ("시작", "start"),
    ("태양·지자기", "weather"),
    ("인공위성·궤도", "satellites"),
    ("Swarm", "swarm"),
    ("NRLMSIS 모델", "msis"),
    ("밀도 비교", "density"),
    ("시간 정렬", "align"),
    ("그래프", "plot"),
    ("데이터 출처", "sources"),
    ("전체 기능", "all"),
)

_MODULES = (
    "orbitoby._easy",
    "orbitoby._easy_result",
    "orbitoby._easy_swarm",
    "orbitoby._easy_msis",
    "orbitoby._easy_trajectory",
    "orbitoby._easy_compare",
    "orbitoby._easy_align",
    "orbitoby._easy_sources",
    "orbitoby._easy_discovery",
    "orbitoby._easy_native",
)


def _signature(callable_object):
    try:
        return str(inspect.signature(callable_object))
    except (TypeError, ValueError):
        return "(signature unavailable)"


def public_easy_api():
    """Discover actual exported Easy commands and result methods."""
    import orbitoby as ob

    commands = {}

    for name in getattr(ob, "__all__", ()):
        member = getattr(ob, name)
        if inspect.isfunction(member) and member.__module__.startswith(
            "orbitoby._easy"
        ):
            commands[f"ob.{name}"] = _signature(member)

    if callable(getattr(ob, "sources", None)):
        commands["ob.sources"] = "()"

    for module_name in _MODULES:
        module = importlib.import_module(module_name)

        for _, cls in inspect.getmembers(module, inspect.isclass):
            if cls.__module__ != module.__name__:
                continue

            if not (
                cls.__name__ in {"Study", "Swarm", "SourceList", "CatalogItem"}
                or cls.__name__.endswith(("Result", "List"))
            ):
                continue

            for name, method in inspect.getmembers(cls, predicate=inspect.isfunction):
                if not name.startswith("_"):
                    commands[f"{cls.__name__}.{name}"] = _signature(method)

    return dict(sorted(commands.items()))


def help(topic=None):
    """Show Korean beginner help or inspect the actual Easy API."""
    if topic is not None and not isinstance(topic, str):
        raise TypeError('Use ob.help() or ob.help("Kp").')

    key = topic.strip().casefold() if topic is not None else ""

    if not key:
        print("Orbitoby 사용법\n")

        for label, name in _INDEX:
            print(f"  {label:<16} ob.help({name!r})")

        print(
            "\n첫 번째 예제:\n"
            "    import orbitoby as ob\n"
            '    study = ob.study("2024-05-10", "2024-05-20")\n'
            '    study.weather("Kp").plot()\n'
        )
        return

    if key == "all":
        commands = public_easy_api()

        print("Orbitoby — 현재 설치된 Easy API")
        print("아래는 실제 존재하는 함수의 시그니처입니다.")
        print("개별 기능의 실행·과학적 동등성 검증과는 구분합니다.\n")

        for name, signature in commands.items():
            print(f"  {name}{signature}")

        from orbitoby._easy_discovery import datasets, sources

        source_rows = sources().table.to_dict("records")
        dataset_rows = datasets().table.to_dict("records")

        print(f"\n등록된 제공기관 ({len(source_rows)}개):")
        for row in source_rows:
            print("  ", row.get("name", "not declared"))

        print(f"\n등록된 데이터셋 ({len(dataset_rows)}개):")
        for row in dataset_rows:
            provider = row.get("source", "not declared")
            dataset_name = (
                row.get("dataset")
                or row.get("dataset_id")
                or row.get("name")
                or "not declared"
            )
            print(f"  {provider} / {dataset_name}")

        print("\n도움말 주제:")
        print("  " + ", ".join(sorted(_TOPICS)))

        print(
            "\n아직 전체 명세를 충족하지 않은 부분:\n"
            "  등록 기관·데이터셋 레지스트리 자동 연동\n"
            "  모든 공개 함수별 검증된 실행 예제\n"
            "  결과별 records/coverage 및 변경형 관리 API 쉬운 경로\n"
            "  31개 Core 기능 동등성 테스트"
        )
        return

    if key in _TOPICS:
        print(_TOPICS[key].strip())
        return

    suggestions = difflib.get_close_matches(key, sorted(_TOPICS), n=4, cutoff=0.4)

    print(f"도움말 주제를 찾을 수 없습니다: {topic!r}")

    if suggestions:
        print("\n비슷한 주제:")
        for candidate in suggestions:
            print(f'    ob.help("{candidate}")')
    else:
        print('사용 가능한 주제는 ob.help("all")에서 확인하세요.')
