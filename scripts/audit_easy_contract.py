"""Audit Orbitoby v0.1.2 Easy API against its 31 Core routes.

This is a surface audit, NOT proof of scientific equivalence.
No network access, provider login or archive mutations.
"""

import inspect
from pathlib import Path

import orbitoby as ob
from orbitoby._easy import Study
from orbitoby._easy_result import DataResult, OrbitResult, WindowResult
from orbitoby.service import Archive

ROUTES = [
    ("artifacts", ("ob.artifacts", "DataResult.artifacts")),
    ("close", ("Study.close",)),
    ("coverage", ("DataResult.coverage",)),
    ("credits", ("ob.credits", "DataResult.sources")),
    ("dataset_info", ("ob.dataset",)),
    ("datasets", ("ob.datasets",)),
    ("fetch", ("Study.data",)),
    ("get_source", ("ob.source",)),
    ("licenses", ("ob.licenses",)),
    ("msis_density", ("Study.msis",)),
    ("msis_inputs", ("Study.msis_inputs",)),
    ("object", ("Study.object",)),
    ("objects", ("Study.objects", "Study.satellites")),
    ("orbit", ("Study.orbit",)),
    ("orbit_summary", ("OrbitResult.check",)),
    ("plot", ("DataResult.plot",)),
    ("plot_timeseries", ("Study.weather", "DataResult.plot")),
    ("plugin_candidates", ("ob.plugins",)),
    ("records", ("DataResult.records",)),
    ("register_http_source", ("ob.add_source",)),
    ("reindex", ("ob.rebuild_index",)),
    ("reload_sources", ("ob.refresh_sources",)),
    ("search", ("Study.search",)),
    ("source_info", ("ob.source",)),
    ("sources_available", ("ob.sources",)),
    ("space_weather", ("Study.weather",)),
    ("timeseries", ("Study.weather", "Study.data")),
    ("trust_source_plugin", ("ob.trust_plugin",)),
    ("unregister_http_source", ("ob.remove_source",)),
    ("untrust_source_plugin", ("ob.untrust_plugin",)),
    ("window", ("Study.align",)),
]

ROOTS = {
    "ob": ob,
    "Study": Study,
    "DataResult": DataResult,
    "OrbitResult": OrbitResult,
    "WindowResult": WindowResult,
}


def exists(path):
    root, method = path.split(".", 1)
    return callable(getattr(ROOTS[root], method, None))


def run():
    assert len(ROUTES) == 31
    missing = []
    partial = []
    complete = []

    print("ORBITOBY v0.1.2 — CORE 31 ROUTE AUDIT")
    print("=" * 78)

    for index, (core, paths) in enumerate(ROUTES, 1):
        core_exists = callable(getattr(Archive, core, None))
        supported = [path for path in paths if exists(path)]
        unsupported = [path for path in paths if not exists(path)]

        if not core_exists or unsupported:
            status = "PARTIAL" if supported else "MISSING"
            (partial if supported else missing).append(core)
        else:
            status = "PRESENT"
            complete.append(core)

        print(f"{index:02d}. {core:<24} {status}")

        if not core_exists:
            print("    ! Core function itself is unavailable")

        for path in supported:
            print(f"    + {path}")

        for path in unsupported:
            print(f"    - {path}")

    print("\n" + "=" * 78)
    print("PRESENT routes:", len(complete))
    print("PARTIAL routes:", len(partial))
    print("MISSING routes:", len(missing))
    print("Total:", len(ROUTES))

    print("\nADDITIONAL CONTRACT CHECKS")

    extra = (
        ("ob.help", exists("ob.help")),
        ("ob.login", exists("ob.login")),
        ("Study.compare", exists("Study.compare")),
        ("DataResult.change", exists("DataResult.change")),
        ("DataResult.info", exists("DataResult.info")),
        ("WindowResult.save", exists("WindowResult.save")),
        ("OrbitResult.plot", exists("OrbitResult.plot")),
    )

    for name, available in extra:
        print(f"{'PRESENT' if available else 'MISSING':<9} {name}")

    info_signature = inspect.signature(DataResult.info)
    print(
        "DataResult.info(topic) supported:",
        "topic" in info_signature.parameters,
    )

    print("\nRELEASE GATE")
    print("This audit checks method presence only.")
    print("Scientific equivalence: NOT VERIFIED")
    print("Live provider access: NOT VERIFIED")
    print("Clean Colab execution: NOT VERIFIED")
    print("Export security: NOT FULLY VERIFIED")

    return len(missing) + len(partial)


if __name__ == "__main__":
    run()
