GoReplay Middleware
===================

Python library for `GoReplay Middleware <https://github.com/buger/goreplay>`_ , API is quite similar to `NodeJS library <https://github.com/buger/goreplay/tree/master/middleware>`_

.. image:: https://badge.fury.io/py/gor.svg
    :target: https://badge.fury.io/py/gor
.. image:: https://app.travis-ci.com/amyangfei/GorMW.svg?branch=master
    :target: https://app.travis-ci.com/amyangfei/GorMW
.. image:: https://coveralls.io/repos/github/amyangfei/GorMW/badge.svg?branch=master
    :target: https://coveralls.io/github/amyangfei/GorMW?branch=master

Installation
------------

To install GorMW, simply:

.. code-block:: bash

    $ pip install gor

or from source:

.. code-block:: bash

    python setup.py install

Getting Started
---------------

Initialize a AsyncioGor based middleware and start it in the following way:

.. code-block:: python

    from gor.middleware import AsyncioGor
    proxy = AsyncioGor()
    proxy.run()

Basic idea is that you write callbacks which respond to request, response, replay, or message events, which contains request meta information and actuall http paylod. Depending on your needs you may compare, override or filter incoming requests and responses.

You can respond to the incoming events using on function, by providing callbacks:

.. code-block:: python

    def on_request(proxy, msg, **kwargs):
        # do anything you want with msg
        # msg is a GorMessage object
        pass

    proxy = AsyncioGor()
    proxy.on('request', on_request)
    proxy.run()

You can provide request ID as additional argument to on function, which allow you to map related requests and responses. Below is example of middleware which checks that original and replayed response have same HTTP status code. Have a try with the following command and sample middleware.

.. code-block:: bash

    gor --input-raw :14000 --middleware "/path/to/middleware.py" --output-http-track-response --input-raw-track-response --output-http "http://127.0.0.1:14001"

.. code-block:: python

    # coding: utf-8
    import sys
    from gor.middleware import AsyncioGor


    def on_request(proxy, msg, **kwargs):
        proxy.on('response', on_response, idx=msg.id, req=msg)

    def on_response(proxy, msg, **kwargs):
        proxy.on('replay', on_replay, idx=kwargs['req'].id, req=kwargs['req'], resp=msg)

    def on_replay(proxy, msg, **kwargs):
        replay_status = proxy.http_status(msg.http)
        resp_status = proxy.http_status(kwargs['resp'].http)
        if replay_status != resp_status:
            sys.stderr.write('replay status [%s] diffs from response status [%s]\n' % (replay_status, resp_status))
        else:
            sys.stderr.write('replay status is same as response status\n')
        sys.stderr.flush()

    if __name__ == '__main__':
        proxy = AsyncioGor()
        proxy.on('request', on_request)
        proxy.run()

.. note:: Since the release v0.2.x, Python2.7 and Python3.4 are not supported any more, the minimum supported Python version is 3.5.2. Besides the release v0.1.x is still compatible with Python2.7 and Python3.4.

Mutiple middleware choices
--------------------------

This library provides multiple middleware to choice, currently includes

- AsyncioGor, implements based on python3 asyncio
- MultiProcessGor, implements based multi processing
