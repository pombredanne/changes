from __future__ import absolute_import, division, unicode_literals

from flask.ext.restful.reqparse import RequestParser

from changes.api.base import APIView
from changes.api.auth import requires_auth
from changes.db.utils import create_or_update
from changes.models import ItemOption, Plan


OPTION_DEFAULTS = {
    'build.expect-tests': '0',
}


class PlanOptionsAPIView(APIView):
    def get(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        options = dict(
            (o.name, o.value) for o in ItemOption.query.filter(
                ItemOption.item_id == plan.id,
            )
        )
        for key, value in OPTION_DEFAULTS.iteritems():
            options.setdefault(key, value)

        return self.respond(options)

    post_parser = RequestParser()
    post_parser.add_argument('build.expect-tests')

    @requires_auth
    def post(self, plan_id):
        plan = Plan.query.get(plan_id)
        if plan is None:
            return '', 404

        args = self.post_parser.parse_args()

        for name, value in args.iteritems():
            if value is None:
                continue

            create_or_update(ItemOption, where={
                'item_id': plan.id,
                'name': name,
            }, values={
                'value': value,
            })

        return '', 200
