import asyncio
from mpdispatcher import MpDispatcher
from multiprocessing import Process
import pytest

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
