from __future__ import annotations

from typing import ClassVar

from orbitoby.sources.hapi import HAPISource


class SwarmSource(HAPISource):
    """ESA Swarm thermospheric-density access through VirES HAPI.

    Provider-native fields are preserved here. Orbitoby's
    canonical research layer later maps ``density`` to the
    observed thermospheric-density metric, distinct from
    modeled density such as MSIS.
    """

    name = "swarm"

    # Discovery metadata.  These values describe the provider
    # products; they do not alter scientific observations.
    dataset_objects: ClassVar[dict[str, tuple[str, ...]]] = {
        "density_a_acc": ("Swarm A",),
        "density_b_acc": ("Swarm B",),
        "density_c_acc": ("Swarm C",),
        "density_a_pod": ("Swarm A",),
        "density_b_pod": ("Swarm B",),
        "density_c_pod": ("Swarm C",),
    }

    dataset_cadence: ClassVar[dict[str, str]] = {
        "density_a_acc": "10 s",
        "density_b_acc": "10 s",
        "density_c_acc": "10 s",
        "density_a_pod": "30 s",
        "density_b_pod": "30 s",
        "density_c_pod": "30 s",
    }

    BASE_URL = "https://vires.services/hapi"

    REQUEST_STYLE = "3"

    INCLUDE_HEADER = True

    PROFILES: ClassVar[dict[str, str]] = {
        "density_a_acc": "SW_OPER_DNSAACC_2_",
        "density_b_acc": "SW_OPER_DNSBACC_2_",
        "density_c_acc": "SW_OPER_DNSCACC_2_",
        "density_a_pod": "SW_OPER_DNSAPOD_2_",
        "density_b_pod": "SW_OPER_DNSBPOD_2_",
        "density_c_pod": "SW_OPER_DNSCPOD_2_",
    }

    datasets = tuple(PROFILES)
