import os
import multiprocessing as mp

from redis import StrictRedis
from rq.contrib.legacy import cleanup_ghosts
from rq.worker import Worker
from rq.utils import import_attribute
from osconf import config_from_environment


MAX_PROCS = mp.cpu_count() + 1
"""Number of maximum procs we can run
"""


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
        max_procs = self.max_procs - Worker.count(self.queue)
        self.processes = [
            mp.Process(target=self._create_worker) for _ in range(0, max_procs)
        ]
        for proc in self.processes:
            proc.daemon = True
            proc.start()
