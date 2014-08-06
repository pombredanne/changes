from __future__ import absolute_import, division, unicode_literals

from changes.api.base import APIView
from changes.constants import Status
from changes.config import db
from changes.models import JobStep


class JobStepAllocateAPIView(APIView):

    def post(self):
        to_allocate = JobStep.query.filter(
            JobStep.status == Status.pending_allocation,
        ).order_by(JobStep.date_created.desc()).first()

        # Should 204, but flask/werkzeug throws StopIteration (bug!) for tests
        if to_allocate is None:
            return self.respond([])

        to_allocate.status = Status.allocated
        db.session.add(to_allocate)
        db.session.commit()

        context = self.serialize(to_allocate)
        context['project'] = self.serialize(to_allocate.project)
        context['resources'] = {
            'cpus': 4,
            'mem': 8 * 1024,
        }

        return self.respond([context])
