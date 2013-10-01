from __future__ import absolute_import

import json
import httpretty
import mock
import os.path

from exam import fixture
from phabricator import Phabricator
from urlparse import parse_qs

from changes.config import db
from changes.models import Repository, Project, EntityType
from changes.backends.phabricator.poller import PhabricatorPoller
from changes.testutils import BackendTestCase


class BaseTestCase(BackendTestCase):
    provider = 'phabricator'
    poller_cls = PhabricatorPoller
    client_options = {
        'host': 'http://phabricator.example.com/api/',
        'username': 'test',
        'certificate': 'the cert',
    }
    client_session_key = 'session key'
    client_connection_id = 'connection id'

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

    def make_project_entity(self, project, remote_id):
        return self.make_entity(EntityType.project, project.id, remote_id)

    def get_poller(self):
        return self.poller_cls(self.phabricator)

    def load_request_params(self, request):
        result = json.loads(parse_qs(request.body)['params'][0])
        del result['__conduit__']
        return result

    @fixture
    def phabricator(self):
        client = Phabricator(**self.client_options)
        client.conduit = {
            'sessionKey': self.client_session_key,
            'connectionID': self.client_connection_id,
        }
        return client


class PhabricatorPollerTest(BaseTestCase):
    @httpretty.activate
    @mock.patch.object(PhabricatorPoller, 'sync_diff')
    def test_sync_diff_list(self, sync_diff):
        httpretty.register_uri(
            httpretty.POST, "http://phabricator.example.com/api/differential.query",
            body=self.load_fixture('fixtures/POST/differential.query.json'),
            streaming=True)

        self.make_project_entity(self.project, 'Server')

        poller = self.get_poller()
        poller.sync_diff_list()

        request = httpretty.last_request()
        assert self.load_request_params(request) == {
            'arcanistProjects': ['Server'],
            'limit': 100,
        }

        assert len(sync_diff.mock_calls) == 2

        _, args, kwargs = sync_diff.mock_calls[0]
        assert len(args) == 2
        assert not kwargs
        assert args[0] == self.project
        assert args[1]['id'] == '23788'

        _, args, kwargs = sync_diff.mock_calls[1]
        assert len(args) == 2
        assert not kwargs
        assert args[0] == self.project
        assert args[1]['id'] == '23766'

    @httpretty.activate
    def test_sync_diff(self):
        httpretty.register_uri(
            httpretty.POST, "http://phabricator.example.com/api/differential.getcommitmessage",
            body=self.load_fixture('fixtures/POST/differential.getcommitmessage.json'))

        diff = {
            'id': '23788',
            'phid': 'PHID-DREV-35ugwwyy63app3nyqymz',
            'title': 'Adding new settings tabs',
            'uri': 'https:\/\/tails.corp.dropbox.com\/D23788',
            'dateCreated': '1380343382',
            'dateModified': '1380584810',
            'authorPHID': 'PHID-USER-55q6ia6onuplhq5ioklt',
            'status': '0',
            'statusName': 'Needs Review',
            'branch': '2account_settings_merged',
            'summary': 'The settings diff.  Still need to finish ajax endpoints for most of the stuff.  Also the gating is around merged account rather than a seperate settings gandalf.  Hopefully I will work on this more this weekend.',
            'testPlan': 'Try all the controls in paired and unpaired view',
            'lineCount': '2646',
            'diffs': [
                '78044',
                '78043',
                '77787'
            ],
            'commits': [],
            'reviewers': [
                'PHID-USER-pqsko37cjldrmpe4b27k'
            ],
            'ccs': [
                'PHID-MLST-kmlvtkgc4qzzhldqprk4',
                'PHID-MLST-abaf3dac5c78fbfcaec4'
            ],
            'hashes': [
                [
                    'hgcm',
                    'd0140e2204fdb80c4c28d1fa4aca53d380bd7160'
                ],
                [
                    'hgcm',
                    '24e587dffe888c0e719312023616803d9b93f328'
                ]
            ],
            'auxiliary': {
                'phabricator:depends-on': [],
                'dropbox:security-review': False,
            }
        }
        message = (
            'Adding new settings tabs\n\nSummary: The settings diff. Still need'
            ' to finish ajax endpoints for most of the stuff. Also the gating'
            ' is around merged account rather than a seperate settings gandalf.'
            ' Hopefully I will work on this more this weekend.\n\n'
            'Test Plan: Try all the controls in paired and unpaired view\n\n'
            'Reviewers: jonv\n\n'
            'CC: web-reviews, Server-Reviews\n\n'
            'Differential Revision: https://tails.corp.dropbox.com/D23788'
        )

        poller = self.get_poller()

        change = poller.sync_diff(self.project, diff)

        request = httpretty.last_request()
        assert self.load_request_params(request) == {
            'revision_id': '23788',
        }

        assert change.label == 'D23788: Adding new settings tabs'
        assert change.message == message
