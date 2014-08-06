import uuid

from cStringIO import StringIO

from changes.artifacts.xunit import XunitHandler
from changes.constants import Result
from changes.models import JobStep, TestResult
from changes.testutils import SAMPLE_XUNIT


def test_result_generation():
    jobstep = JobStep(
        id=uuid.uuid4(),
        project_id=uuid.uuid4(),
        job_id=uuid.uuid4(),
    )

    fp = StringIO(SAMPLE_XUNIT)

    handler = XunitHandler(jobstep)
    results = handler.get_tests(fp)

    assert len(results) == 2

    r1 = results[0]
    assert type(r1) == TestResult
    assert r1.step == jobstep
    assert r1.package is None
    assert r1.name == 'tests.test_report'
    assert r1.duration == 0.0
    assert r1.result == Result.failed
    assert r1.message == """tests/test_report.py:1: in <module>
>   import mock
E   ImportError: No module named mock"""
    r2 = results[1]
    assert type(r2) == TestResult
    assert r2.step == jobstep
    assert r2.package is None
    assert r2.name == 'tests.test_report.ParseTestResultsTest.test_simple'
    assert r2.duration == 1.65796279907
    assert r2.result == Result.passed
    assert r2.message == ''
    assert r2.reruns == 1
