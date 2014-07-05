from datetime import datetime
from flask import current_app
from sqlalchemy.sql import func

from changes.config import db, queue
from changes.constants import Result, Status
from changes.db.utils import try_create
from changes.jobs.signals import fire_signal
from changes.models import Build, ItemStat, Job
from changes.utils.agg import safe_agg
from changes.queue.task import tracked_task


def aggregate_build_stat(build, name, func_=func.sum):
    value = db.session.query(
        func.coalesce(func_(ItemStat.value), 0),
    ).filter(
        ItemStat.item_id.in_(
            db.session.query(Job.id).filter(
                Job.build_id == build.id,
            )
        ),
        ItemStat.name == name,
    ).as_scalar()

    try_create(ItemStat, where={
        'item_id': build.id,
        'name': name,
    }, defaults={
        'value': value
    })


def abort_build(task):
    build = Build.query.get(task.kwargs['build_id'])
    build.status = Status.finished
    build.result = Result.aborted
    db.session.add(build)
    db.session.commit()
    current_app.logger.exception('Unrecoverable exception syncing build %s', build.id)


@tracked_task(on_abort=abort_build)
def sync_build(build_id):
    """
    Synchronizing the build happens continuously until all jobs have reported in
    as finished or have failed/aborted.

    This task is responsible for:
    - Checking in with jobs
    - Aborting/retrying them if they're beyond limits
    - Aggregating the results from jobs into the build itself
    """
    build = Build.query.get(build_id)
    if not build:
        return

    if build.status == Status.finished:
        return

    all_jobs = list(Job.query.filter(
        Job.build_id == build_id,
    ))

    is_finished = sync_build.verify_all_children() == Status.finished

    build.date_started = safe_agg(
        min, (j.date_started for j in all_jobs if j.date_started))

    if is_finished:
        build.date_finished = safe_agg(
            max, (j.date_finished for j in all_jobs if j.date_finished))
    else:
        build.date_finished = None

    if build.date_started and build.date_finished:
        build.duration = int((build.date_finished - build.date_started).total_seconds() * 1000)
    else:
        build.duration = None

    if any(j.result is Result.failed for j in all_jobs):
        build.result = Result.failed
    elif is_finished:
        build.result = safe_agg(
            max, (j.result for j in all_jobs), Result.unknown)
    else:
        build.result = Result.unknown

    if is_finished:
        build.status = Status.finished
    elif any(j.status is not Status.queued for j in all_jobs):
        build.status = Status.in_progress
    else:
        build.status = Status.queued

    if db.session.is_modified(build):
        build.date_modified = datetime.utcnow()
        db.session.add(build)
        db.session.commit()

    if not is_finished:
        raise sync_build.NotFinished

    try:
        aggregate_build_stat(build, 'test_count')
        aggregate_build_stat(build, 'test_duration')
        aggregate_build_stat(build, 'test_failures')
        aggregate_build_stat(build, 'test_rerun_count')
        aggregate_build_stat(build, 'tests_missing')
        aggregate_build_stat(build, 'lines_covered')
        aggregate_build_stat(build, 'lines_uncovered')
        aggregate_build_stat(build, 'diff_lines_covered')
        aggregate_build_stat(build, 'diff_lines_uncovered')
    except Exception:
        current_app.logger.exception('Failing recording aggregate stats for build %s', build.id)

    fire_signal.delay(
        signal='build.finished',
        kwargs={'build_id': build.id.hex},
    )

    queue.delay('update_project_stats', kwargs={
        'project_id': build.project_id.hex,
    }, countdown=1)
