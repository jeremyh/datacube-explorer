"""
A simple command-line viewer of Explorer products
and time-periods.

Useful for testing Explorer-generated summaries from
scripts and the command-line.
"""
import sys
import time

import click
import structlog
from click import echo, secho

from cubedash._filters import sizeof_fmt
from cubedash.logs import init_logging
from cubedash.summary import SummaryStore
from datacube.config import LocalConfig
from datacube.index import Index, index_connect
from datacube.ui.click import config_option, environment_option, pass_config

_LOG = structlog.get_logger()


def _get_store(config: LocalConfig, variant: str, log=_LOG) -> SummaryStore:
    index: Index = index_connect(
        config, application_name=f"cubedash.show.{variant}", validate_connection=False
    )
    return SummaryStore.create(index, log=log)


@click.command(help=__doc__)
@environment_option
@config_option
@pass_config
@click.option("-v", "--verbose", is_flag=True)
@click.option(
    "-l",
    "--event-log-file",
    help="Output jsonl logs to file",
    type=click.Path(writable=True, dir_okay=True),
)
@click.option("--allow-cache/--no-cache", is_flag=True, default=True)
@click.argument("product_name")
@click.argument("year", type=int, required=False)
@click.argument("month", type=int, required=False)
@click.argument("day", type=int, required=False)
def cli(
    config: LocalConfig,
    allow_cache: bool,
    product_name: str,
    year: int,
    month: int,
    day: int,
    event_log_file: str,
    verbose: bool,
):
    """
    Print the recorded summary information for the given product
    """
    init_logging(open(event_log_file, "a") if event_log_file else None, verbose=verbose)

    store = _get_store(config, "setup")

    t = time.time()
    summary = store.get(product_name, year, month, day)
    t_end = time.time()
    product = store.get_product_summary(product_name)
    if product is None:
        echo(f"Unsummarised product {product_name}", err=True)
        sys.exit(-1)

    secho(product_name, bold=True)
    echo()
    dataset_count = summary.dataset_count if summary else product.dataset_count
    echo(f"{dataset_count}  datasets")

    if product.dataset_count:
        echo(f"from {product.time_earliest.isoformat()} ")
        echo(f"  to {product.time_latest.isoformat()} ")

    echo()
    if store.needs_extent_refresh(product_name):
        secho("Has changes", bold=True)

    echo(f"Last extent refresh:     {product.last_refresh_time}")
    echo(f"Last summary completion: {product.last_successful_summary_time}")

    if product.fixed_metadata:
        echo()
        secho("Metadata", fg="blue")
        for k, v in product.fixed_metadata.items():
            echo(f"\t{k}: {v}")

    if summary:
        echo()
        secho(f"Period: {year or 'all'} {month or 'all'} {day or 'all'}", fg="blue")
        if summary.size_bytes:
            echo(f"\tStorage size: {sizeof_fmt(summary.size_bytes)}")

        echo(f"\t{summary.dataset_count} datasets")
        echo(f"\tSummarised: {summary.summary_gen_time}")

    echo()
    echo(f"(fetched in {round(t_end - t, 2)} seconds)")


if __name__ == "__main__":
    cli()
