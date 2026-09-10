"""Collect the four primary metrics for two-bloc BT profiles listed in a settings file."""

import ast
import contextlib
import json
import sys
import warnings
from collections.abc import Callable, Sequence
from functools import partial
from itertools import batched
from pathlib import Path
from typing import Iterator, TypeAlias, TypedDict, cast

import click
from joblib import Parallel, delayed
from tqdm.auto import tqdm
from votekit import RankProfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from voting_metrics_main_code.constants import AllowedRule
from voting_metrics_main_code.fairness_metric import (  # noqa: E402
    sigma_IIA,
    sigma_IIA_random,
    sigma_IIA_winner_set,
    sigma_IIA_winner_set_random,
    sigma_UM,
    sigma_UM_winner_set,
)
from voting_metrics_main_code.replication import STATS_OUTPUT, new_data_file, seed_task
from voting_metrics_main_code.voting_rules import build_voting_rule  # noqa: E402

warnings.filterwarnings("ignore")

PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNS = (
    ("sigma_UM", sigma_UM, "worst_case", "asin"),
    ("sigma_UM_winner_set", sigma_UM_winner_set, "worst_case", "asin"),
    ("sigma_IIA", sigma_IIA, "average", "None"),
    ("sigma_IIA_winner_set", sigma_IIA_winner_set, "average", "None"),
)
RANDOM_METRICS = {
    sigma_IIA: sigma_IIA_random,
    sigma_IIA_winner_set: sigma_IIA_winner_set_random,
}

ProfileBatchTask: TypeAlias = tuple[
    tuple[tuple[int, Path], ...],
    int,
    int,
    AllowedRule,
    str,
    tuple[tuple[int, Callable[..., float], str, str], ...],
]
# Joblib must serialize this annotation when the collector runs as a standalone script.
BatchScores: TypeAlias = tuple[tuple[int, tuple[tuple[int, float], ...]], ...]


class OutputProgress(TypedDict):
    """Scores retain CSV order while parallel batches complete out of order."""

    output_file: Path
    scores: list[float | None]
    remaining_batches: int
    label: str


def output_jobs(
    input_folder: str | Path, n_seats: int, election_type: AllowedRule, tiebreak: str
) -> tuple[int, list[tuple[Callable[..., float], str, str, Path]]]:
    """Build metric jobs and output paths from a two-bloc profile directory name.

    Args:
        input_folder (str | Path): Two-bloc profile directory with encoded candidate and bloc
            parameters.
        n_seats (int): Number of seats to elect.
        election_type (AllowedRule): Voting rule name.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.

    Returns:
        tuple[int, list[tuple[Callable[..., float], str, str, Path]]]: Total candidate count and
            jobs containing the metric callable, variant, interpolation token, and output path.

    Raises:
        ValueError: Encoded candidate counts or bloc parameters cannot be parsed or unpacked.
        IndexError: The directory name lacks a required parameter segment.
        SyntaxError: An encoded alpha or cohesion tuple is not a valid Python literal.
    """
    input_folder = Path(input_folder).resolve()
    base_parts = input_folder.name.split("__")
    cand_parts = input_folder.parent.stem.split("_")

    b_proportion = float(base_parts[0].split("_")[-1])
    aa_alpha, ab_alpha, ba_alpha, bb_alpha = ast.literal_eval(base_parts[1].split("_")[-1])
    a_cohesion, b_cohesion = ast.literal_eval(base_parts[2].split("_")[-1])
    n_a_cands, n_b_cands = map(int, cand_parts)
    n_cands = n_a_cands + n_b_cands
    output_root = STATS_OUTPUT / "bt_2_bloc_profile_stats" / f"{n_seats}_seats"

    jobs = []

    for metric, metric_function, variant, interpolation_type in RUNS:
        basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{variant}"
            f"__INTERP_{interpolation_type}"
            f"__NCANDS_({n_a_cands:02d}_{n_b_cands:02d})"
            f"__SEATS_{n_seats}"
            f"__BPROP_{b_proportion:0.1f}"
            f"__ALPHA_({aa_alpha:0.2f},{ab_alpha:0.2f},{ba_alpha:0.2f},{bb_alpha:0.2f})"
            f"__COHESION_({a_cohesion:0.2f},{b_cohesion:0.2f})"
            f"__TYPE_{election_type}"
            f"__TIEBREAK_{tiebreak}.json"
        )
        output_file = output_root / metric / f"{n_cands:02d}" / election_type / basename

        jobs.append((metric_function, variant, interpolation_type, output_file))

    return n_cands, jobs


def run_profile_batch(
    profile_batch: Sequence[tuple[int, Path]],
    n_cands: int,
    n_seats: int,
    election_type: AllowedRule,
    tiebreak: str,
    metric_jobs: Sequence[tuple[int, Callable[..., float], str, str]],
) -> BatchScores:
    """Score a batch of profiles with a separate deterministic seed for each metric.

    Args:
        profile_batch (Sequence[tuple[int, Path]]): Pairs of CSV-order index and profile path.
        n_cands (int): Number of candidates.
        n_seats (int): Number of seats to elect.
        election_type (AllowedRule): Voting rule name.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
        metric_jobs (Sequence[tuple[int, Callable[..., float], str, str]]): Jobs containing output
            ID, metric callable, variant, and interpolation token.

    Returns:
        BatchScores: Results grouped by output ID as (output_id, ((profile_index, score), ...)). Each
            group retains the input batch order.

    Raises:
        FileNotFoundError: A profile CSV does not exist.
    """
    with contextlib.redirect_stdout(None):
        voting_rule = build_voting_rule(n_cands, election_type, tiebreak=tiebreak)
        metrics = []
        scores = {}

        for output_id, metric_function, variant, interpolation_type in metric_jobs:
            metric = partial(metric_function, n_seats=n_seats, variant=variant)

            if interpolation_type != "None":
                metric = partial(metric, interpolation_type=interpolation_type)

            metrics.append((output_id, metric))
            scores[output_id] = []

        for index, path in profile_batch:
            profile = RankProfile.from_csv(path)

            for output_id, metric in metrics:
                seed_task(
                    path.parent.parent.name,
                    path.parent.name,
                    path.name,
                    election_type,
                    tiebreak,
                    n_seats,
                    metric.func.__name__,
                    metric.keywords,
                )

                scores[output_id].append((index, metric(profile, voting_rule)))

    return tuple((output_id, tuple(values)) for output_id, values in scores.items())


def write_scores(output_file: Path, scores: list[float]) -> None:
    """Publish completed JSON scores without replacing an existing result.

    Args:
        output_file (Path): Destination file path.
        scores (list[float]): Completed metric scores in profile CSV order.

    Raises:
        FileExistsError: The result file exists and must be moved manually before recomputing.
        OSError: The output directory or temporary file cannot be written or published.
    """
    with new_data_file(output_file) as temporary_file, temporary_file.open("w") as file:
        json.dump(scores, file)


def load_profile_folders(settings_file: Path) -> list[Path]:
    """Resolve and validate all selected inputs before creating any outputs.

    Relative paths resolve against the repository root. Blank lines and comments are ignored;
    duplicate stripped entries are removed while retaining their first occurrence.

    Args:
        settings_file (Path): Text file listing profile directories, one per line.

    Returns:
        list[Path]: Resolved directories containing at least one profile CSV.

    Raises:
        FileNotFoundError: The settings file does not exist.
        click.ClickException: No profile folders are listed, or a listed folder is missing or has no
            CSVs.
    """
    input_folders = list(
        dict.fromkeys(line.strip() for line in settings_file.read_text().splitlines())
    )
    input_folders = [
        (Path(folder) if Path(folder).is_absolute() else PROJECT_ROOT / folder).resolve()
        for folder in input_folders
        if folder and not folder.startswith("#")
    ]

    if not input_folders:
        raise click.ClickException("The settings file contains no profile folders.")

    for folder in input_folders:
        if not folder.is_dir() or not any(folder.glob("*.csv")):
            raise click.ClickException(f"Missing or empty profile folder: {folder}")

    return input_folders


def prepare_tasks(
    input_folders: Sequence[Path],
    n_seats: int,
    election_type: AllowedRule,
    tiebreak: str,
    profile_batch_size: int,
) -> tuple[list[ProfileBatchTask], dict[int, OutputProgress], int, int]:
    """Build pending batch tasks and output progress, skipping existing result files.

    Empty profile folders produce empty JSON arrays immediately.

    Args:
        input_folders (Sequence[Path]): Profile directories to process, in task preparation order.
        n_seats (int): Number of seats to elect.
        election_type (AllowedRule): Voting rule name.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
        profile_batch_size (int): Maximum number of profiles per parallel task; must be positive.

    Returns:
        tuple[list[ProfileBatchTask], dict[int, OutputProgress], int, int]: Tasks accepted by
            run_profile_batch, progress keyed by output ID, skipped file count, and written file
            count.

    Raises:
        ValueError: The batch size is below one or encoded profile parameters are invalid.
    """
    tasks = []
    outputs: dict[int, OutputProgress] = {}
    skipped = 0
    written = 0

    for folder in tqdm(input_folders, desc="Preparing folders", unit="folder"):
        n_cands, folder_jobs = output_jobs(folder, n_seats, election_type, tiebreak)
        profile_files = sorted(Path(folder).resolve().glob("*.csv"))
        profile_batches = list(batched(enumerate(profile_files), profile_batch_size))
        metric_jobs = []

        for metric_function, variant, interpolation_type, output_file in folder_jobs:
            if output_file.exists() or output_file.is_symlink():
                skipped += 1
                continue

            output_id = len(outputs)
            outputs[output_id] = {
                "output_file": output_file,
                "scores": [None] * len(profile_files),
                "remaining_batches": len(profile_batches),
                "label": f"{output_file.parents[2].name}: {Path(folder).name}",
            }

            if not profile_batches:
                write_scores(output_file, [])
                written += 1
                continue

            if election_type == "random":
                metric_function = RANDOM_METRICS.get(metric_function, metric_function)

            metric_jobs.append((output_id, metric_function, variant, interpolation_type))

        tasks.extend(
            (
                profile_batch,
                n_cands,
                n_seats,
                election_type,
                tiebreak,
                tuple(metric_jobs),
            )
            for profile_batch in profile_batches
            if metric_jobs
        )

    return tasks, outputs, skipped, written


@click.command()
@click.option(
    "--settings-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=PROJECT_ROOT / "config/bt_profiles.txt",
    show_default=True,
)
@click.option("--n-seats", type=click.IntRange(min=1), default=3, show_default=True)
@click.option(
    "--election-type",
    type=click.Choice(
        [
            "borda",
            "plurality",
            "stv",
            "2-approval",
            "3-approval",
            "ranked-pairs",
            "random",
        ]
    ),
    default="random",
    show_default=True,
)
@click.option(
    "--tiebreak",
    type=click.Choice(["random", "lex"]),
    default="lex",
    show_default=True,
)
@click.option("--n-jobs", type=click.IntRange(min=1), default=1, show_default=True)
@click.option(
    "--profile-batch-size",
    type=click.IntRange(min=1),
    default=5,
    show_default=True,
)
def main(
    settings_file: Path,
    n_seats: int,
    election_type: AllowedRule,
    tiebreak: str,
    n_jobs: int,
    profile_batch_size: int,
) -> None:
    """Compute the four primary metrics across the folders in SETTINGS_FILE.

    Args:
        settings_file (Path): Text file listing profile directories, one per line.
        n_seats (int): Number of seats to elect.
        election_type (AllowedRule): Voting rule name.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
        n_jobs (int): Number of parallel workers.
        profile_batch_size (int): Maximum number of profiles per parallel task; must be positive.

    Raises:
        click.ClickException: The settings file lists no usable profile folders.
    """
    input_folders = load_profile_folders(settings_file)
    tasks, outputs, skipped, written = prepare_tasks(
        input_folders, n_seats, election_type, tiebreak, profile_batch_size
    )

    if skipped:
        click.echo(
            f"Skipping {skipped} completed folder/metric outputs. Move them manually to recompute."
        )

    if not outputs:
        click.echo("All outputs already exist.")

        return

    # Joblib does not retain the worker result type in its return annotation.
    results = cast(
        Iterator[BatchScores],
        Parallel(
            n_jobs=n_jobs,
            # Joblib accepts integer batch sizes despite its inferred string parameter type.
            batch_size=1,  # pyright: ignore[reportArgumentType]
            return_as="generator_unordered",
        )(delayed(run_profile_batch)(*task) for task in tasks),
    )

    with (
        tqdm(total=len(tasks), desc="Profile batches", unit="batch") as batch_progress,
        tqdm(
            total=len(outputs),
            initial=written,
            desc="Folder/metric outputs",
            unit="output",
        ) as output_progress,
    ):
        for batch_results in results:
            batch_progress.update()

            for output_id, batch_scores in batch_results:
                output = outputs[output_id]

                for index, score in batch_scores:
                    output["scores"][index] = score

                output["remaining_batches"] -= 1

                if output["remaining_batches"]:
                    continue

                # Every CSV slot has a score once all batches have finished.
                write_scores(output["output_file"], cast(list[float], output["scores"]))
                written += 1
                output_progress.set_postfix_str(output["label"], refresh=False)

                output_progress.update()

    click.echo(f"Wrote {written} output files.")


if __name__ == "__main__":
    main()
