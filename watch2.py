import autobahn
import trollius as asyncio
from autobahn.asyncio.websocket import WebSocketClientProtocol

class MyClientProtocol(WebSocketClientProtocol):

   def onOpen(self):
      self.sendMessage(u"Hello, world!".encode('utf8'))

   def onMessage(self, payload, isBinary):
      if isBinary:
         print("Binary message received: {0} bytes".format(len(payload)))
      else:
         print("Text message received: {0}".format(payload.decode('utf8')))

try:
  import asyncio
except ImportError:
  ## Trollius >= 0.3 was renamed
  import trollius as asyncio

from autobahn.asyncio.websocket import WebSocketClientFactory
factory = WebSocketClientFactory()
factory.protocol = MyClientProtocol

loop = asyncio.get_event_loop()
coro = loop.create_connection(factory, '192.168.1.15', 80)
loop.run_until_complete(coro)
loop.run_forever()
loop.close()