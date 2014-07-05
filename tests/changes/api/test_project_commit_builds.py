from uuid import uuid4

from changes.testutils import APITestCase


class ProjectCommitDetailsTest(APITestCase):
    def test_simple(self):
        fake_commit_id = uuid4()

        project = self.create_project()
        build = self.create_build(project)
        self.create_job(build)

        project2 = self.create_project()
        revision = self.create_revision(repository=project2.repository)
        source = self.create_source(project2, revision_sha=revision.sha)
        build = self.create_build(project2, source=source)

        path = '/api/0/projects/{0}/commits/{1}/builds/'.format(
            project.id.hex, fake_commit_id)

        resp = self.client.get(path)
        assert resp.status_code == 404

        path = '/api/0/projects/{0}/commits/{1}/builds/'.format(
            project2.id.hex, revision.sha)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == build.id.hex
