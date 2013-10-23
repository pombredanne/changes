from __future__ import absolute_import, division, unicode_literals

from cStringIO import StringIO
from datetime import datetime
from flask import current_app as app, request
from sqlalchemy.orm import joinedload

from changes.api.base import APIView, param
from changes.api.validators.author import AuthorValidator
from changes.config import db
from changes.constants import Status
from changes.jobs.sync_build import sync_build
from changes.models import Project, Build, Repository, Patch, Change


class BuildIndexAPIView(APIView):
    def get_backend(self, app=app):
        # TODO this should be automatic via a project
        from changes.backends.koality.builder import KoalityBuilder
        return KoalityBuilder(
            app=app,
            base_url=app.config['KOALITY_URL'],
            api_key=app.config['KOALITY_API_KEY'],
        )

    @param('change_id', lambda x: Change.query.get(x), dest='change', required=False)
    def get(self, change=None):
        queryset = Build.query.options(
            joinedload(Build.project),
            joinedload(Build.author),
        ).order_by(Build.date_created.desc(), Build.date_started.desc())
        if change:
            queryset = queryset.filter_by(change=change)

        build_list = list(queryset)[:100]

        context = {
            'builds': build_list,
        }

        return self.respond(context)

    @param('sha')
    # TODO(dcramer): these params are getting messy, and in this case we've got
    # multiple input styles (GET vs POST) that can potentially squash each other
    @param('change', lambda x: Change.query.get(x), dest='change', required=False)
    @param('change_id', lambda x: Change.query.get(x), dest='change', required=False)
    @param('project', lambda x: Project.query.filter_by(slug=x).first(), dest='project', required=False)
    @param('author', AuthorValidator(), required=False)
    @param('patch[label]', required=False, dest='patch_label')
    @param('patch[url]', required=False, dest='patch_url')
    def post(self, sha, project=None, change=None, author=None,
             patch_label=None, patch_url=None, patch=None):

        assert change or project

        if request.form.get('patch'):
            raise ValueError('patch')

        patch_file = request.files.get('patch')
        patch_label = request.form.get('patch_label')
        patch_url = request.form.get('patch_url')

        if patch_file and not patch_label:
            raise ValueError('patch_label')

        if change:
            project = change.project
        repository = Repository.query.get(project.repository_id)

        if patch_file:
            fp = StringIO()
            for line in patch_file:
                fp.write(line)

            patch = Patch(
                change=change,
                repository=repository,
                project=project,
                parent_revision_sha=sha,
                label=patch_label,
                url=patch_url,
                diff=fp.getvalue(),
            )
            db.session.add(patch)
        else:
            patch = None

        if patch_label:
            label = patch_label
        else:
            label = sha[:12]

        build = Build(
            project=project,
            repository=repository,
            status=Status.queued,
            author=author,
            label=label,
            parent_revision_sha=sha,
            patch=patch,
        )
        if change:
            build.change = change
            change.date_modified = datetime.utcnow()
            db.session.add(change)

        db.session.add(build)

        backend = self.get_backend()
        backend.create_build(build)

        sync_build.delay(build_id=build.id)

        context = {
            'build': {
                'id': build.id.hex,
            },
        }

        return self.respond(context)

    def get_stream_channels(self, change_id=None):
        if not change_id:
            return ['builds:*']
        return ['builds:{0}:*'.format(change_id)]
