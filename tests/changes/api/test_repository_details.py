from changes.models import Repository, RepositoryBackend
from changes.testutils import APITestCase


class RepositoryDetailsTest(APITestCase):
    def test_simple(self):
        repo = self.create_repo(
            url='https://example.com/bar',
        )

        path = '/api/0/repositories/{0}/'.format(repo.id)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['id'] == repo.id.hex
        assert data['url'] == repo.url


class UpdateRepositoryTest(APITestCase):
    def test_simple(self):
        repo = self.create_repo(
            url='https://example.com/bar',
        )

        path = '/api/0/repositories/{0}/'.format(repo.id)

        # ensure endpoint requires authentication
        resp = self.client.post(path, data={
            'url': 'https://example.com/foo'
        })
        assert resp.status_code == 401

        self.login_default()

        # ensure endpoint requires admin
        resp = self.client.post(path, data={
            'url': 'https://example.com/foo'
        })
        assert resp.status_code == 403

        self.login_default_admin()

        # test only setting url
        resp = self.client.post(path, data={
            'url': 'https://example.com/foo'
        })
        assert resp.status_code == 200

        data = self.unserialize(resp)
        assert data['url'] == 'https://example.com/foo'

        repo = Repository.query.get(repo.id)
        assert repo.url == 'https://example.com/foo'

        # test only setting backend
        resp = self.client.post(path, data={
            'backend': 'git'
        })
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert data['backend']['id'] == 'git'

        repo = Repository.query.get(repo.id)

        assert repo.backend == RepositoryBackend.git
