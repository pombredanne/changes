from uuid import uuid4

from datetime import datetime
from sqlalchemy import (
    Column, DateTime, ForeignKey, String, Text
)
from sqlalchemy.orm import relationship

from changes.config import db
from changes.db.types.guid import GUID


class Patch(db.Model):
    # TODO(dcramer): a patch is repo specific, not project specific, and the
    # label/message/etc aren't super useful
    __tablename__ = 'patch'

    id = Column(GUID, primary_key=True, default=uuid4)
    change_id = Column(GUID, ForeignKey('change.id', ondelete="CASCADE"))
    repository_id = Column(GUID, ForeignKey('repository.id', ondelete="CASCADE"), nullable=False)
    parent_revision_sha = Column(String(40))
    diff = Column(Text)
    date_created = Column(DateTime, default=datetime.utcnow)

    change = relationship('Change')
    repository = relationship('Repository')

    def __init__(self, **kwargs):
        super(Patch, self).__init__(**kwargs)
        if self.id is None:
            self.id = uuid4()
        if self.date_created is None:
            self.date_created = datetime.utcnow()
