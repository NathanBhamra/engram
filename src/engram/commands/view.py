"""``engram view`` — render the knowledge graph as a static HTML file."""

from __future__ import annotations

import webbrowser
from pathlib import Path

import click

from engram.commands._shared import resolve_paths
from engram.viz import edges as edges_mod
from engram.viz import metrics as metrics_mod
from engram.viz import renderer


@click.command("view")
@click.option(
    "--open",
    "open_browser",
    is_flag=True,
    default=False,
    help="Open the generated HTML file in the default browser.",
)
@click.option(
    "--out",
    "out_path",
    type=click.Path(dir_okay=False, path_type=Path),
    default=None,
    help="Output HTML path (default: from config, usually viz.html / viz-3d.html).",
)
@click.option(
    "--theme",
    type=click.Choice(["dark", "light"]),
    default=None,
    help="Override the viewer theme.",
)
@click.option(
    "--include-quarantined",
    is_flag=True,
    default=False,
    help="Include quarantined nodes (greyed out) in the graph.",
)
@click.option(
    "--no-recompute",
    is_flag=True,
    default=False,
    help="Skip edge derivation and metric recomputation; render current state.",
)
@click.option(
    "--3d",
    "three_d",
    is_flag=True,
    default=False,
    help="Render the WebGL 3D viewer (3d-force-graph + bloom) instead of the 2D graph.",
)
@click.pass_context
def view(
    ctx: click.Context,
    open_browser: bool,
    out_path: Path | None,
    theme: str | None,
    include_quarantined: bool,
    no_recompute: bool,
    three_d: bool,
) -> None:
    """Render the knowledge graph as a self-contained HTML file."""
    config, conn, _, _ = resolve_paths(ctx)
    target = out_path
    if target is None:
        base = config.source.parent if config.source else Path.cwd()
        default_key = "viz_3d_out" if three_d else "viz_out"
        default_name = "viz-3d.html" if three_d else "viz.html"
        target = (
            base / config.get("paths", default_key, default=default_name)
        ).resolve()
    theme_name = theme or config.get("viz", "theme", default="dark")

    try:
        if not no_recompute:
            edge_counts = edges_mod.recompute_derived(conn, config=config)
            metric_stats = metrics_mod.recompute(conn)
            click.echo(
                f"Recomputed edges: {edge_counts} | "
                f"graph: {metric_stats['nodes']} nodes, "
                f"{metric_stats['edges']} edges, "
                f"{metric_stats['clusters']} clusters"
            )

        result = renderer.render(
            conn,
            target,
            theme_name=theme_name,
            include_quarantined=include_quarantined,
            three_d=three_d,
            config=config,
        )
    finally:
        conn.close()

    click.echo(
        f"Wrote {result['path']} "
        f"({result['meta']['node_count']} nodes, "
        f"{result['meta']['edge_count']} edges, "
        f"assets={result['asset_mode']})"
    )

    if open_browser:
        webbrowser.open(target.as_uri())
