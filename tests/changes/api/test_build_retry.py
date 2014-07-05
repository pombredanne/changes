from changes.config import db
from changes.constants import Cause
from changes.models import Build, Job
from changes.testutils import APITestCase


class BuildRetryTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        build = self.create_build(project=project)
        job = self.create_job(build=build)
        plan = self.create_plan()
        plan.projects.append(project)
        db.session.commit()

        path = '/api/0/builds/{0}/retry/'.format(build.id.hex)
        resp = self.client.post(path, follow_redirects=True)

        assert resp.status_code == 200

        data = self.unserialize(resp)

        assert data['id']

        new_build = Build.query.get(data['id'])

        assert new_build.id != build.id
        assert new_build.project_id == project.id
        assert new_build.cause == Cause.retry
        assert new_build.author_id == build.author_id
        assert new_build.source_id == build.source_id
        assert new_build.label == build.label
        assert new_build.message == build.message
        assert new_build.target == build.target

        jobs = list(Job.query.filter(
            Job.build_id == new_build.id,
        ))

        assert len(jobs) == 1

        new_job = jobs[0]
        assert new_job.id != job.id
