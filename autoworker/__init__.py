# coding: utf-8
from __future__ import unicode_literals
import os
import multiprocessing as mp
from uuid import uuid4
import subprocess
import sys

from redis import Redis
from rq.defaults import DEFAULT_RESULT_TTL
from rq.contrib.legacy import cleanup_ghosts
from rq.queue import Queue
from rq.worker import Worker, WorkerStatus
from rq.utils import import_attribute
from osconf import config_from_environment


#MAX_PROCS = max(mp.cpu_count() - os.getloadavg()[0], 0) + 1
MAX_PROCS = int(max((mp.cpu_count() * (1 - os.getloadavg()[0]), 0)) +1)
"""Number of maximum procs we can run
"""


class AutoWorkerQueue(Queue):

    def __init__(self, name='default', default_timeout=None, connection=None,
                 is_async=True, job_class=None, max_workers=None):
        super(AutoWorkerQueue, self).__init__(
            name=name, default_timeout=default_timeout, connection=connection,
            is_async=is_async, job_class=job_class
        )
        if max_workers is None:
            max_workers = MAX_PROCS
        self.max_workers = max_workers

    def enqueue(self, f, *args, **kwargs):
        res = super(AutoWorkerQueue, self).enqueue(f, *args, **kwargs)
        self.run_autowker()
        return res

    def enqueue_job(self, job, pipeline=None, at_front=False):
        res = super(AutoWorkerQueue, self).enqueue_job(job, pipeline, at_front)
        self.run_autowker()
        return res

    def run_autowker(self):
        if Worker.count(queue=self) <= self.max_workers:
            aw = AutoWorker(self.name, max_procs=1)
            aw.work()

    def run_job(self, job):
        return super(AutoWorkerQueue, self).run_job(job)


class AutoWorker(object):
    """AutoWorker allows to spawn multiple RQ Workers using multiprocessing.
    :param queue: Queue to listen
    :param max_procs: Number of max_procs to spawn
    """
    def __init__(self, queue=None, max_procs=None, skip_failed=True,
                 default_result_ttl=DEFAULT_RESULT_TTL):
        if queue is None:
            queue = 'default'
        if max_procs is None:
            self.max_procs = MAX_PROCS
        elif 1 <= max_procs < MAX_PROCS + 1:
            self.max_procs = max_procs
        else:
            raise ValueError('Max procs {} not supported'.format(max_procs))
        self.processes = []
        self.config = config_from_environment(
            'AUTOWORKER',
            ['redis_url'],
            queue_class='rq.Queue',
            worker_class='rq.Worker',
            job_class='rq.Job',
        )
        self.skip_failed = skip_failed
        self.default_result_ttl = default_result_ttl
        self.connection = Redis.from_url(self.config['redis_url'])
        queue_class = import_attribute(self.config['queue_class'])
        self.queue = queue_class(queue, connection=self.connection)

    def num_connected_workers(self):
        return len([
            w for w in Worker.all(queue=self.queue) if w.state in (
                WorkerStatus.STARTED, WorkerStatus.SUSPENDED, WorkerStatus.BUSY,
                WorkerStatus.IDLE
            )
        ])

    @property
    def worker_command(self):
        """Internal target to use in multiprocessing
        """

        rq_params = {
            '-b': '',
            '-w': self.config['worker_class'],
            '-n': '{}-auto'.format(uuid4().hex),
            '-u': self.config['redis_url'],
            '--results-ttl': self.default_result_ttl

        }
        if self.skip_failed:
            rq_params['--disable-default-exception-handler'] = ''

        command = ['rq', 'worker']
        for k, v in rq_params.items():
            command.append(str(k))
            if v:
                command.append(str(v))
        command.append(self.queue.name)
        return command

    def work(self):
        """Spawn the multiple workers using multiprocessing and `self.worker`_
        targget
        """
        max_procs = self.max_procs - self.num_connected_workers()
        env = os.environ.copy()
        env['PYTHONPATH'] = ':'.join(sys.path)
        for _ in range(0, max_procs):
            subprocess.Popen(self.worker_command, close_fds=True, env=env)
