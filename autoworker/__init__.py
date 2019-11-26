import os
import multiprocessing as mp

from redis import StrictRedis
from rq.contrib.legacy import cleanup_ghosts
from rq.queue import Queue
from rq.worker import Worker, WorkerStatus
from rq.utils import import_attribute
from osconf import config_from_environment


MAX_PROCS = mp.cpu_count() + 1
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
        if Worker.count(queue=self) <= self.max_workers:
            aw = AutoWorker(self.name, max_procs=1)
            aw.work()
        return res

    def run_job(self, job):
        return super(AutoWorkerQueue, self).run_job(job)


class AutoWorker(object):
    """AutoWorker allows to spawn multiple RQ Workers using multiprocessing.
    :param queue: Queue to listen
    :param max_procs: Number of max_procs to spawn
    """
    def __init__(self, queue=None, max_procs=None, skip_failed=True,
                 default_result_ttl=None):
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
        self.connection = StrictRedis.from_url(self.config['redis_url'])
        queue_class = import_attribute(self.config['queue_class'])
        self.queue = queue_class(queue, connection=self.connection)

    def num_connected_workers(self):
        return len([
            w for w in Worker.all(queue=self.queue) if w.state in (
                WorkerStatus.STARTED, WorkerStatus.SUSPENDED, WorkerStatus.BUSY,
                WorkerStatus.IDLE
            )
        ])

    def worker(self):
        """Internal target to use in multiprocessing
        """
        cleanup_ghosts(self.connection)
        worker_class = import_attribute(self.config['worker_class'])
        if self.skip_failed:
            exception_handlers = []
        else:
            exception_handlers = None

        worker = worker_class(
            [self.queue], connection=self.connection,
            exception_handlers=exception_handlers,
            default_result_ttl=self.default_result_ttl
        )
        worker._name = '{}-auto'.format(worker.name)
        worker.work(burst=True)

    def _create_worker(self):
        child_pid = os.fork()
        if child_pid == 0:
            self.worker()

    def work(self):
        """Spawn the multiple workers using multiprocessing and `self.worker`_
        targget
        """
        max_procs = self.max_procs - self.num_connected_workers()
        self.processes = [
            mp.Process(target=self._create_worker) for _ in range(0, max_procs)
        ]
        for proc in self.processes:
            proc.daemon = True
            proc.start()
