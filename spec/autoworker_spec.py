import os
from autoworker import AutoWorker, MAX_PROCS
from rq.queue import Queue

from expects import *
from mamba import *

# Setup environment variable
os.environ['AUTOWORKER_REDIS_URL'] = 'redis://localhost:6379/0'


with description('The autoworker class'):
    with context('if not max_procs is defined'):
        with it('must use the limit based on CPU count and system load'):
            a = AutoWorker()
            expect(a.max_procs).to(equal(MAX_PROCS))

    with context('if max_procs is passed to __init__'):
        with it('must be the the same value'):
            a = AutoWorker(max_procs=1)
            expect(a.max_procs).to(equal(1))

        with it('must raise an error if max_procs exceeds the limit'):
            def callback():
                AutoWorker(max_procs=MAX_PROCS + 1)

            expect(callback).to(raise_error(ValueError))

    with context('if no queue is defined'):
        with it('must be "default" queue'):
            a = AutoWorker()
            q = Queue('default', connection=a.connection)
            expect(a.queue).to(equal(q))
    with context('if a queue is defined'):
        with it('have to be the same value'):
            a = AutoWorker('low')
            q = Queue('low', connection=a.connection)
            expect(a.queue).to(equal(q))


with description('An instance of a AutoWorker'):
    with before.each:
        self.aw = AutoWorker(max_procs=1)

    with it('must have a "work" method to spawn max_procs workers'):
        self.aw.work()
