import asyncio
from mpdispatcher import MpDispatcher, Closed
from multiprocessing import Process
import multiprocessing as mp
import pytest
import sys
from time import sleep

@pytest.fixture()
def dispatcher():
  return MpDispatcher()


def receive_single_event(receiver):
  l = []
  def cb(arg):
    l.append(arg)
  receiver.connect("cb", cb)
  receiver.handle_next(timeout=2)
  assert l == [54]

def test_handle_next_in_child_proc_with_timeout(dispatcher):
  proc = Process(target=receive_single_event, args=[dispatcher.receiver])
  proc.daemon = True
  proc.start()
  dispatcher.sender.fire("cb", 54)
  proc.join(timeout=2)
  assert not proc.is_alive()
  assert proc.exitcode == 0


def receive_three_events_expecting_close(receiver):
  l = []
  def cb(arg):
    l.append(arg)
  receiver.connect("cb", cb)
  receiver.handle_next(timeout=2)
  receiver.handle_next(timeout=2)
  with pytest.raises(Closed):
    receiver.handle_next(timeout=2)

def test_handle_next_on_closed(dispatcher):
  proc = Process(target=receive_three_events_expecting_close,
    args=[dispatcher.receiver])
  proc.daemon = True
  proc.start()
  dispatcher.sender.fire("cb", 54)
  dispatcher.sender.close()
  proc.join(timeout=2)
  assert not proc.is_alive()
  assert proc.exitcode == 0


def send_single_event(sender):
  sender.fire("cb", 54)

def test_handle_next_in_parent_proc_with_timeout(dispatcher):
  proc = Process(target=send_single_event, args=[dispatcher.sender])
  l = []
  def cb(arg):
    l.append(arg)
  dispatcher.receiver.connect("cb", cb)
  proc.start()
  dispatcher.receiver.handle_next(timeout=2)
  proc.join(timeout=2)
  assert l == [54]
  assert not proc.is_alive()
  assert proc.exitcode == 0


def receive_events_until_closed(receiver):
  l = []
  def cb(arg):
    l.append(arg)
  receiver.connect("cb", cb)
  receiver.handle_until_closed()
  assert l == [43, 54, 87]

def test_handle_until_closed_in_child_proc(dispatcher):
  proc = Process(target=receive_events_until_closed,
    args=[dispatcher.receiver])
  proc.daemon = True
  proc.start()
  dispatcher.sender.fire("cb", 43)
  dispatcher.sender.fire("cb", 54)
  dispatcher.sender.fire("cb", 87)
  dispatcher.sender.close()
  proc.join(timeout=2)
  assert not proc.is_alive()
  assert proc.exitcode == 0


def receive_events_until_87(receiver):
  l = []
  def cb(arg):
    l.append(arg)
    if arg == 87:
      receiver.close()
  receiver.connect("cb", cb)
  receiver.handle_until_closed()
  assert l == [43, 54, 87]

def test_handle_until_closed_in_child_proc_closing_itself(dispatcher):
  proc = Process(target=receive_events_until_87,
    args=[dispatcher.receiver])
  proc.daemon = True
  proc.start()
  dispatcher.sender.fire("cb", 43)
  dispatcher.sender.fire("cb", 54)
  dispatcher.sender.fire("cb", 87)
  proc.join(timeout=2)
  assert not proc.is_alive()
  assert proc.exitcode == 0


def receive_events_until_blocking(receiver, aux_in, aux_out):
  l = []
  def cb(arg):
    l.append(arg)
  receiver.connect("cb", cb)
  assert aux_in.get(timeout=5) == "sent_3"
  receiver.handle_until_blocking()
  aux_out.put("blocks")
  assert l == [43, 54, 87]

def test_handle_until_blocking(dispatcher):
  aux_to_child, aux_from_child = mp.Queue(), mp.Queue()
  proc = Process(target=receive_events_until_blocking,
    args=[dispatcher.receiver, aux_to_child, aux_from_child])
  proc.daemon = True
  proc.start()
  dispatcher.sender.fire("cb", 43)
  dispatcher.sender.fire("cb", 54)
  dispatcher.sender.fire("cb", 87)
  aux_to_child.put("sent_3")
  assert aux_from_child.get("blocks")
  dispatcher.sender.fire("cb", 100)
  dispatcher.sender.close()
  proc.join(timeout=2)
  assert not proc.is_alive()
  assert proc.exitcode == 0


def receive_events_and_run_concurrent_coro(receiver):
  l = []
  l2 = []
  async def some_concurrent_coro():
    for i in range(3):
      l2.append(i**2)
      await asyncio.sleep(0.1)
  def cb(arg):
    l.append(arg)
  receiver.connect("cb", cb)
  async def asyncio_main(receiver):
    await asyncio.wait([
      asyncio.create_task(x) for x in [
        some_concurrent_coro(),
        receiver.coro_handle_until_closed()
      ]
    ])
  asyncio.run(asyncio_main(receiver))
  assert l == [43, 54, 87]
  assert l2 == [0, 1, 4]

@pytest.mark.skipif(sys.version_info < (3, 7),
  reason="requires python3.7 or higher")
def test_coro_handle_until_closed_in_child_proc(dispatcher):
  proc = Process(target=receive_events_and_run_concurrent_coro,
    args=[dispatcher.receiver])
  proc.daemon = True
  proc.start()
  dispatcher.sender.fire("cb", 43)
  dispatcher.sender.fire("cb", 54)
  dispatcher.sender.fire("cb", 87)
  dispatcher.sender.close()
  proc.join(timeout=2)
  assert not proc.is_alive()
  assert proc.exitcode == 0


def receive_events_threaded_and_run_parallel_coro(receiver):
  # note: asyncio here plays the role of any other event loop, as seen in
  # various GUI toolkits etc., so it's entirely incidental that this uses
  # coroutines instead of just synchronous functions with threads in the
  # background
  l = []
  l2 = []
  async def some_stoppable_coro(should_stop):
    await should_stop.wait()
    await asyncio.sleep(0.1)
    l2.extend([0,1,4])
  def cb(arg):
    l.append(arg)
  receiver.connect("cb", cb)
  async def asyncio_main(receiver):
    should_stop = asyncio.Event()
    def stop_coro():
      should_stop.set()
    receiver.connect("stop_coro", stop_coro)
    loop = asyncio.get_running_loop()
    receiver.threaded_handle_until_closed(call_via=loop.call_soon_threadsafe)
    await some_stoppable_coro(should_stop)
  asyncio.run(asyncio_main(receiver))
  assert l == [43, 54, 87]
  assert l2 == [0, 1, 4]

@pytest.mark.skipif(sys.version_info < (3, 7),
  reason="requires python3.7 or higher")
def test_threaded_handle_until_closed_in_child_proc(dispatcher):
  proc = Process(target=receive_events_threaded_and_run_parallel_coro,
    args=[dispatcher.receiver])
  proc.daemon = True
  proc.start()
  dispatcher.sender.fire("cb", 43)
  dispatcher.sender.fire("cb", 54)
  dispatcher.sender.fire("cb", 87)
  dispatcher.sender.fire("stop_coro")
  dispatcher.sender.close()
  proc.join(timeout=2)
  assert not proc.is_alive()
  assert proc.exitcode == 0
