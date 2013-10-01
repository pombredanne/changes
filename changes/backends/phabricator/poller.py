#!/usr/bin/env
"""
Phabricator Poller
"""
from datetime import datetime
from phabricator import Phabricator

from changes.config import db
from changes.models import RemoteEntity, EntityType, Change

PROJECT_MAP = {
    'Server': 'server',
}


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
        try:
            entity = RemoteEntity.query.filter_by(
                provider='phabricator',
                type=EntityType.change,
                remote_id=diff['id'],
            )[0]
        except IndexError:
            return

        change = Change.query.get(entity.internal_id)
        return change

    def _create_change_from_diff(self, diff):
        message = self.client.differential.getcommitmessage(
            revision_id=diff['id']).response

        change = Change(
            label='D{0}: {1}'.format(diff['id'], diff['title'])[:128],
            message=message,
            date_created=datetime.utcfromtimestamp(float(diff['dateCreated'])),
            date_modified=datetime.utcfromtimestamp(float(diff['dateModified'])),
        )
        db.session.add(change)
        return change

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
        return change
