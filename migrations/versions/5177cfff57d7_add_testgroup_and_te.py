"""Add TestGroup and TestSuite

Revision ID: 5177cfff57d7
Revises: 14491da59392
Create Date: 2013-11-04 12:42:37.249656

"""

from __future__ import absolute_import, print_function

# revision identifiers, used by Alembic.
revision = '5177cfff57d7'
down_revision = '14491da59392'

from alembic import op
from datetime import datetime
from hashlib import sha1
from sqlalchemy.sql import table
from uuid import uuid4
import sqlalchemy as sa


def upgrade():
    from changes.constants import Result

    testsuites_table = table(
        'testsuite',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name_sha', sa.String(length=40), nullable=False),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
    )
    testgroups_table = table(
        'testgroup',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('name_sha', sa.String(length=40), nullable=False),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('num_tests', sa.Integer(), nullable=True),
        sa.Column('num_failed', sa.Integer(), nullable=True),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('date_created', sa.DateTime(), nullable=True),
    )
    testgroups_m2m_table = table(
        'testgroup_test',
        sa.Column('group_id', sa.GUID(), nullable=False),
        sa.Column('test_id', sa.GUID(), nullable=False),
    )
    testcases_table = table(
        'test',
        sa.Column('id', sa.GUID(), nullable=False),
        sa.Column('build_id', sa.GUID(), nullable=False),
        sa.Column('project_id', sa.GUID(), nullable=False),
        sa.Column('package', sa.Text(), nullable=True),
        sa.Column('name', sa.Text(), nullable=True),
        sa.Column('group', sa.Text(), nullable=True),
        sa.Column('suite_id', sa.GUID(), nullable=True),
        sa.Column('duration', sa.Integer(), nullable=True),
        sa.Column('result', sa.Enum(), nullable=True),
    )

    connection = op.get_bind()

    ### commands auto generated by Alembic - please adjust! ###
    op.create_table('testsuite',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('build_id', sa.GUID(), nullable=False),
    sa.Column('project_id', sa.GUID(), nullable=False),
    sa.Column('name_sha', sa.String(length=40), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('build_id','name_sha', name='_suite_key')
    )
    op.create_table('testgroup',
    sa.Column('id', sa.GUID(), nullable=False),
    sa.Column('build_id', sa.GUID(), nullable=False),
    sa.Column('project_id', sa.GUID(), nullable=False),
    sa.Column('suite_id', sa.GUID(), nullable=True),
    sa.Column('parent_id', sa.GUID(), nullable=True),
    sa.Column('name_sha', sa.String(length=40), nullable=False),
    sa.Column('name', sa.Text(), nullable=True),
    sa.Column('duration', sa.Integer(), default=0, nullable=True),
    sa.Column('num_tests', sa.Integer(), default=0, nullable=True),
    sa.Column('num_failed', sa.Integer(), default=0, nullable=True),
    sa.Column('data', sa.JSONEncodedDict(), nullable=True),
    sa.Column('date_created', sa.DateTime(), nullable=True),
    sa.ForeignKeyConstraint(['build_id'], ['build.id'], ),
    sa.ForeignKeyConstraint(['parent_id'], ['testgroup.id'], ),
    sa.ForeignKeyConstraint(['project_id'], ['project.id'], ),
    sa.ForeignKeyConstraint(['suite_id'], ['testsuite.id'], ),
    sa.PrimaryKeyConstraint('id'),
    sa.UniqueConstraint('build_id','suite_id','name_sha', name='_group_key')
    )
    op.create_table('testgroup_test',
    sa.Column('group_id', sa.GUID(), nullable=False),
    sa.Column('test_id', sa.GUID(), nullable=False),
    sa.ForeignKeyConstraint(['group_id'], ['testgroup.id'], ),
    sa.ForeignKeyConstraint(['test_id'], ['test.id'], ),
    sa.PrimaryKeyConstraint('group_id', 'test_id')
    )
    op.add_column(u'test', sa.Column('suite_id', sa.GUID(), nullable=True))

    # perform data migrations
    for testcase in connection.execute(testcases_table.select()):
        # migrate group to suite
        print("Migrating TestCase %s" % (testcase.id,))

        suite_name = testcase.group or 'default'
        suite_sha = sha1(suite_name).hexdigest()

        result = connection.execute(testsuites_table.select().where(sa.and_(
            testsuites_table.c.build_id == testcase.build_id,
            testsuites_table.c.name_sha == suite_sha,
        )).limit(1)).fetchone()
        if not result:
            suite_id = uuid4()
            connection.execute(
                testsuites_table.insert().values(
                    id=suite_id,
                    build_id=testcase.build_id,
                    project_id=testcase.project_id,
                    name=suite_name,
                    name_sha=suite_sha,
                    date_created=datetime.utcnow(),
                )
            )
        else:
            suite_id = result[0]

        connection.execute(
            testcases_table.update().where(
                testcases_table.c.id == testcase.id,
            ).values({
                testcases_table.c.suite_id: suite_id,
            })
        )
        # add package as group
        group_name = testcase.package or testcase.name.rsplit('.', 1)[1]
        group_sha = sha1(group_name).hexdigest()

        result = connection.execute(testgroups_table.select().where(sa.and_(
            testgroups_table.c.build_id == testcase.build_id,
            testgroups_table.c.name_sha == group_sha,
        )).limit(1)).fetchone()

        if not result:
            group_id = uuid4()
            connection.execute(
                testgroups_table.insert().values(
                    id=group_id,
                    build_id=testcase.build_id,
                    project_id=testcase.project_id,
                    name=group_name,
                    name_sha=group_sha,
                    date_created=datetime.utcnow(),
                    duration=0,
                    num_tests=0,
                    num_failed=0,
                )
            )
        else:
            group_id = result[0]

        update_values = {
            testgroups_table.c.num_tests: testgroups_table.c.num_tests + 1,
            testgroups_table.c.duration: testgroups_table.c.duration + testcase.duration,
        }
        if testcase.result == Result.failed.value:
            update_values[testgroups_table.c.num_failed] = testgroups_table.c.num_failed + 1

        connection.execute(testgroups_m2m_table.insert().values({
            testgroups_m2m_table.c.group_id: group_id,
            testgroups_m2m_table.c.test_id: testcase.id,
        }))

        connection.execute(testgroups_table.update().where(
            testgroups_table.c.id == group_id,
        ).values(update_values))

    op.drop_column(u'test', u'group')
    op.drop_column(u'test', u'group_sha')
    ### end Alembic commands ###


def downgrade():
    ### commands auto generated by Alembic - please adjust! ###
    op.add_column(u'test', sa.Column(u'group_sha', sa.VARCHAR(length=40), nullable=True))
    op.add_column(u'test', sa.Column(u'group', sa.TEXT(), nullable=True))
    op.drop_column(u'test', 'suite_id')
    op.drop_table('testgroup_test')
    op.drop_table('testgroup')
    op.drop_table('testsuite')
    ### end Alembic commands ###
