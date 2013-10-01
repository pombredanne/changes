#!/usr/bin/env
"""
Phabricator Poller
"""
import requests

from datetime import datetime
from phabricator import Phabricator

PROJECT_MAP = {
    'Server': 'server',
}

# differential.getcommitmessage
'''"Adding new settings tabs Summary: The settings diff. Still need to finish ajax endpoints for most of the stuff. Also the gating is around merged account rather than a seperate settings gandalf. Hopefully I will work on this more this weekend. Test Plan: Try all the controls in paired and unpaired view Reviewers: jonv CC: web-reviews, Server-Reviews Differential Revision: https://tails.corp.dropbox.com/D23788"'''


class PhabricatorPoller(object):
    def __init__(self, client, *args, **kwargs):
        # The default client uses ~/.arcrc
        self.client = client or Phabricator()
        super(PhabricatorPoller, self).__init__(*args, **kwargs)

    def _yield_diffs(self):
        results = self.client.differential.query(
            arcanistProjects=PROJECT_MAP.keys(),
            limit=100,
        )

        for num in xrange(len(results)):
            yield results[str(num)]

    def _get_change_from_diff(self, diff):
        # look for existing change first
        matches = requests.get('/api/0/changes/', {
            'remote_id': diff['id'],
        })
        if not matches:
            return None

    def _create_change_from_diff(self, diff):
        message = self.client.differential.getcommitmessage(
            revision_id=diff['id'])

        requests.post('/api/0/changes/', {
            'remote_id': diff['id'],
            'label': 'D{0}: {1}'.format(diff['id'], diff['title'])[:128],
            'message': message,
            'date_created': datetime.utcfromtimestamp(float(diff['dateCreated'])),
            'date_modified': datetime.utcfromtimestamp(float(diff['dateModified'])),
        })

    def sync_diff_list(self):
        """
        Fetch a list of all diffs, and create any changes that are
        missing (via the API).
        """
        for diff in self._yield_diffs():
            self.sync_diff(diff)

    def sync_diff(self, diff):
        change = self._get_change_from_diff(diff)
        if not change:
            change = self._create_change_from_diff(diff)
