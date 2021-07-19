from mpdispatcher import MpDispatcher
from multiprocessing import Process
import pytest

def process_target(receiver):
  l = []
  def cb(arg):
    l.append(arg)
  receiver.connect("cb", cb)
  receiver.handle_next(timeout=2)
  assert l == [54]

def test_handle_next_in_child_proc_with_timeout():
  dispatcher = MpDispatcher()
  proc = Process(target=process_target, args=[dispatcher.receiver])
  proc.daemon = True
  proc.start()
  dispatcher.sender.fire("cb", 54)
  proc.join(timeout=2)
  assert not proc.is_alive()
  assert proc.exitcode == 0


def process2_target(sender):
  sender.fire("cb", 54)
  print("end of proc2")

def test_handle_next_in_parent_proc_with_timeout():
  dispatcher = MpDispatcher()
  proc = Process(target=process2_target, args=[dispatcher.sender])
  l = []
  def cb(arg):
    l.append(arg)
  dispatcher.receiver.connect("cb", cb)
  proc.start()
  import queue
  dispatcher.receiver.handle_next(timeout=2)
  proc.join(timeout=2)
  assert l == [54]
  assert not proc.is_alive()
  assert proc.exitcode == 0
