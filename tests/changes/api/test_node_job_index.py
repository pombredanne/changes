from changes.config import db
from changes.models import JobStep, JobPhase
from changes.testutils import APITestCase


class NodeJobIndexTest(APITestCase):
    def test_simple(self):
        project = self.create_project()
        node = self.create_node()
        build = self.create_build(project)
        job = self.create_job(build)
        phase = JobPhase(
            job=job,
            project=project,
            label='test',
        )
        db.session.add(phase)
        jobstep = JobStep(
            job=job,
            project=project,
            phase=phase,
            node=node,
            label='test',
        )
        db.session.add(jobstep)
        db.session.commit()

        path = '/api/0/nodes/{0}/jobs/'.format(node.id.hex)

        resp = self.client.get(path)
        assert resp.status_code == 200
        data = self.unserialize(resp)
        assert len(data) == 1
        assert data[0]['id'] == job.id.hex
