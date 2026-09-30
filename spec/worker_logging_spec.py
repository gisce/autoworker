import logging
import os

import click
from redis import Redis
from rq import Queue, Worker
from rq.cli.cli import worker as worker_cli
from rq.job import Job
from rq.utils import utcnow

from autoworker import AutoWorker
from expects import contain, equal, expect
from mamba import after, before, description, it


with description('Worker logging'):
    with before.each:
        self.previous_env = os.environ.copy()
        os.environ['AUTOWORKER_REDIS_URL'] = 'redis://localhost:6379/0'
        self.autoworker = AutoWorker('create_reads', max_procs=1)

    with after.each:
        os.environ.clear()
        os.environ.update(self.previous_env)

    with it('keeps the queue and job ID without logging configuration'):
        parser = worker_cli.make_parser(click.Context(worker_cli))
        options, _, _ = parser.parse_args(self.autoworker.worker_command[2:])
        connection = Redis()
        config = {'minio_endpoint': 'private-endpoint',
                  'minio_secret_key': 'private-secret'}
        job = Job.create('oorq.tasks.execute',
                         args=(config, 'ecasa_comer', 43, 'res.users', 'read'),
                         connection=connection)
        messages = []

        class TestQueue(Queue):
            @classmethod
            def dequeue_any(cls, *args, **kwargs):
                return job, queue

        class CaptureHandler(logging.Handler):
            def emit(self, record):
                messages.append(record.getMessage())

        queue = TestQueue('create_reads', connection=connection)
        worker = Worker(
            [queue], connection=connection, queue_class=TestQueue,
            prepare_for_work=False,
            log_job_description=not options.get('disable_job_desc_logging', False),
        )
        worker.heartbeat = lambda: None
        worker.set_state = lambda state: None
        worker.procline = lambda title: None
        worker.get_redis_server_version = lambda: (7, 0, 0)
        worker.last_cleaned_at = utcnow()
        worker.log = logging.Logger('test.autoworker', level=logging.INFO)
        worker.log.addHandler(CaptureHandler())

        result, _ = worker.dequeue_job_and_maintain_ttl(None)

        output = '\n'.join(messages)
        expect(output).to(contain('create_reads:', job.id))
        for value in ('minio_', 'private-endpoint', 'private-secret'):
            expect(output).not_to(contain(value))
        expect(result.args[0]).to(equal(config))

    with it('disables descriptions when a custom worker class is configured'):
        os.environ['AUTOWORKER_WORKER_CLASS'] = 'custom.Worker'
        autoworker = AutoWorker('custom_queue', max_procs=1)
        command = autoworker.worker_command
        expect(command).to(contain('--disable-job-desc-logging'))
        expect(command[command.index('-w') + 1]).to(equal('custom.Worker'))
        expect(command[-1]).to(equal('custom_queue'))
