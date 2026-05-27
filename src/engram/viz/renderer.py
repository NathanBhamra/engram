"""Render the knowledge graph to a self-contained HTML file."""

from __future__ import annotations

import json
import sqlite3
from importlib import resources
from pathlib import Path
from typing import Any

from jinja2 import Environment, PackageLoader, select_autoescape

from engram.viz import exporter, metrics
from engram.viz import theme as theme_mod


def _load_vendored_asset(name: str) -> str | None:
    """Return the contents of ``viz/assets/<name>`` or ``None`` if missing."""
    try:
        files = resources.files("engram.viz.assets")
        asset = files / name
        if asset.is_file():
            return asset.read_text(encoding="utf-8")
    except (FileNotFoundError, ModuleNotFoundError):
        return None
    return None


def render(
    conn: sqlite3.Connection,
    out_path: Path,
    *,
    theme_name: str = "dark",
    include_quarantined: bool = False,
) -> dict[str, Any]:
    """Build the graph payload and render the static HTML.

    Returns the export ``meta`` dict plus ``{path, sidebar_stats}``.
    """
    theme = theme_mod.resolve(theme_name)
    theme_dark = theme_mod.DARK
    theme_light = theme_mod.LIGHT
    payload = exporter.export(
        conn, theme=theme, include_quarantined=include_quarantined
    )
    stats = metrics.graph_stats(conn)

    env = Environment(
        loader=PackageLoader("engram.viz", "templates"),
        autoescape=select_autoescape(["html"]),
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template("static.html.jinja")

    vis_network_js = _load_vendored_asset("vis-network.min.js")
    rendered = template.render(
        theme=theme,
        theme_dark=theme_dark,
        theme_light=theme_light,
        initial_mode=theme.name,
        graph_json=json.dumps(payload, default=str),
        sidebar_stats=stats,
        vis_network_js=vis_network_js,
        vis_network_cdn=(
            "https://unpkg.com/vis-network@9.1.9/standalone/umd/vis-network.min.js"
        ),
    )

    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(rendered, encoding="utf-8")
    return {
        "path": str(out_path),
        "meta": payload["meta"],
        "sidebar_stats": stats,
        "asset_mode": "vendored" if vis_network_js else "cdn",
    }
