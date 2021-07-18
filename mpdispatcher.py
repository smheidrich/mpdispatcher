import asyncio
from functools import partial
from concurrent.futures import ThreadPoolExecutor
import multiprocessing as mp
import queue

CLOSE_SENTINEL = "CLOSE"

class MpDispatcher:
    """
    Callback dispatcher for multiprocessing processes

    Note that passing this as a mp.Process arg/kwarg (which will pickle it)
    should work, but of course listeners *won't* be synchronized across process
    boundaries! So only use `receiver.connect()` on the side on which the
    callbacks should actually run, otherwise things get confusing.
    """
    def __init__(self, q=None):
        if q is None:
            q = mp.Queue()
        self.receiver = MpDispatchReceiver(q=q)
        self.sender = MpDispatchSender(q=q)

class MpDispatchSender:
    """
    Sending end of an MpDispatcher.

    Can be used to `fire()` signals/events, which will be put into the queue on
    which the corresponding receiving end listens.
    """
    def __init__(self, q=None):
        self.q = q
        self.closed = False

    def fire(self, signal, *args, **kwargs):
        """
        Fire off an event.
        """
        self.q.put((signal, args, kwargs))

    def close(self):
        """
        Closes the underlying queue and aborts any blocking calls.
        """
        self.q.put(CLOSE_SENTINEL)


class MpDispatchReceiver:
    """
    Receiving end of an MpDispatcher.

    Can be used to `connect()` signal names to functions (listeners), which
    will be called when a signal of that name arrives.
    """
    def __init__(self, q=None):
        self.listeners = {}
        self.q = q
        self.closed = False

    def __del__(self):
        self.close()

    def connect(self, signal, cb):
        if signal not in self.listeners:
            self.listeners[signal] = []
        self.listeners[signal].append(cb)

    def _handle_received(self, obj):
        if obj == CLOSE_SENTINEL:
            self.closed = True
            return
        # TODO exception isolation perhaps
        signal, args, kwargs = obj
        if signal not in self.listeners:
            return
        for listener in self.listeners[signal]:
            listener(*args, **kwargs)

    def handle_next(self, call_via=None, **q_get_kwargs):
        """
        Waits for the next incoming event and handles it by dispatching.

        If `call_via` is not `None`, it's expected to be a callable that will
        be passed the event processing function and should make sure that the
        latter gets called from whichever thread or process originally called
        `handle_next()`. Most likely you won't ever use this directly but via
        `threaded_handle_until_closed()`.

        Blocking unless otherwise specified in `q_get_kwargs`
        """
        if self.closed:
            raise Closed()
        obj = self.q.get(**q_get_kwargs)
        # NOTE: the close handling below is NOT superfluous just because it
        # also appears in _handle_received. When using
        # threaded_handle_until_closed, _handle_received will be called in the
        # original thread, while the loop for queue listening via
        # handle_until_closed (which calls this function here) will be
        # performed in a separate listening thread. It's important that
        # self.closed gets set in the listening thread so handle_until_closed
        # returns. When using coro_handle_until_closed, by contrast, the loop
        # condition is checked in the main thread and only the individual queue
        # listening iterations are done in the separate thread (made possible
        # via cooperative multitasking), so for that one we do need to set
        # self.closed in the original thread. Hence, both are required until I
        # change the architecture to e.g. have the non-coroutine version
        # emulate the coroutine version by scheduling the next listening
        # iteration from the original thread at the end of each
        # _handle_received instead of threading the whole loop, or something
        # like that.
        if obj == CLOSE_SENTINEL:
            self.closed = True
        if call_via is None:
            self._handle_received(obj)
        else:
            call_via(partial(self._handle_received, obj))

    def handle_until_blocking(self):
        """
        Handle all events currently in the queue until the queue would block.

        You should know exactly what you're doing when deciding to use this, as
        it's an easy way to get race conditions. The sensible use cases are
        fairly limited.
        """
        while True:
            try:
                self.handle_next(block=False)
            except queue.Empty:
                break

    async def coro_handle_next(self, pool, **q_get_kwargs):
        """
        Like handle_next() but async by waiting in a separate thread.

        For users of this library, it probably makes more sense to use
        `coro_handle_until_closed`, which calls this method internally.

        Blocking unless otherwise specified in `q_get_kwargs`

        `pool` should be a `ThreadPoolExecutor` (the whole point of these is
        re-use, so it wouldn't make any sense for this method to allocate a new
        one on each call that then gets used only once, and I'm too lazy to
        have instances of this class cache them).
        """
        if self.closed:
            raise Closed()
        loop = asyncio.get_running_loop()
        obj = await loop.run_in_executor(
            pool, partial(self.q.get, **q_get_kwargs)
        )
        self._handle_received(obj)

    def handle_until_closed(self, call_via=None):
        """
        Waits for incoming events in a blocking manner and handles them.

        Cf. `handle_next()` and `threaded_handle_until_closed()` for
        explanation of `call_via`.
        """
        while not self.closed:
          self.handle_next(call_via=call_via)

    def threaded_handle_until_closed(self, call_via, executor=None):
        """
        Like handle_until_closed() but async by waiting in a separate thread.

        `call_via` needs to be some function that allows scheduling function
        calls back in the original thread from the spawned listening thread,
        e.g. `idle_add` in Glib or `loop.call_soon_threadsafe` in asyncio. See
        the section on "guest mode" in [1], where I stole this idea from.

        [1]: https://trio.readthedocs.io/en/stable/reference-lowlevel.html .
        """
        self._executor = executor or ThreadPoolExecutor()
        self._executor.submit(self.handle_until_closed, call_via=call_via)

    async def coro_handle_until_closed(self):
        """
        Like threaded_handle_until_closed() but as a coroutine.

        This means listeners can be called from within the original thread, so
        no `call_via` is required.
        """
        with ThreadPoolExecutor() as pool:
            while not self.closed:
                await self.coro_handle_next(pool=pool)

    def close(self):
        """
        Closes the underlying queue and aborts any blocking calls.
        """
        self.q.put(CLOSE_SENTINEL)

class Closed(Exception):
    pass
