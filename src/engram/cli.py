"""Engram command-line entry point.

The CLI is a thin shell: each subcommand lives in :mod:`engram.commands` and is
registered here. This keeps individual commands testable in isolation and
ensures ``--help`` output is generated declaratively by ``click``.
"""

from __future__ import annotations

import click

from engram.version import __version__


@click.group(
    context_settings={"help_option_names": ["-h", "--help"]},
    help="Engram — a deterministic, local-first AI memory layer.",
)
@click.version_option(__version__, "-V", "--version", prog_name="engram")
@click.option(
    "--config",
    "config_path",
    type=click.Path(dir_okay=False, path_type=str),
    default=None,
    help="Path to a engram.toml configuration file. Default: ./engram.toml then ~/.engram.toml.",
)
@click.pass_context
def main(ctx: click.Context, config_path: str | None) -> None:
    """Root command. Subcommands attach below."""
    ctx.ensure_object(dict)
    ctx.obj["config_path"] = config_path


# Subcommand registrations.
#
# Each command lives in its own module under ``engram.commands``. Phase 0 ships
# the skeleton; subsequent phases flesh each one out without changing this
# wiring. Importing here (rather than at module-load time of the package) keeps
# import cost down and makes failures point at the offending subcommand.

from engram.commands import (  # noqa: E402  (ordered after click group definition)
    audit,
    autostore,
    doctor,
    forget,
    list_stale,
    rebuild,
    recall,
    store,
    usage,
    verify,
    view,
)

main.add_command(store.store)
main.add_command(autostore.autostore)
main.add_command(recall.recall)
main.add_command(verify.verify)
main.add_command(list_stale.list_stale)
main.add_command(rebuild.rebuild)
main.add_command(view.view)
main.add_command(audit.audit)
main.add_command(doctor.doctor)
main.add_command(usage.usage)
main.add_command(forget.forget)


if __name__ == "__main__":
    main()
