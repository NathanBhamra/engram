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
    help="Output HTML path (default: from config, usually viz.html).",
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
@click.pass_context
def view(
    ctx: click.Context,
    open_browser: bool,
    out_path: Path | None,
    theme: str | None,
    include_quarantined: bool,
    no_recompute: bool,
) -> None:
    """Render the knowledge graph as a self-contained HTML file."""
    config, conn, _, _ = resolve_paths(ctx)
    target = out_path
    if target is None:
        base = config.source.parent if config.source else Path.cwd()
        target = (base / config.get("paths", "viz_out", default="viz.html")).resolve()
    theme_name = theme or config.get("viz", "theme", default="dark")

    try:
        if not no_recompute:
            edge_counts = edges_mod.recompute_derived(conn)
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
