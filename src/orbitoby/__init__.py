from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

try:
    __version__ = _dist_version("orbitoby")
except PackageNotFoundError:
    __version__ = "0+unknown"

from orbitoby._easy import Study, study
from orbitoby._easy_discovery import (
    artifacts,
    credits,
    dataset,
    datasets,
    install_sources_entrypoint,
    licenses,
    plugins,
    source,
)
from orbitoby._easy_help import help
from orbitoby._easy_login import login
from orbitoby._easy_management import (
    add_source,
    rebuild_index,
    refresh_sources,
    remove_source,
    trust_plugin,
    untrust_plugin,
)
from orbitoby.research import ResearchWindow
from orbitoby.service import Archive
from orbitoby.warehouse.products import (
    ProductParent,
)

__all__ = [
    "Archive",
    "ProductParent",
    "ResearchWindow",
    "Study",
    "add_source",
    "artifacts",
    "credits",
    "dataset",
    "datasets",
    "help",
    "licenses",
    "login",
    "plugins",
    "rebuild_index",
    "refresh_sources",
    "remove_source",
    "source",
    "sources",
    "study",
    "trust_plugin",
    "untrust_plugin",
]


install_sources_entrypoint()
