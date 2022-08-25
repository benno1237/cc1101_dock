import datetime
import asyncio
import websockets

from enum import IntEnum
from typing import Optional, List

from cc1101 import CC1101, ReceivedPacket


class SensorTypes(IntEnum):
    TEMPERATURE = 0
    HUMIDITY = 1
    SWITCH = 2


class NodeTypes(IntEnum):
    PUSH = 0  # Node pushes data at regular intervals
    POLL = 1  # Server polls the node


class ConnectionTypes(IntEnum):
    SERIAL = 0
    WEBSERVER = 1


class Main:
    _WS_PORT = 8001
    _WS_HOST = "127.0.0.1:"
    _WS_URI = f"ws://{_WS_HOST}:{_WS_PORT}"

    def __init__(self):
        self._node_pool: List[NodeBase] = []
        self._connection_type = ConnectionTypes.WEBSERVER
        self._ws: Optional[websockets.WebSocketServer] = None

    async def initialize(self):
        if self._connection_type == ConnectionTypes.WEBSERVER:
            try:
                self._ws = await websockets.connect(uri=self._WS_URI)
            except (websockets.InvalidHandshake, asyncio.TimeoutError):
                await self._ws.close()
                raise NotImplementedError

        elif self._connection_type == ConnectionTypes.SERIAL:
            # ToDo: initialize serial connection

    async def main(self):
        for node in self._node_pool:
            if node._should_be_polled():
                await node.poll()

    async def publish(self):
        if self._connection_type == ConnectionTypes.WEBSERVER:


class NodeBase:
    def __init__(
            self,
            node_type: NodeTypes,
    ):
        self.type: NodeTypes = node_type  # whether the node pushes or has to be polled
        self.poll_frequency: int = 0
        self.requires_confirmation: bool = False  # whether the node requires confirmation of successful transfer
        self.packet_length: int = 0  # the packet length to expect from the node

        self._channel: int = 0  # the rf channel the node is at

        self._node_timeout: float = 0.5  # Timeout in s
        self._next_poll: Optional[datetime.datetime] = None

    @property
    def last_active(self):
        """Last message from the remote node"""
        return self._next_poll - datetime.timedelta(seconds=self.poll_frequency)

    @property
    def channel(self):
        """The nodes rf channel"""
        return self._channel

    async def send_confirmation(self):
        """Send a confirmation of receipt to the node"""
        CC1101.set_channel(None, self._channel)
        await CC1101.send_data(None, 0)

    def _should_be_polled(self):
        if self.type == NodeTypes.POLL:
            if self._next_poll < datetime.datetime.now(datetime.timezone.utc):
                return True
        return False

    async def _wait_for_received(self):
        """Handle received packages"""
        try:
            data = await asyncio.wait_for(CC1101.receive_data(), timeout=self._node_timeout)
        except asyncio.TimeoutError:
            raise NotImplementedError

        await self.packet_received(data)

        self._next_poll = datetime.datetime.now(datetime.timezone.utc) + \
                          datetime.timedelta(seconds=self.poll_frequency)

    async def packet_received(self, data: ReceivedPacket):
        """Overwrite this when subclassing"""

    async def poll(self):
        """Polls the node"""
        CC1101.set_channel(None, self._channel)
        await CC1101.send_data(None, 0)
