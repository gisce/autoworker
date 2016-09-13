import multiprocessing as mp
from rq import Worker, Queue
from redis import StrictRedis

MAX_PROCS = mp.cpu_count() + 1


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
        elif 1 < max_procs < MAX_PROCS + 1:
            self.max_procs = max_procs
        else:
            raise ValueError('Max procs {} not supported'.format(max_procs))
        self.processes = []

    def worker(self):
        """Internal target to use in multiprocessing
        """
        conn = StrictRedis()
        q = [Queue(self.queue, connection=conn)]
        worker = Worker(q, connection=conn)
        worker._name = '{}-auto'.format(worker.name)
        worker.work(burst=True)

    def work(self):
        """Spawn the multiple workers using multiprocessing and `self.worker`_
        targget
        """
        self.processes = [
            mp.Process(target=self.worker) for _ in range(0, self.max_procs)
        ]
        for proc in self.processes:
            proc.daemon = False
            proc.start()
