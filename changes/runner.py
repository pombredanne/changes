#!/usr/bin/env python


def web():
    from gevent import wsgi
    from changes.config import create_app

    print "Listening on http://0.0.0.0:5000"

    app = create_app()
    wsgi.WSGIServer(('0.0.0.0', 5000), app).serve_forever()


def poller():
    import time
    from changes.backends.koality.backend import KoalityBackend
    from changes.backends.phabricator.poller import PhabricatorPoller
    from changes.config import create_app, db
    from changes.models import Build
    from phabricator import Phabricator

    app = create_app()
    app_context = app.app_context()
    app_context.push()

    from changes.models import (
        RemoteEntity, EntityType, Project, Repository
    )

    try:
        phabricator_project = RemoteEntity.query.filter_by(
            provider='phabricator',
            remote_id='Server',
            type=EntityType.project,
        )[0]
    except IndexError:
        repo = Repository(
            url='http://example.com/server',
        )
        db.session.add(repo)
        project = Project(
            repository=repo,
            name='Server',
        )
        db.session.add(project)
        phabricator_project = RemoteEntity(
            provider='phabricator',
            remote_id='Server',
            internal_id=project.id,
            type=EntityType.project,
        )
        db.session.add(phabricator_project)

    try:
        RemoteEntity.query.filter_by(
            provider='koality',
            remote_id='26',
            type=EntityType.project,
        )[0]
    except IndexError:
        project = phabricator_project.fetch_instance()
        koality_project = RemoteEntity(
            provider='koality',
            remote_id='26',
            internal_id=project.id,
            type=EntityType.project,
        )
        db.session.add(koality_project)

    db.session.commit()

    print "Polling for changes"
    client = Phabricator(host='https://tails.corp.dropbox.com/api/')

    backend = KoalityBackend(app=app)

    poller = PhabricatorPoller(client)
    poller._populate_project_cache()
    while True:
        for project, revision in poller.yield_revisions():
            change, created = poller.sync_revision(project, revision)
            for patch, created in poller.sync_diff_list(change):
                if created:
                    # fire off a build
                    build = Build(
                        repository=project.repository,
                        project=project,
                        change=change,
                        patch=patch,
                        label=patch.label,
                        message=patch.message,
                        parent_revision_sha=patch.parent_revision_sha,
                    )
                    db.session.add(build)
                    backend.create_build(build, project)
            db.session.commit()
        time.sleep(5)
