from changes.utils.imports import import_submodules

import_submodules(globals(), __name__, __path__)


class Registry(dict):
    def add(self, type, cls):
        self[type] = cls()

registry = Registry()
registry.add('test_failures', TestFailure)  # NOQA
registry.add('missing_tests', MissingTests)  # NOQA
registry.add('timeout', Timeout)  # NOQA
registry.add('missing_artifact', MissingArtifact)  # NOQA
