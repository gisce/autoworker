AutoWorker
==========

.. image:: https://travis-ci.org/gisce/autoworker.svg?branch=master
    :target: https://travis-ci.org/gisce/autoworker

Spawn RQ Workers automatically

.. code-block:: python

    from autoworker import AutoWorker
    aw = AutoWorker(queue='high', max_procs=6)
    aw.work()
