"""Collect the four primary metrics for two-bloc BT profiles listed in a settings file."""

import ast
import contextlib
import json
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass
from itertools import batched
from pathlib import Path
from types import FunctionType
from typing import NamedTuple, cast

import click
from joblib import Parallel, delayed
from tqdm.auto import tqdm
from votekit import RankProfile

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from pipelines.bradley_terry._metrics import IIAMetric, MetricSpec, UMMetric, configure_metric
from voting_metrics_main_code.constants import AllowedRule
from voting_metrics_main_code.replication import ROOT, new_data_file, seed_task
from voting_metrics_main_code.voting_rules import build_voting_rule

PRIMARY_METRICS: tuple[MetricSpec, ...] = (
    UMMetric("sigma_UM", "worst_case", "asin"),
    UMMetric("sigma_UM_winner_set", "worst_case", "asin"),
    IIAMetric("sigma_IIA", "average"),
    IIAMetric("sigma_IIA_winner_set", "average"),
)


class MetricOutput(NamedTuple):
    spec: MetricSpec
    path: Path


class MetricJob(NamedTuple):
    output_id: int
    spec: MetricSpec


class ProfileBatchTask(NamedTuple):
    profiles: tuple[tuple[int, Path], ...]
    n_cands: int
    n_seats: int
    election_type: AllowedRule
    tiebreak: str
    metrics: tuple[MetricJob, ...]


class OutputBatchScores(NamedTuple):
    output_id: int
    scores: tuple[tuple[int, float], ...]


@dataclass
class OutputProgress:
    """Scores retain CSV order while parallel batches complete out of order."""

    output_file: Path
    scores: list[float | None]
    remaining_batches: int
    label: str


@dataclass
class CollectionPlan:
    tasks: list[ProfileBatchTask]
    outputs: dict[int, OutputProgress]
    skipped: int


def build_output_jobs(
    input_folder: str | Path,
    n_seats: int,
    election_type: AllowedRule,
    tiebreak: str,
    *,
    output_root: Path,
) -> tuple[int, list[MetricOutput]]:
    """Build metric jobs and output paths from a two-bloc profile directory name.

    Args:
        input_folder (str | Path): Two-bloc profile directory with encoded candidate and bloc
            parameters.
        n_seats (int): Number of seats to elect.
        election_type (AllowedRule): Voting rule name.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
        output_root (Path): Run root containing stats, plots, and tables.

    Returns:
        tuple[int, list[MetricOutput]]: Total candidate count and
            jobs containing a metric specification and output path.

    Raises:
        ValueError: Encoded candidate counts or bloc parameters cannot be parsed or unpacked.
        IndexError: The directory name lacks a required parameter segment.
        SyntaxError: An encoded alpha or cohesion tuple is not a valid Python literal.
    """
    profile_folder = Path(input_folder).resolve()
    base_parts = profile_folder.name.split("__")
    cand_parts = profile_folder.parent.stem.split("_")

    b_proportion = float(base_parts[0].split("_")[-1])
    aa_alpha, ab_alpha, ba_alpha, bb_alpha = ast.literal_eval(base_parts[1].split("_")[-1])
    a_cohesion, b_cohesion = ast.literal_eval(base_parts[2].split("_")[-1])
    n_a_cands, n_b_cands = map(int, cand_parts)
    n_cands = n_a_cands + n_b_cands
    stats_dir = output_root / "stats" / "bt_2_bloc_profile_stats" / f"{n_seats}_seats"

    jobs = []

    for spec in PRIMARY_METRICS:
        metric = spec.name
        interpolation_type = spec.interpolation if isinstance(spec, UMMetric) else "None"
        basename = (
            f"METRIC_{metric}"
            f"__VARIANT_{spec.variant}"
            f"__INTERP_{interpolation_type}"
            f"__NCANDS_({n_a_cands:02d}_{n_b_cands:02d})"
            f"__SEATS_{n_seats}"
            f"__BPROP_{b_proportion:0.1f}"
            f"__ALPHA_({aa_alpha:0.2f},{ab_alpha:0.2f},{ba_alpha:0.2f},{bb_alpha:0.2f})"
            f"__COHESION_({a_cohesion:0.2f},{b_cohesion:0.2f})"
            f"__TYPE_{election_type}"
            f"__TIEBREAK_{tiebreak}.json"
        )
        output_file = stats_dir / metric / f"{n_cands:02d}" / election_type / basename

        jobs.append(MetricOutput(spec=spec, path=output_file))

    return n_cands, jobs


def run_profile_batch(task: ProfileBatchTask, *, seed: int = 0) -> tuple[OutputBatchScores, ...]:
    """Score profiles with independent metric seeds, retaining their original CSV indices.

    Task seeds depend on experiment settings and profile identity, not output IDs, worker count,
    or scheduling. The result groups indexed scores by output ID for ordered publication.

    Args:
        task (ProfileBatchTask): Indexed CSV paths, election settings, and metric jobs for one
            batch.
        seed (int, optional): Base seed for independent profile and metric streams. Defaults to 0.

    Returns:
        tuple[OutputBatchScores, ...]: Indexed profile scores grouped by output ID.

    Raises:
        FileNotFoundError: A profile CSV does not exist.
        ValueError: A voting rule or metric rejects the profile or election settings.
    """
    with contextlib.redirect_stdout(None):
        voting_rule = build_voting_rule(task.n_cands, task.election_type, tiebreak=task.tiebreak)
        metrics = [
            (
                job.output_id,
                configure_metric(
                    job.spec, task.n_seats, random_rule=task.election_type == "random"
                ),
            )
            for job in task.metrics
        ]
        scores: dict[int, list[tuple[int, float]]] = {output_id: [] for output_id, _ in metrics}

        for index, path in task.profiles:
            profile = RankProfile.from_csv(path)

            for output_id, metric in metrics:
                seed_task(
                    path.parent.parent.name,
                    path.parent.name,
                    path.name,
                    task.election_type,
                    task.tiebreak,
                    task.n_seats,
                    cast(FunctionType, metric.func).__name__,
                    metric.keywords,
                    seed=seed,
                )
                scores[output_id].append((index, metric(profile, voting_rule)))

    return tuple(
        OutputBatchScores(output_id, tuple(values)) for output_id, values in scores.items()
    )


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
        (Path(folder) if Path(folder).is_absolute() else ROOT / folder).resolve()
        for folder in input_folders
        if folder and not folder.startswith("#")
    ]

    if not input_folders:
        raise click.ClickException("The settings file contains no profile folders.")

    for folder in input_folders:
        if not folder.is_dir() or not any(folder.glob("*.csv")):
            raise click.ClickException(f"Missing or empty profile folder: {folder}")

    return input_folders


def plan_collection(
    input_folders: Sequence[Path],
    n_seats: int,
    election_type: AllowedRule,
    tiebreak: str,
    profile_batch_size: int,
    *,
    output_root: Path,
) -> CollectionPlan:
    """Inspect inputs and plan pending batches without writing results.

    Existing outputs are skipped. Empty folders retain an empty output to publish during execution.
    Profile indices follow sorted CSV paths, regardless of batching or resume order.

    Args:
        input_folders (Sequence[Path]): Profile directories to inspect in preparation order.
        n_seats (int): Number of seats to elect.
        election_type (AllowedRule): Voting rule to evaluate.
        tiebreak (str): Tie-breaking token used in election settings and result filenames.
        profile_batch_size (int): Maximum number of profiles per task; must be positive.
        output_root (Path): Run root containing the statistics tree.

    Returns:
        CollectionPlan: Pending tasks, output progress, and the count of existing results skipped.

    Raises:
        ValueError: Batch size is nonpositive or encoded profile parameters cannot be parsed.
        IndexError: A profile directory name lacks a required parameter segment.
        SyntaxError: An encoded alpha or cohesion tuple is not a valid Python literal.
    """
    if profile_batch_size < 1:
        raise ValueError("profile_batch_size must be positive")

    tasks = []
    outputs: dict[int, OutputProgress] = {}
    skipped = 0

    for folder in input_folders:
        n_cands, folder_jobs = build_output_jobs(
            folder, n_seats, election_type, tiebreak, output_root=output_root
        )
        profile_files = sorted(folder.resolve().glob("*.csv"))
        profile_batches = list(batched(enumerate(profile_files), profile_batch_size))
        metric_jobs = []

        for job in folder_jobs:
            if job.path.exists() or job.path.is_symlink():
                skipped += 1
                continue

            output_id = len(outputs)
            outputs[output_id] = OutputProgress(
                output_file=job.path,
                scores=[None] * len(profile_files),
                remaining_batches=len(profile_batches),
                label=f"{job.path.parents[2].name}: {folder.name}",
            )
            metric_jobs.append(MetricJob(output_id=output_id, spec=job.spec))

        if metric_jobs:
            tasks.extend(
                ProfileBatchTask(
                    profiles=batch,
                    n_cands=n_cands,
                    n_seats=n_seats,
                    election_type=election_type,
                    tiebreak=tiebreak,
                    metrics=tuple(metric_jobs),
                )
                for batch in profile_batches
            )

    return CollectionPlan(tasks=tasks, outputs=outputs, skipped=skipped)


def publish_completed_scores(output: OutputProgress) -> None:
    """Publish only after every batch and every CSV slot has been filled.

    Args:
        output (OutputProgress): Destination and ordered scores for one metric output.

    Raises:
        ValueError: Batches remain unfinished or a profile score is missing.
        FileExistsError: A result already exists at the destination.
        OSError: The completed scores cannot be written or published.
    """
    if output.remaining_batches or any(score is None for score in output.scores):
        raise ValueError(f"Incomplete scores for {output.output_file}")

    write_scores(output.output_file, [score for score in output.scores if score is not None])


def execute_collection(plan: CollectionPlan, *, n_jobs: int, seed: int) -> int:
    """Execute batches and publish each complete output in original profile order.

    Args:
        plan (CollectionPlan): Pending tasks and output progress, updated as batches complete.
        n_jobs (int): Number of parallel workers.
        seed (int): Base seed for independent profile and metric streams.

    Returns:
        int: Number of result files published, including outputs for empty profile folders.

    Raises:
        FileExistsError: A result appears at a destination before publication.
        ValueError: A profile, election setting, or completed batch result is invalid.
        OSError: An input cannot be read or an output cannot be written or published.
    """
    written = 0
    for output in plan.outputs.values():
        if not output.remaining_batches:
            publish_completed_scores(output)
            written += 1

    # Joblib does not retain the worker result type in its return annotation.
    results = cast(
        Iterator[tuple[OutputBatchScores, ...]],
        Parallel(n_jobs=n_jobs, batch_size=1, return_as="generator_unordered")(
            delayed(run_profile_batch)(task, seed=seed) for task in plan.tasks
        ),
    )
    with (
        tqdm(total=len(plan.tasks), desc="Profile batches", unit="batch") as batch_progress,
        tqdm(
            total=len(plan.outputs), initial=written, desc="Folder/metric outputs", unit="output"
        ) as output_progress,
    ):
        for batch_results in results:
            batch_progress.update()

            for result in batch_results:
                output = plan.outputs[result.output_id]
                for index, score in result.scores:
                    output.scores[index] = score

                output.remaining_batches -= 1
                if output.remaining_batches:
                    continue

                publish_completed_scores(output)
                written += 1
                output_progress.set_postfix_str(output.label, refresh=False)
                output_progress.update()

    return written


@click.command()
@click.option(
    "--settings-file",
    type=click.Path(path_type=Path, exists=True, dir_okay=False),
    default=ROOT / "code/config/bt_profiles.txt",
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
@click.option(
    "--output-dir",
    "output_root",
    type=click.Path(path_type=Path),
    default=ROOT,
    show_default=True,
    help="Run root containing stats, plots, and tables",
)
@click.option(
    "--seed",
    "seed",
    type=int,
    default=0,
    show_default=True,
    help="Base seed for independent task streams",
)
def main(
    settings_file: Path,
    n_seats: int,
    election_type: AllowedRule,
    tiebreak: str,
    n_jobs: int,
    profile_batch_size: int,
    *,
    output_root: Path = ROOT,
    seed: int = 0,
) -> None:
    """Compute the four primary metrics across the folders in SETTINGS_FILE.

    Args:
        settings_file (Path): Text file listing profile directories, one per line.
        n_seats (int): Number of seats to elect.
        election_type (AllowedRule): Voting rule name.
        tiebreak (str): Tiebreak rule token used in the statistics filenames.
        n_jobs (int): Number of parallel workers.
        profile_batch_size (int): Maximum number of profiles per parallel task; must be positive.
        output_root (Path, optional): Run root containing stats, plots, and tables. Defaults to
            ROOT.
        seed (int, optional): Base seed for independent task streams. Defaults to 0.

    Raises:
        click.ClickException: The settings file lists no usable profile folders.
    """
    output_root = output_root.resolve()
    if n_jobs < 1:
        raise ValueError("n_jobs must be positive")

    input_folders = load_profile_folders(settings_file)
    plan = plan_collection(
        input_folders, n_seats, election_type, tiebreak, profile_batch_size, output_root=output_root
    )

    if plan.skipped:
        click.echo(
            f"Skipping {plan.skipped} completed folder/metric outputs. Move them manually to recompute."
        )

    if not plan.outputs:
        click.echo("All outputs already exist.")
        return

    written = execute_collection(plan, n_jobs=n_jobs, seed=seed)
    click.echo(f"Wrote {written} output files.")


if __name__ == "__main__":
    main()
