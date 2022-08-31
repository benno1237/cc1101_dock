import datetime
import asyncio

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
    _STREAM_PORT = 8001
    _STREAM_URI = "127.0.0.1:"

    def __init__(self):
        self._node_pool: List[NodeBase] = []
        self._connection_type = ConnectionTypes.WEBSERVER
        self._stream_writer: Optional[asyncio.StreamWriter] = None

    async def initialize(self):
        if self._connection_type == ConnectionTypes.WEBSERVER:
            try:
                _, self._stream_writer = await asyncio.open_connection(
                    self._STREAM_URI, self._STREAM_PORT
                )
            except Exception as e:
                # ToDo: handle connection issues
                raise e

        elif self._connection_type == ConnectionTypes.SERIAL:
            # ToDo: initialize serial connection

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
        CC1101.set_channel(self._channel)
        await CC1101.send_data(0)

    def _should_be_polled(self):
        if self.type == NodeTypes.POLL:
            if self._next_poll < datetime.datetime.now(datetime.timezone.utc):
                return True
        return False

    async def _wait_for_received(self):
        """Handle received packages"""
        to_transmit = None
        if self.type == NodeTypes.POLL:
            timeout = datetime.datetime.now(datetime.timezone.utc) + \
                      datetime.timedelta(seconds=self._node_timeout)

            while datetime.datetime.now(datetime.timezone.utc) < timeout:
                if CC1101.check_rx_fifo():
                    packet = CC1101.receive_data()
                    break
                else:
                    await asyncio.sleep(0.01)
            else:
                raise asyncio.TimeoutError  # node took longer than node_timeout seconds to respond

            to_transmit = await self.packet_received(packet)
            if not isinstance(to_transmit, str):
                # ToDo: handle different data classes
                raise NotImplementedError

            self._next_poll = datetime.datetime.now(datetime.timezone.utc) + \
                              datetime.timedelta(seconds=self.poll_frequency)
        else:
            if CC1101.check_rx_fifo():
                packet = CC1101.receive_packet()
                to_transmit = await self.packet_received(packet)

        return to_transmit

    async def packet_received(self, data: ReceivedPacket) -> str:
        """Overwrite this when subclassing
        Return a string representing the data you want to forward over the TCP stream"""

    async def poll(self):
        """Polls the node"""
        CC1101.set_channel(self._channel)
        await CC1101.send_data(0)

class TempHumNode:
    async def packet_received(self, packet: ReceivedPacket) -> str:
        if packet.valid:
            data = packet.data
            # Default temp node follows the format:
            # example: 3332198
            # first two digits: battery level
            # 3rd to 5th: temperature
            # 6th to 7th: humidity
            to_transmit = {"Bat:": data[0:2], "Temp:": data[2:5], "Hum:": data[5:7]}
            return str(to_transmit)
