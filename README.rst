AutoWorker
==========

.. image:: https://travis-ci.org/gisce/autoworker.svg?branch=master
    :target: https://travis-ci.org/gisce/autoworker

Spawn RQ Workers automatically

.. code-block:: python

    from autoworker import AutoWorker
    aw = AutoWorker(queue='high', max_procs=6)
    aw.work()

**Note**: From **v0.4.0** failed jobs doesn't go to the failed queue. If you want to enqueue to failed queue you should call `AutoWorker` as following

.. code-block:: python

    aw = AutoWorker(queue='high', max_procs=6, skip_failed=False)
