#!/usr/bin/env
"""
Phabricator Poller
"""
from datetime import datetime
from phabricator import Phabricator

from changes.config import db
from changes.models import RemoteEntity, Project, EntityType, Change

PROJECT_MAP = {
    'Server': 'server',
}


class PhabricatorPoller(object):
    def __init__(self, client, *args, **kwargs):
        # The default client uses ~/.arcrc
        self.client = client or Phabricator()
        super(PhabricatorPoller, self).__init__(*args, **kwargs)

    def _populate_project_cache(self):
        entity_map = dict(
            (e.internal_id, e.remote_id)
            for e in RemoteEntity.query.filter_by(
                provider='phabricator',
                type=EntityType.project,
            )
        )
        project_list = Project.query.filter(
            Project.id.in_(entity_map.keys()))
        self._arcproject_to_project_id = {}
        self._project_id_to_arcproject = {}
        self._project_cache = {}
        for project in project_list:
            self._arcproject_to_project_id[entity_map[project.id]] = project.id
            self._project_id_to_arcproject[project.id] = entity_map[project.id]
            self._project_cache[project.id] = project

    def _get_project_from_arcproject(self, name):
        if name not in self._arcproject_to_project:
            entity = RemoteEntity.query.filter_by(
                provider='phabricator',
                type=EntityType.project,
                remote_id=name,
            )[0]

            project = Project.query.get(entity.internal_id)
            self._arcproject_to_project[name] = project
            self._project_to_arcproject[project] = name
        return self._arcproject_to_project[name]

    def _yield_diffs(self):
        # the API response does not include the arcanist project, so we
        # must query each individually
        for project in self._project_cache.itervalues():
            arcproject = self._project_id_to_arcproject[project.id]
            results = self.client.differential.query(
                arcanistProjects=[arcproject],
                limit=100,
            )

            for num in xrange(len(results)):
                yield (project, results[str(num)])

    def _get_change_from_diff(self, project, diff):
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

    def _create_change_from_diff(self, project, diff):
        message = self.client.differential.getcommitmessage(
            revision_id=diff['id']).response

        change = Change(
            repository=project.repository,
            project=project,
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
        self._populate_project_cache()
        for project, diff in self._yield_diffs():
            self.sync_diff(project, diff)

    def sync_diff(self, project, diff):
        change = self._get_change_from_diff(project, diff)
        if not change:
            change = self._create_change_from_diff(project, diff)
        return change
