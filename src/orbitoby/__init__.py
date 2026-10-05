from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as _dist_version

try:
    __version__ = _dist_version("orbitoby")
except PackageNotFoundError:
    __version__ = "0+unknown"

from orbitoby.research import ResearchWindow
from orbitoby.service import Archive
from orbitoby.warehouse.products import (
    ProductParent,
)

__all__ = [
    "Archive",
    "ProductParent",
    "ResearchWindow",
]
