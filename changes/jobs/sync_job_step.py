from datetime import datetime
from flask import current_app
from sqlalchemy.orm import subqueryload_all
from sqlalchemy.sql import func

from changes.backends.base import UnrecoverableException
from changes.constants import Status, Result
from changes.config import db
from changes.db.utils import try_create
from changes.models import (
    ItemOption, JobPhase, JobStep, JobPlan, Plan, TestCase, ItemStat,
    FileCoverage, FailureReason
)
from changes.queue.task import tracked_task
from changes.utils.agg import safe_agg


def get_build_step(job_id):
    job_plan = JobPlan.query.options(
        subqueryload_all('plan.steps')
    ).filter(
        JobPlan.job_id == job_id,
    ).join(Plan).first()
    if not job_plan:
        raise UnrecoverableException('Missing job plan for job: %s' % (job_id,))

    plan = job_plan.plan
    try:
        step = plan.steps[0]
    except IndexError:
        raise UnrecoverableException('Missing steps for plan: %s' % (job_plan.plan.id))

    implementation = step.get_implementation()
    return plan, implementation


def sync_phase(phase):
    phase_steps = list(phase.steps)

    if phase.date_started is None:
        phase.date_started = safe_agg(
            min, (s.date_started for s in phase_steps), phase.date_started)
        db.session.add(phase)

    if all(s.status == Status.finished for s in phase_steps):
        phase.status = Status.finished
        phase.date_finished = safe_agg(
            max, (s.date_finished for s in phase_steps), phase.date_finished)

        if any(s.result is Result.failed for s in phase_steps):
            phase.result = Result.failed
        else:
            phase.result = safe_agg(
                max, (s.result for s in phase.steps), Result.unknown)

        db.session.add(phase)
    elif any(s.status != Status.finished for s in phase_steps):
        phase.status = Status.in_progress
        db.session.add(phase)

    if db.session.is_modified(phase):
        phase.date_modified = datetime.utcnow()
        db.session.commit()


def abort_step(task):
    step = JobStep.query.get(task.kwargs['step_id'])
    step.status = Status.finished
    step.result = Result.aborted
    db.session.add(step)
    db.session.commit()
    sync_phase(phase=step.phase)
    current_app.logger.exception('Unrecoverable exception syncing step %s', step.id)


def is_missing_tests(plan, step):
    query = ItemOption.query.filter(
        ItemOption.item_id == plan.id,
        ItemOption.name == 'build.expect-tests',
        ItemOption.value == '1',
    )
    if not db.session.query(query.exists()).scalar():
        return False

    # if this is not the final phase then ignore it
    # TODO(dcramer): there is probably a better way we can be explicit about
    # this?
    if db.session.query(JobPhase.query.filter(
        JobPhase.job_id == step.job_id,
        JobPhase.date_created > step.phase.date_created,
    ).exists()).scalar():
        return False

    has_tests = db.session.query(TestCase.query.filter(
        TestCase.step_id == step.id,
    ).exists()).scalar()

    return not has_tests


def has_test_failures(step):
    return db.session.query(TestCase.query.filter(
        TestCase.step_id == step.id,
        TestCase.result == Result.failed,
    ).exists()).scalar()


def record_coverage_stats(step):
    coverage_stats = db.session.query(
        func.sum(FileCoverage.lines_covered).label('lines_covered'),
        func.sum(FileCoverage.lines_uncovered).label('lines_uncovered'),
        func.sum(FileCoverage.diff_lines_covered).label('diff_lines_covered'),
        func.sum(FileCoverage.diff_lines_uncovered).label('diff_lines_uncovered'),
    ).filter(
        FileCoverage.step_id == step.id,
    ).group_by(
        FileCoverage.step_id,
    ).first()

    stat_list = (
        'lines_covered', 'lines_uncovered',
        'diff_lines_covered', 'diff_lines_uncovered',
    )
    for stat_name in stat_list:
        try_create(ItemStat, where={
            'item_id': step.id,
            'name': stat_name,
        }, defaults={
            'value': getattr(coverage_stats, stat_name, 0) or 0,
        })


@tracked_task(on_abort=abort_step, max_retries=100)
def sync_job_step(step_id):
    step = JobStep.query.get(step_id)
    if not step:
        return

    plan, implementation = get_build_step(step.job_id)

    # only synchronize if upstream hasn't suggested we're finished
    if step.status != Status.finished:
        implementation.update_step(step=step)

    if step.status != Status.finished:
        is_finished = False
    else:
        is_finished = sync_job_step.verify_all_children() == Status.finished

    if not is_finished:
        db.session.flush()
        if step.phase.status != Status.in_progress == step.status:
            sync_phase(phase=step.phase)
        raise sync_job_step.NotFinished

    missing_tests = is_missing_tests(plan, step)

    try_create(ItemStat, where={
        'item_id': step.id,
        'name': 'tests_missing',
    }, defaults={
        'value': int(missing_tests)
    })

    try:
        record_coverage_stats(step)
    except Exception:
        current_app.logger.exception('Failing recording coverage stats for step %s', step.id)

    if step.result == Result.passed and missing_tests:
        step.result = Result.failed
        db.session.add(step)

    if missing_tests:
        if step.result != Result.failed:
            step.result = Result.failed
            db.session.add(step)

        try_create(FailureReason, {
            'step_id': step.id,
            'job_id': step.job_id,
            'build_id': step.job.build_id,
            'project_id': step.project_id,
            'reason': 'missing_tests'
        })
        db.session.commit()

    db.session.flush()

    sync_phase(phase=step.phase)

    if has_test_failures(step):
        if step.result != Result.failed:
            step.result = Result.failed
            db.session.add(step)

        try_create(FailureReason, {
            'step_id': step.id,
            'job_id': step.job_id,
            'build_id': step.job.build_id,
            'project_id': step.project_id,
            'reason': 'test_failures'
        })
        db.session.commit()
