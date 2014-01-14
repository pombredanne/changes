import requests

from flask import current_app

from changes.config import db
from changes.models import ProjectOption
from changes.utils.http import build_uri

# echo PROJECT: $PROJECT
# echo REVISION: $REVISION

# credentials=$(cat /srv/green_build_password)
# result=$(curl --write-out %{http_code} --retry 3 --output curl.output -s -d "project=$PROJECT;id=$REVISION;build_url=$URL;build_server=jenkins" --user green_build:$credentials https://monitor.dropbox.com/cgi-bin/set_green_build.py)


def build_finished_handler(build, **kwargs):
    # TODO(dcramer): this is Dropbox specific, and should be moved out into a
    # separate project
    url = current_app.config.get('GREEN_BUILD_URL')
    if not url:
        return

    auth = current_app.config['GREEN_BUILD_AUTH']
    if not auth:
        return

    # we only want to identify stable revisions
    if build.patch_id or not build.revision_sha:
        return

    options = dict(
        db.session.query(
            ProjectOption.name, ProjectOption.value
        ).filter(
            ProjectOption.project_id == build.project_id,
            ProjectOption.name.in_([
                'green-build.notify', 'green-build.project',
            ])
        )
    )

    if options.get('green-build.notify') != '1':
        return

    project = options.get('green-build.project') or build.project.slug

    requests.post(url, auth=auth, data={
        'project': project,
        'id': build.revision_sha,
        'build_url': build_uri('/builds/{0}/'.format(build.id.hex)),
        'build_server': 'changes',
    })
