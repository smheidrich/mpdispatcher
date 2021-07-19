Usage
=====

.. py:currentmodule:: mpdispatcher

Basic usage
-----------

Creating a new :class:`MpDispatcher` instance:

>>> from mpdispatcher import MpDispatcher
>>>
>>> disp = MpDispatcher()

Each :class:`MpDispatcher` has a a sender (:class:`MpDispatchSender`) and
receiver (:class:`MpDispatchReceiver`):

>>> sender, receiver = disp.sender, disp.receiver

Handler functions ("listeners") for events (identified by strings) are attached
to the receiving end using :meth:`MpDispatchSender.connect`:

>>> def handle_new_user(name):
...   print(f"Hello {name}.")
>>>
>>> receiver.connect("on_new_user", handle_new_user)

Handler functions can have arguments just like functions which will be filled
in from the event.

An event can be triggered on the sender using :meth:`MpDispatchSender.fire`:

>>> sender.fire("on_new_user", "Newman")

Arguments can be specified either positionally as done here or via keyword
arguments.

For now this event just sits in the dispatcher's internal
:class:`multiprocessing.Queue`, because while executing the callback would be
trivial in the single-process case here, in the multi-process case, there is no
way around explicitly specifying at which point in the code events should be
handled.

To cover as many use cases as possible, the receiver has several different
methods for handling events and calling the appropriate callbacks. The simplest
one is :meth:`MpDispatchReceiver.handle_next`, which processes only one event
at a time:

>>> receiver.handle_next()
Hello Newman.

The more practically useful methods all involve blocking or concurrency and
therefore make more sense in a multiprocessing or asyncio context, which will
be described in the following sections.
Note that one use case for :meth:`MpDispatchReceiver.handle_next` would be
within a busy-waiting / polling loop, but that should of course be avoided if
possible.


Pure listening process
----------------------

The next simplest use case is probably a process which does nothing but listen
to events and call the attached functions. In this case, we can use the
blocking :meth:`MpDispatchReceiver.handle_until_closed` method:

.. code:: python

  import multiprocessing as mp
  
  def proc_target(receiver):
    def handle_new_user(name):
      print(f"Hello {name}.")

    def handle_delete_user(name):
      print(f"Goodbye {name}.")

    receiver.connect("on_new_user", handle_new_user)
    receiver.connect("on_delete_user", handle_delete_user)

    receiver.handle_until_closed()
  
  if __name__ == "__main__":
    disp = MpDispatcher()
    proc = mp.Process(target=proc_target, args=[disp.receiver])
    proc.start()
    
    disp.sender.fire("on_new_user", "Jerry")
    disp.sender.fire("on_delete_user", "Newman")
    disp.sender.close()
    proc.join()

The output of this would be:

.. code:: text

  Hello Jerry.
  Goodbye Newman.

This would work just as well if we were firing events from the child process to
the parent process, of course, we'd just have to make sure to pass the sender
to the child instead of the receiver.


Listening process with concurrency
----------------------------------

TODO
