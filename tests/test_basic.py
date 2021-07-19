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
