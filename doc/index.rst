Welcome to mpdispatcher's documentation!
========================================

Signal dispatcher for multiprocessing, with asyncio support.

Quick Example
-------------

A minimal example that demonstrates the main functionality:

.. code:: python

   from mpdispatcher import MpDispatcher
   import asyncio
   import multiprocessing as mp
   from time import sleep

   async def some_async_task():
     # pretend to do something...
     print("some_async_task task started")
     await asyncio.sleep(2)
     print("some_async_task task finished")

   def some_event_handler(some_arg):
     print(f"handling event with arg '{some_arg}' in child process")

   async def asyncio_main(receiver):
     await asyncio.wait([
       asyncio.create_task(x) for x in [
         some_async_task(),
         receiver.coro_handle_until_closed()
       ]
     ])

   def process_target(receiver):
     receiver.connect("some_event", some_event_handler)
     asyncio.run(asyncio_main(receiver))


   dispatcher = MpDispatcher()

   proc = mp.Process(target=process_target, args=[dispatcher.receiver])
   proc.start()

   sleep(1)
   print("firing event from parent process")
   dispatcher.sender.fire("some_event", "hello world")
   sleep(2)
   print("closing dispatcher")
   dispatcher.sender.close()

Output:

.. code::
   some_async_task task started
   firing event from parent process
   handling event with arg 'hello world' in child process
   some_async_task task finished
   closing dispatcher


See :doc:`usage` for more detailed instructions and explanations.


Similar projects
----------------

- TODO


Table of contents
-----------------

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   installation
   usage
   api


Indices and tables
------------------

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
