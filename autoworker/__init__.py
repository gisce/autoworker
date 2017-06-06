import os
import multiprocessing as mp

from redis import StrictRedis
from rq.contrib.legacy import cleanup_ghosts
from osconf import config_from_environment


MAX_PROCS = mp.cpu_count() + 1
"""Number of maximum procs we can run
"""


class AutoWorker(object):
    """AutoWorker allows to spawn multiple RQ Workers using multiprocessing.
    :param queue: Queue to listen
    :param max_procs: Number of max_procs to spawn
    """
    def __init__(self, queue=None, max_procs=None):
        if queue is None:
            self.queue = 'default'
        else:
            self.queue = queue
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

    def worker(self):
        """Internal target to use in multiprocessing
        """
        from rq.utils import import_attribute
        conn = StrictRedis.from_url(self.config['redis_url'])
        cleanup_ghosts(conn)
        worker_class = import_attribute(self.config['worker_class'])
        queue_class = import_attribute(self.config['queue_class'])
        q = [queue_class(self.queue, connection=conn)]
        worker = worker_class(q, connection=conn)
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
        self.processes = [
            mp.Process(target=self._create_worker) for _ in range(0, self.max_procs)
        ]
        for proc in self.processes:
            proc.daemon = True
            proc.start()
