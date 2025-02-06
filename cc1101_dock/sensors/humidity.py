from typing import TYPE_CHECKING

from . import SensorBase

if TYPE_CHECKING:
    from cc1101.cc1101 import ReceivedPacket


class HumiditySensor(SensorBase):
    async def packet_received(self, packet: 'ReceivedPacket') -> str:
        if packet.valid:
            data = packet.data
            # Default temp node follows the format:
            # example: 3332198
            # first two digits: battery level
            # 3rd to 5th: temperature
            # 6th to 7th: humidity
            to_transmit = {"Bat:": data[0:2], "Temp:": data[2:5], "Hum:": data[5:7]}
            return str(to_transmit)