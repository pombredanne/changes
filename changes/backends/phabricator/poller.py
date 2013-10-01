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

# differential.query
"""{
  "0"  : {
    "id"           : "23788",
    "phid"         : "PHID-DREV-35ugwwyy63app3nyqymz",
    "title"        : "Adding new settings tabs",
    "uri"          : "https:\/\/tails.corp.dropbox.com\/D23788",
    "dateCreated"  : "1380343382",
    "dateModified" : "1380584810",
    "authorPHID"   : "PHID-USER-55q6ia6onuplhq5ioklt",
    "status"       : "0",
    "statusName"   : "Needs Review",
    "branch"       : "2account_settings_merged",
    "summary"      : "The settings diff.  Still need to finish ajax endpoints for most of the stuff.  Also the gating is around merged account rather than a seperate settings gandalf.  Hopefully I will work on this more this weekend.",
    "testPlan"     : "Try all the controls in paired and unpaired view",
    "lineCount"    : "2646",
    "diffs"        : [
      "78044",
      "78043",
      "77787"
    ],
    "commits"      : [],
    "reviewers"    : [
      "PHID-USER-pqsko37cjldrmpe4b27k"
    ],
    "ccs"          : [
      "PHID-MLST-kmlvtkgc4qzzhldqprk4",
      "PHID-MLST-abaf3dac5c78fbfcaec4"
    ],
    "hashes"       : [
      [
        "hgcm",
        "d0140e2204fdb80c4c28d1fa4aca53d380bd7160"
      ],
      [
        "hgcm",
        "24e587dffe888c0e719312023616803d9b93f328"
      ]
    ],
    "auxiliary"    : {
      "phabricator:depends-on"  : [],
      "dropbox:security-review" : false
    }
  },
  "1"  : {
    "id"           : "23766",
    "phid"         : "PHID-DREV-skfki3if2ltfc4rfklqp",
    "title"        : "Make a taskrunner task for get started backfill and make corresponding changes to the backfill script.",
    "uri"          : "https:\/\/tails.corp.dropbox.com\/D23766",
    "dateCreated"  : "1380320177",
    "dateModified" : "1380584431",
    "authorPHID"   : "PHID-USER-ev2ecay4iywhvdwhhx2g",
    "status"       : "3",
    "statusName"   : "Closed",
    "branch"       : null,
    "summary"      : "",
    "testPlan"     : "",
    "lineCount"    : "298",
    "diffs"        : [
      "78041",
      "77709"
    ],
    "commits"      : [
      "PHID-CMIT-qqf27nr3gw32geuy2i5j"
    ],
    "reviewers"    : [
      "PHID-USER-cbb6375d0d6df249978d"
    ],
    "ccs"          : [
      "PHID-USER-e32fvrmbx4stfr2epnbq",
      "PHID-MLST-s2nmmqjvzrcguyrzxso2",
      "PHID-MLST-3tntq6nrcymndxowp4ly",
      "PHID-MLST-abaf3dac5c78fbfcaec4"
    ],
    "hashes"       : [
      [
        "hgcm",
        "c0bb118ab1a13efd4d2064d161034f4315aaf24a"
      ]
    ],
    "auxiliary"    : {
      "phabricator:depends-on"  : [],
      "dropbox:security-review" : false
    }
  }
]"""


class PhabricatorPoller(object):
    def __init__(self, client, base_url='http://localhost:7777', *args,
                 **kwargs):
        # The default client uses ~/.arcrc
        self.client = client or Phabricator()
        super(PhabricatorPoller, self).__init__(*args, **kwargs)

    def yield_diffs(self):
        results = self.client.differential.query(
            arcanistProjects=PROJECT_MAP.keys(),
            limit=100,
        )

        for num in xrange(len(results)):
            yield results[num]

    def get_change_from_diff(self, diff):
        # look for existing change first
        matches = requests.get('/api/0/changes/', {
            'remote_id': diff['id'],
        })
        if not matches:
            return None

    def create_change_from_diff(self, diff):
        message = self.client.differential.getcommitmessage(
            revision_id=diff['id'])

        requests.post('/api/0/changes/', {
            'remote_id': diff['id'],
            'label': 'D{0}: {1}'.format(diff['id'], diff['title'])[:128],
            'message': message,
            'date_created': datetime.utcfromtimestamp(float(diff['dateCreated'])),
            'date_modified': datetime.utcfromtimestamp(float(diff['dateModified'])),
        })

    def sync_diffs(self):
        """
        Fetch a list of all diffs, and create any changes that are
        missing (via the API).
        """
        for diff in self.yield_diffs():
            change = self.get_change_from_diff(diff)
            if change:
                continue
            change = self.create_change_from_diff(diff)
