"""Beginner-friendly native plots with public source attribution."""

import json
from html import escape

import pandas as pd

from orbitoby.plotting import PlotAPI, PlotResult


def _text(value, y, *, bold=False):
    weight = "600" if bold else "400"
    return (
        f'<text x="28" y="{y}" font-size="11" '
        f'font-family="sans-serif" fill="#263242" '
        f'font-weight="{weight}">{escape(str(value))}</text>'
    )


def _link(label, url, y):
    """Render only public HTTPS links from the source registry."""
    if not isinstance(url, str) or not url.startswith("https://"):
        return ""

    safe_url = escape(url, quote=True)
    safe_label = escape(f"{label}: {url}")

    return (
        f'<a href="{safe_url}" target="_blank" '
        f'rel="noopener noreferrer">'
        f'<text x="28" y="{y}" font-size="10" '
        f'font-family="sans-serif" fill="#2563eb">'
        f"{safe_label}</text></a>"
    )


def plot_result(result, *, kind="auto", title=None, width=900, height=360, below=None):
    """Plot canonical values without changing timestamps or units."""

    from orbitoby._easy_result import DataResult

    additions = (
        ()
        if below is None
        else tuple(below)
        if isinstance(below, (list, tuple))
        else (below,)
    )

    results = (result, *additions)

    frames = []
    ordered_metrics = []

    required = {
        "timestamp",
        "metric",
        "value",
        "unit",
        "source",
        "dataset",
    }

    for item in results:
        if not isinstance(item, DataResult):
            raise TypeError("below must contain Orbitoby data results.")

        if pd.Timestamp(item.start) != pd.Timestamp(result.start) or pd.Timestamp(
            item.end
        ) != pd.Timestamp(result.end):
            raise ValueError("All plotted results must use the same study period.")

        part = item.provenance if hasattr(item, "_window") else item.table

        if not required.issubset(part.columns):
            raise ValueError(
                "This result is not a canonical time series. "
                "Use .show() or a suitable domain-specific plot."
            )

        if part.empty:
            raise ValueError(f"No observations available to plot: {item.name}")

        frames.append(part)

        metrics = (
            tuple(item._window.metrics)
            if hasattr(item, "_window")
            else tuple(dict.fromkeys(part["metric"].astype(str)))
        )

        ordered_metrics.extend(metrics)

    frame = pd.concat(frames, ignore_index=True)
    metrics = tuple(dict.fromkeys(ordered_metrics))

    sources = (
        pd.concat(
            [item.sources().table for item in results],
            ignore_index=True,
        )
        .drop_duplicates()
        .reset_index(drop=True)
    )
    metric_order = {name: index for index, name in enumerate(metrics)}
    sources = (
        sources.assign(_order=sources["metric"].map(metric_order))
        .sort_values("_order", kind="stable")
        .drop(columns="_order")
    )

    # One reference per displayed source/provenance record.
    exact_refs = {}
    product_refs = {}

    for number, (_, source_row) in enumerate(sources.iterrows(), start=1):
        reference = f"S{number}"
        source = str(source_row["source"])
        dataset = str(source_row["dataset"])
        metric = str(source_row["metric"])

        exact_refs.setdefault((metric, source, dataset), []).append(reference)
        product_refs.setdefault((source, dataset), []).append(reference)

    def source_reference(metric, source, dataset):
        exact = exact_refs.get((str(metric), str(source), str(dataset)), [])
        if len(exact) == 1:
            return exact[0]

        product = product_refs.get((str(source), str(dataset)), [])
        if len(product) == 1:
            return product[0]

        # Never invent a reference if multiple records could match.
        return None

    # Explicit dependency graph supplied by scientific result objects.
    # The plotting engine never infers model inputs from source names.
    def result_leaves(item):
        left = getattr(item, "left", None)
        right = getattr(item, "right", None)

        if isinstance(left, DataResult) and isinstance(right, DataResult):
            yield from result_leaves(left)
            yield from result_leaves(right)
        else:
            yield item

    dependency_links = {}

    for item in results:
        for leaf in result_leaves(item):
            getter = getattr(leaf, "source_dependencies", None)

            if not callable(getter):
                continue

            dependencies = getter()
            required_keys = {"metric", "source", "dataset"}

            if not isinstance(dependencies, pd.DataFrame) or not required_keys.issubset(
                dependencies.columns
            ):
                raise ValueError("Model input source metadata is incomplete.")

            direct = leaf.table[["metric", "source", "dataset"]].drop_duplicates()

            for _, output in direct.iterrows():
                output_ref = source_reference(
                    output["metric"],
                    output["source"],
                    output["dataset"],
                )

                if output_ref is None:
                    raise ValueError("Cannot identify the plotted model source.")

                links = dependency_links.setdefault(output_ref, [])

                for _, upstream in dependencies.iterrows():
                    input_ref = source_reference(
                        upstream["metric"],
                        upstream["source"],
                        upstream["dataset"],
                    )

                    if input_ref is None:
                        raise ValueError(
                            "Cannot identify a model input source. "
                            "Check the result's source metadata."
                        )

                    pair = (input_ref, str(upstream["metric"]))

                    if input_ref != output_ref and pair not in links:
                        links.append(pair)

    engine = PlotAPI()
    panels = []

    for metric in metrics:
        rows = frame.loc[frame["metric"].astype(str).eq(metric)].copy()

        if "plot_label" not in rows.columns:
            rows["plot_label"] = (
                rows["dataset"].astype(str) + " [" + rows["source"].astype(str) + "]"
            )

        references = [
            source_reference(metric_name, source, dataset)
            for metric_name, source, dataset in zip(
                rows["metric"],
                rows["source"],
                rows["dataset"],
                strict=True,
            )
        ]

        rows["plot_label"] = [
            f"{label} [{reference}]" if reference is not None else str(label)
            for label, reference in zip(rows["plot_label"], references, strict=True)
        ]

        def label_with_inputs(label, reference):
            links = dependency_links.get(reference, [])

            if not links:
                return str(label)

            shown = links[:6]
            refs = ", ".join(f"[{ref}]" for ref, _ in shown)

            if len(links) > len(shown):
                refs += f", +{len(links) - len(shown)} (see below)"

            return f"{label} | inputs: {refs}"

        rows["plot_label"] = [
            label_with_inputs(label, reference)
            for label, reference in zip(
                rows["plot_label"],
                references,
                strict=True,
            )
        ]

        panel_title = (
            metric
            if title is None
            else (title if len(metrics) == 1 else f"{title} - {metric}")
        )

        panel_kind = (
            "scatter"
            if kind == "auto" and metric in {"kp", "f107_observed"}
            else "line"
            if kind == "auto"
            else kind
        )

        panel = engine.plot(
            rows,
            kind=panel_kind,
            title=panel_title,
            width=width,
            height=height,
            time_range=(result.start, result.end),
        )
        panels.append(panel)

    footer = []
    y = height * len(panels) + 30

    footer.append(_text("Data sources and provenance", y, bold=True))
    y += 24

    # The complete source registry is embedded in SVG metadata,
    # not just the short visible attribution.

    if dependency_links:
        footer.append(_text("Input sources used by plotted results", y, bold=True))
        y += 23

        for output_ref, links in dependency_links.items():
            footer.append(_text(f"[{output_ref}] uses these inputs:", y, bold=True))
            y += 19

            for input_ref, role in links:
                footer.append(_text(f"    [{input_ref}] {role}", y))
                y += 17

            y += 12

    public_records = []

    for number, (_, source_row) in enumerate(sources.iterrows(), start=1):
        record = {
            key: source_row[key] if isinstance(source_row[key], str) else None
            for key in sources.columns
        }
        record["source_ref"] = f"S{number}"
        public_records.append(record)

    for number, (_, row) in enumerate(sources.iterrows(), start=1):
        footer.append(
            _text(
                f"[S{number}] {row['metric']} | {row['dataset']} | {row['provider']}",
                y,
                bold=True,
            )
        )
        y += 17

        footer.append(
            _text(
                f"Retrieved from: {row['source']} | Observed by: {row['observed_by']}",
                y,
            )
        )
        y += 17

        footer.append(
            _text(
                f"Produced by: {row['produced_by']} | "
                f"Retrieved at: {row['retrieved_at']}",
                y,
            )
        )
        y += 17

        data_url = row["data_page"]
        if not isinstance(data_url, str):
            data_url = row["provider_site"]

        if isinstance(data_url, str):
            footer.append(_link("Data page", data_url, y))
            y += 17

        origin_url = row["origin_reference"]
        if isinstance(origin_url, str):
            footer.append(_link("Origin reference", origin_url, y))
            y += 17

        y += 13

    total_height = y + 20

    metadata = {
        "sources": public_records,
        "source_usage": [
            {
                "output_ref": output_ref,
                "inputs": [
                    {"source_ref": input_ref, "role": role} for input_ref, role in links
                ],
            }
            for output_ref, links in dependency_links.items()
        ],
        "scientific_processing": {
            "interpolation": "none",
            "resampling": "none",
            "source_mixing": "none",
        },
    }

    elements = [
        (
            '<svg xmlns="http://www.w3.org/2000/svg" '
            f'width="{width}" height="{total_height}" '
            f'viewBox="0 0 {width} {total_height}" role="img">'
        ),
        "<title>Orbitoby research plot with data provenance</title>",
        f"<metadata>{escape(json.dumps(metadata, ensure_ascii=False))}</metadata>",
        f'<rect width="{width}" height="{total_height}" fill="white"/>',
    ]

    for index, panel in enumerate(panels):
        elements.append(f'<g transform="translate(0,{index * height})">{panel.svg}</g>')

    elements.extend(footer)
    elements.append("</svg>")

    return PlotResult(
        svg="".join(elements),
        data=frame.copy(),
        provenance=frame.copy(),
    )
