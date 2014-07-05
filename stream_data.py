#!/usr/bin/env python

import random
import time

from datetime import datetime

from changes import mock
from changes.config import db, create_app
from changes.constants import Result, Status
from changes.db.utils import get_or_create
from changes.models import (
    Change, Job, JobStep, LogSource, TestResultManager, ProjectPlan,
    ItemStat
)
from changes.testutils.fixtures import Fixtures

app = create_app()
app_context = app.app_context()
app_context.push()

fixtures = Fixtures()


def create_new_change(project, **kwargs):
    return mock.change(project=project, **kwargs)


def create_new_entry(project):
    new_change = (random.randint(0, 2) == 5)
    if not new_change:
        try:
            change = Change.query.all()[0]
        except IndexError:
            new_change = True

    if new_change:
        author = mock.author()
        revision = mock.revision(project.repository, author)
        change = create_new_change(
            project=project,
            author=author,
            message=revision.message,
        )
    else:
        change.date_modified = datetime.utcnow()
        db.session.add(change)
        revision = mock.revision(project.repository, change.author)

    if random.randint(0, 1) == 1:
        patch = mock.patch(project)
    else:
        patch = None
    source = mock.source(
        project.repository, revision_sha=revision.sha, patch=patch)

    date_started = datetime.utcnow()

    build = mock.build(
        author=change.author,
        project=project,
        source=source,
        message=change.message,
        result=Result.failed if random.randint(0, 3) == 1 else Result.unknown,
        status=Status.in_progress,
        date_started=date_started,
    )

    build_task = fixtures.create_task(
        task_id=build.id,
        task_name='sync_build',
        data={'kwargs': {'build_id': build.id.hex}},
    )

    db.session.add(ItemStat(item_id=build.id, name='lines_covered', value='5'))
    db.session.add(ItemStat(item_id=build.id, name='lines_uncovered', value='5'))
    db.session.add(ItemStat(item_id=build.id, name='diff_lines_covered', value='5'))
    db.session.add(ItemStat(item_id=build.id, name='diff_lines_uncovered', value='5'))

    db.session.commit()

    for x in xrange(0, random.randint(1, 3)):
        job = mock.job(
            build=build,
            change=change,
            status=Status.in_progress,
            result=build.result,
        )
        fixtures.create_task(
            task_id=job.id.hex,
            parent_id=build_task.task_id,
            task_name='sync_job',
            data={'kwargs': {'job_id': job.id.hex}},
        )

        db.session.commit()
        if patch:
            mock.file_coverage(project, job, patch)

        for step in JobStep.query.filter(JobStep.job == job):
            logsource = LogSource(
                job=job,
                project=job.project,
                step=step,
                name=step.label,
            )
            db.session.add(logsource)
            db.session.commit()

            offset = 0
            for x in xrange(30):
                lc = mock.logchunk(source=logsource, offset=offset)
                db.session.commit()
                offset += lc.size

    return build


def update_existing_entry(project):
    try:
        job = Job.query.filter(
            Job.status == Status.in_progress,
        )[0]
    except IndexError:
        return create_new_entry(project)

    job.date_modified = datetime.utcnow()
    job.status = Status.finished
    job.result = Result.failed if random.randint(0, 3) == 1 else Result.passed
    job.date_finished = datetime.utcnow()
    db.session.add(job)
    db.session.commit()

    jobstep = JobStep.query.filter(JobStep.job == job).first()
    if jobstep:
        test_results = []
        for _ in xrange(10):
            if job.result == Result.failed:
                result = Result.failed if random.randint(0, 3) == 1 else Result.passed
            else:
                result = Result.passed
            test_results.append(mock.test_result(jobstep, result=result))
        try:
            TestResultManager(jobstep).save(test_results)
        except Exception:
            db.session.rollback()

    if job.status == Status.finished:
        job.build.status = job.status
        if job.build.result != Result.failed:
            job.build.result = job.result
        job.build.date_finished = job.date_finished
        job.build.date_modified = job.date_finished
        db.session.add(job.build)

    return job


def gen(project):
    if random.randint(0, 5) == 1:
        build = create_new_entry(project)
    else:
        build = update_existing_entry(project)

    db.session.commit()

    return build


def loop():
    repository = mock.repository()
    project = mock.project(repository)
    plan = mock.plan()
    get_or_create(ProjectPlan, where={
        'plan': plan,
        'project': project,
    })

    while True:
        build = gen(project)
        print 'Pushed build {0} on {1}'.format(build.id, project.slug)
        time.sleep(0.1)


if __name__ == '__main__':
    loop()
