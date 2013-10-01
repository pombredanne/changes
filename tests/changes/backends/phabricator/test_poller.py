from __future__ import absolute_import

import mock
import os

from datetime import datetime
from exam import fixture
from phabricator import Phabricator

from changes.config import db
from changes.constants import Result, Status
from changes.models import (
    Repository, Project, Build, EntityType, Revision, Author,
    Phase, Step, Patch
)
from changes.backends.phabricator.poller import PhabricatorPoller
from changes.testutils import BackendTestCase
from changes.testutils.http import MockedHTTPConnection


class BaseTestCase(BackendTestCase):
    poller_cls = PhabricatorPoller
    client_options = {
        'host': 'http://phabricator.example.com',
        'username': 'test',
        'certificate': 'the cert',
    }
    client_session_key = 'session key'
    client_connection_id = 'connection id'

    def setUp(self):
        from httplib import HTTPConnection
        self.mock_request = mock.Mock(
            spec=HTTPConnection,
            side_effect=MockedHTTPConnection(
                self.client_options['host'],
                os.path.join(os.path.dirname(__file__), 'fixtures')),
        )

        self.patcher = mock.patch(
            'httplib.HTTPConnection',
            side_effect=self.mock_request,
        )
        self.patcher.start()
        self.addCleanup(self.patcher.stop)

        self.repo = Repository(url='https://github.com/dropbox/changes.git')
        self.project = Project(repository=self.repo, name='test', slug='test')

        db.session.add(self.repo)
        db.session.add(self.project)

    def make_project_entity(self, project=None):
        return self.make_entity(EntityType.project, (project or self.project).id, 1)

    def get_poller(self):
        return self.poller_cls(self.phabricator)

    @fixture
    def phabricator(self):
        client = Phabricator(**self.client_options)
        client.conduit = {
            'sessionKey': self.client_session_key,
            'connectionID': self.client_connection_id,
        }
        return client


class PhabricatorPollerTest(BaseTestCase):
    @mock.patch.object(PhabricatorPoller, 'sync_diff')
    def test_sync_diff_list(self, sync_diff):
        poller = self.get_poller()
        poller.sync_diff_list()

        assert len(sync_diff.mock_calls) == 2

        _, args, kwargs = sync_diff.mock_calls[0]
        assert len(args) == 1
        assert not kwargs
        assert args[0]['id'] == '23788'

        _, args, kwargs = sync_diff.mock_calls[1]
        assert len(args) == 1
        assert not kwargs
        assert args[0]['id'] == '23766'
