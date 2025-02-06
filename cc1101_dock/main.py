import datetime
import asyncio

from enum import IntEnum
from typing import Optional, List

from cc1101.cc1101 import CC1101, ReceivedPacket

from .config import AsyncConfigManager
from .node import Node, NodePool
from .sensors import *


class Main:

  def __init__(self, config: str):
    self._node_pool: NodePool = NodePool()
    self._config_path = config

  async def initialize(self):
    await self._node_pool.initialize_nodes(self._config_path)

  async def main(self):
    for node in self._node_pool:
      to_transmit = None
      if node._should_be_polled():
        await node.poll()
        to_transmit = await node._wait_for_received()
      elif node.type == NodeTypes.PUSH:  # Check nodes that push data
        to_transmit = await node._wait_for_received()

      if isinstance(to_transmit, str):
        await self.publish(to_transmit)

  async def publish(self, message: str):
    if self._connection_type == ConnectionTypes.WEBSERVER:
      self._stream_writer.write(message.encode())
      await self._stream_writer.drain()
