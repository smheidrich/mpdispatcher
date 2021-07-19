# mpdispatcher

[![pipeline status](https://gitlab.com/smheidrich/mpdispatcher/badges/main/pipeline.svg?style=flat-square)](https://gitlab.com/smheidrich/mpdispatcher/-/commits/main)
[![codecov](https://img.shields.io/codecov/c/gl/smheidrich/mpdispatcher?style=flat-square&token=1WHSKDTZVC)](https://codecov.io/gl/smheidrich/mpdispatcher)
[![docs](https://img.shields.io/badge/docs-online-brightgreen?style=flat-square)](https://smheidrich.gitlab.io/mpdispatcher/)

Signal dispatcher for multiprocessing, with asyncio support.


## Installation

```bash
pip install git+https://gitlab.com/smheidrich/mpdispatcher.git
```

## Example

An example that demonstrates the asyncio functionality (requires Python 3.7+):

```python
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


if __name__ == "__main__":
  dispatcher = MpDispatcher()

  proc = mp.Process(target=process_target, args=[dispatcher.receiver])
  proc.start()

  sleep(1)
  print("firing event from parent process")
  dispatcher.sender.fire("some_event", "hello world")
  sleep(2)
  print("closing dispatcher")
  dispatcher.sender.close()
```

Output:
```
some_async_task task started
firing event from parent process
handling event with arg 'hello world' in child process
some_async_task task finished
closing dispatcher
```

Here, the
[asyncio-*flavored*](https://trio-asyncio.readthedocs.io/en/latest/principles.html#async-function-flavors)
coroutine `coro_handle_until_closed()`, which waits for events to be fired on
the sending end of the dispatcher, is run concurrently with other asyncio tasks
using `asyncio.wait`.

If you don't use asyncio (or only use it for some processes but not others),
there are also several non-coroutine versions of `coro_handle_until_closed()` -
please refer to the documentation for more information.


## Documentation

Extensive usage examples and the API reference can be found in the
[documentation](https://smheidrich.gitlab.io/mpdispatcher/).
