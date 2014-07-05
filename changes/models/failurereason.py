from __future__ import absolute_import, division

from uuid import uuid4

from datetime import datetime
from sqlalchemy import Column, DateTime, ForeignKey, String
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Index, UniqueConstraint

from changes.config import db
from changes.db.types.guid import GUID


class FailureReason(db.Model):
    __tablename__ = 'failurereason'
    __table_args__ = (
        Index('idx_failurereason_job_id', 'job_id'),
        Index('idx_failurereason_build_id', 'build_id'),
        Index('idx_failurereason_project_id', 'project_id'),
        UniqueConstraint('step_id', 'reason', name='unq_failurereason_key'),
    )

    id = Column(GUID, nullable=False, primary_key=True, default=uuid4)
    step_id = Column(GUID, ForeignKey('jobstep.id', ondelete="CASCADE"), nullable=False)
    job_id = Column(GUID, ForeignKey('job.id', ondelete="CASCADE"), nullable=False)
    build_id = Column(GUID, ForeignKey('build.id', ondelete="CASCADE"), nullable=False)
    project_id = Column(GUID, ForeignKey('project.id', ondelete="CASCADE"), nullable=False)
    reason = Column(String(32), nullable=False)
    date_created = Column(DateTime, default=datetime.utcnow, server_default='now()', nullable=False)

    step = relationship('JobStep')
    job = relationship('Job')
    build = relationship('Build')
    project = relationship('Project')

    def __init__(self, **kwargs):
        super(FailureReason, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
