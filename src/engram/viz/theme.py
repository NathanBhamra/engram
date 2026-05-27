"""Theme and visual constants for the viewer."""

from __future__ import annotations

from dataclasses import dataclass

# Node colour by node_type. iOS palette, picked for hue separation.
_NODE_COLOURS_DARK: dict[str, str] = {
    "fact": "#5e5ce6",  # iOS indigo
    "pattern": "#30d158",  # iOS green
    "decision": "#ff375f",  # iOS pink
    "reference": "#ff9f0a",  # iOS orange
}
_NODE_COLOURS_LIGHT: dict[str, str] = {
    "fact": "#5856d6",
    "pattern": "#34c759",
    "decision": "#ff2d55",
    "reference": "#ff9500",
}

# Edge colour by edge_type. Muted to stay quiet behind the nodes.
_EDGE_COLOURS_DARK: dict[str, str] = {
    "wiki-link": "#5e5ce6",
    "co-recall": "#30d158",
    "shared-tag": "#8e8e93",
    "manual": "#ff9f0a",
}
_EDGE_COLOURS_LIGHT: dict[str, str] = {
    "wiki-link": "#5856d6",
    "co-recall": "#34c759",
    "shared-tag": "#636366",
    "manual": "#ff9500",
}

# Stale (past-TTL) overlay.
_STALE_COLOUR = "#48484a"
_QUARANTINE_COLOUR = "#3a2a2a"


@dataclass(frozen=True)
class Theme:
    """A resolved viewer theme."""

    name: str
    background: str
    foreground: str
    sidebar_bg: str
    node_colours: dict[str, str]
    edge_colours: dict[str, str]
    stale_colour: str
    quarantine_colour: str


DARK = Theme(
    name="dark",
    background="#000000",
    foreground="#f2f2f7",
    sidebar_bg="rgba(28, 28, 30, 0.72)",
    node_colours=_NODE_COLOURS_DARK,
    edge_colours=_EDGE_COLOURS_DARK,
    stale_colour=_STALE_COLOUR,
    quarantine_colour=_QUARANTINE_COLOUR,
)

LIGHT = Theme(
    name="light",
    background="#f2f2f7",
    foreground="#1c1c1e",
    sidebar_bg="rgba(255, 255, 255, 0.78)",
    node_colours=_NODE_COLOURS_LIGHT,
    edge_colours=_EDGE_COLOURS_LIGHT,
    stale_colour="#aeaeb2",
    quarantine_colour="#d4a3a3",
)


def resolve(name: str | None) -> Theme:
    """Return the named theme, defaulting to :data:`DARK`."""
    if name is None or name.lower() == "dark":
        return DARK
    if name.lower() == "light":
        return LIGHT
    raise ValueError(f"unknown theme: {name!r}")


def node_size(degree: int, pagerank: float) -> int:
    """Pixel size for a node given its degree and pagerank.

    Both metrics are blended so a node that's heavily connected *and* highly
    central reads as biggest. Tuned for graphs of 10 - 1 000 nodes.
    """
    base = 12
    by_degree = min(degree * 2, 40)
    by_rank = int(pagerank * 200)
    return base + by_degree + by_rank
