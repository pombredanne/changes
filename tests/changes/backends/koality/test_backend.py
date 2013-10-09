from __future__ import absolute_import

import cgi
import httpretty
import os

from cStringIO import StringIO
from datetime import datetime
from urlparse import parse_qs

from changes.backends.koality.backend import KoalityBackend
from changes.config import db
from changes.constants import Result, Status
from changes.models import (
    Repository, Project, Build, EntityType, Revision, Author,
    Phase, Step, Patch
)
from changes.testutils import BackendTestCase


SAMPLE_DIFF = """diff --git a/README.rst b/README.rst
index 2ef2938..ed80350 100644
--- a/README.rst
+++ b/README.rst
@@ -1,5 +1,5 @@
 Setup
------
+====="""


class KoalityBackendTestCase(BackendTestCase):
    backend_cls = KoalityBackend
    backend_options = {
        'base_url': 'https://koality.example.com',
        'api_key': 'a' * 12,
    }
    provider = 'koality'

    def setUp(self):
        self.repo = Repository(url='https://github.com/dropbox/changes.git')
        self.project = Project(repository=self.repo, name='test', slug='test')

        db.session.add(self.repo)
        db.session.add(self.project)

    def load_fixture(self, filename):
        filepath = os.path.join(
            os.path.dirname(__file__),
            filename,
        )
        with open(filepath, 'rb') as fp:
            return fp.read()

    def make_project_entity(self, project=None):
        return self.make_entity(EntityType.project, (project or self.project).id, 1)

    def load_request_params(self, request):
        return parse_qs(request.body)


class SyncBuildDetailsTest(KoalityBackendTestCase):
    # TODO(dcramer): we should break this up into testing individual methods
    # so edge cases can be more isolated
    @httpretty.activate
    def test_simple(self):
        httpretty.register_uri(
            httpretty.GET, 'https://koality.example.com/api/v/0/repositories/1/changes',
            body=self.load_fixture('fixtures/GET/changes.json'))
        httpretty.register_uri(
            httpretty.GET, 'https://koality.example.com/api/v/0/repositories/1/changes/1',
            body=self.load_fixture('fixtures/GET/changes__1.json'))
        httpretty.register_uri(
            httpretty.GET, 'https://koality.example.com/api/v/0/repositories/1/changes/1/stages',
            body=self.load_fixture('fixtures/GET/stages.json'))

        backend = self.get_backend()
        change = self.create_change(self.project)
        build = self.create_build(project=self.project, change=change)

        project_entity = self.make_project_entity()
        build_entity = self.make_entity(EntityType.build, build.id, 1)

        backend.sync_build_details(
            build=build,
            project=self.project,
            build_entity=build_entity,
            project_entity=project_entity,
        )

        assert build.label == 'Fixing visual regression with visuals.'
        assert build.parent_revision_sha == '7ebd1f2d750064652ef5bbff72452cc19e1731e0'
        assert build.status == Status.finished
        assert build.result == Result.failed
        assert build.date_started == datetime(2013, 9, 19, 22, 15, 22)
        assert build.date_finished == datetime(2013, 9, 19, 22, 15, 36)

        revision = Revision.query.filter_by(
            sha=build.parent_revision_sha,
            repository=build.repository,
        )[0]
        author = Author.query.get(revision.author_id)
        build = Build.query.get(build.id)

        assert revision.message == 'Fixing visual regression with visuals.'

        assert author.email == 'john@example.com'
        assert author.name == 'John Developer'

        phase_list = list(Phase.query.filter_by(
            build=build,
        ))

        phase_list.sort(key=lambda x: x.date_started)

        assert len(phase_list) == 3

        assert phase_list[0].project_id == build.project_id
        assert phase_list[0].repository_id == build.repository_id
        assert phase_list[0].label == 'Setup'
        assert phase_list[0].status == Status.finished
        assert phase_list[0].result == Result.passed
        assert phase_list[0].date_started == datetime(2013, 9, 19, 22, 15, 22)
        assert phase_list[0].date_finished == datetime(2013, 9, 19, 22, 15, 33)

        assert phase_list[1].project_id == build.project_id
        assert phase_list[1].repository_id == build.repository_id
        assert phase_list[1].label == 'Compile'
        assert phase_list[1].status == Status.finished
        assert phase_list[1].result == Result.passed
        assert phase_list[1].date_started == datetime(2013, 9, 19, 22, 15, 22, 500000)
        assert phase_list[1].date_finished == datetime(2013, 9, 19, 22, 15, 34)

        assert phase_list[2].project_id == build.project_id
        assert phase_list[2].repository_id == build.repository_id
        assert phase_list[2].label == 'Test'
        assert phase_list[2].status == Status.finished
        assert phase_list[2].result == Result.failed
        assert phase_list[2].date_started == datetime(2013, 9, 19, 22, 15, 25)
        assert phase_list[2].date_finished == datetime(2013, 9, 19, 22, 15, 36)

        step_list = list(Step.query.filter_by(
            build=build,
        ))

        step_list.sort(key=lambda x: (x.date_started, x.date_created))

        assert len(step_list) == 6

        assert step_list[0].project_id == build.project_id
        assert step_list[0].repository_id == build.repository_id
        assert step_list[0].phase_id == phase_list[0].id
        assert step_list[0].label == 'ci/setup'
        assert step_list[0].status == Status.finished
        assert step_list[0].result == Result.passed
        assert step_list[0].date_started == datetime(2013, 9, 19, 22, 15, 22)
        assert step_list[0].date_finished == datetime(2013, 9, 19, 22, 15, 33)

        assert step_list[1].project_id == build.project_id
        assert step_list[1].repository_id == build.repository_id
        assert step_list[1].phase_id == phase_list[0].id
        assert step_list[1].label == 'ci/setup'
        assert step_list[1].status == Status.finished
        assert step_list[1].result == Result.passed
        assert step_list[1].date_started == datetime(2013, 9, 19, 22, 15, 22)
        assert step_list[1].date_finished == datetime(2013, 9, 19, 22, 15, 33)

        assert step_list[2].project_id == build.project_id
        assert step_list[2].repository_id == build.repository_id
        assert step_list[2].phase_id == phase_list[1].id
        assert step_list[2].label == 'ci/compile'
        assert step_list[2].status == Status.finished
        assert step_list[2].result == Result.passed
        assert step_list[2].date_started == datetime(2013, 9, 19, 22, 15, 22, 500000)
        assert step_list[2].date_finished == datetime(2013, 9, 19, 22, 15, 33, 500000)

        assert step_list[3].project_id == build.project_id
        assert step_list[3].repository_id == build.repository_id
        assert step_list[3].phase_id == phase_list[1].id
        assert step_list[3].label == 'ci/compile'
        assert step_list[3].status == Status.finished
        assert step_list[3].result == Result.passed
        assert step_list[3].date_started == datetime(2013, 9, 19, 22, 15, 23)
        assert step_list[3].date_finished == datetime(2013, 9, 19, 22, 15, 34)

        assert step_list[4].project_id == build.project_id
        assert step_list[4].repository_id == build.repository_id
        assert step_list[4].phase_id == phase_list[2].id
        assert step_list[4].label == 'ci/test'
        assert step_list[4].status == Status.finished
        assert step_list[4].result == Result.passed
        assert step_list[4].date_started == datetime(2013, 9, 19, 22, 15, 25)
        assert step_list[4].date_finished == datetime(2013, 9, 19, 22, 15, 35)

        assert step_list[5].project_id == build.project_id
        assert step_list[5].repository_id == build.repository_id
        assert step_list[5].phase_id == phase_list[2].id
        assert step_list[5].label == 'ci/test'
        assert step_list[5].status == Status.finished
        assert step_list[5].result == Result.failed
        assert step_list[5].date_started == datetime(2013, 9, 19, 22, 15, 26)
        assert step_list[5].date_finished == datetime(2013, 9, 19, 22, 15, 36)


class CreateBuildTest(KoalityBackendTestCase):
    @httpretty.activate
    def test_simple(self):
        httpretty.register_uri(
            httpretty.POST, 'https://koality.example.com/api/v/0/repositories/1/changes',
            body=self.load_fixture('fixtures/POST/changes.json'))

        backend = self.get_backend()

        project_entity = self.make_project_entity()

        revision = '7ebd1f2d750064652ef5bbff72452cc19e1731e0'

        build = Build(
            repository=self.repo,
            project=self.project,
            parent_revision_sha=revision,
            label='D1345',
        )
        db.session.add(build)

        entity = backend.create_build(
            build=build,
            project=self.project,
            project_entity=project_entity,
        )
        assert entity.type == EntityType.build
        assert entity.internal_id == build.id
        assert entity.remote_id == '1501'
        assert entity.provider == 'koality'

        request = httpretty.last_request()
        assert self.load_request_params(request) == {
            'sha': [revision],
        }

    @httpretty.activate
    def test_patch(self):
        httpretty.register_uri(
            httpretty.POST, 'https://koality.example.com/api/v/0/repositories/1/changes',
            body=self.load_fixture('fixtures/POST/changes.json'))

        backend = self.get_backend()

        project_entity = self.make_project_entity()

        revision = '7ebd1f2d750064652ef5bbff72452cc19e1731e0'

        patch = Patch(
            repository=self.repo,
            project=self.project,
            parent_revision_sha=revision,
            label='D1345',
            diff=SAMPLE_DIFF,
        )
        db.session.add(patch)

        build = Build(
            repository=self.repo,
            project=self.project,
            parent_revision_sha=revision,
            patch=patch,
            label='D1345',
        )
        db.session.add(build)

        entity = backend.create_build(
            build=build,
            project=self.project,
            project_entity=project_entity,
        )
        assert entity.type == EntityType.build
        assert entity.internal_id == build.id
        assert entity.remote_id == '1501'
        assert entity.provider == 'koality'

        request = httpretty.last_request()
        ctype, pdict = cgi.parse_header(request.headers['Content-Type'])
        assert ctype == 'multipart/form-data'
        params = cgi.parse_multipart(StringIO(request.body), pdict)
        assert params['sha'] == [revision]
        assert params['patch'] == [SAMPLE_DIFF]
