import time

from enum import IntEnum
from typing import Optional

from .battery import BatterySensor
from .humidity import HumiditySensor
from .temperature import TemperatureSensor


SENSORS = {  # list of all sensors
    'battery': BatterySensor,
    'temperature': TemperatureSensor,
    'humidity': HumiditySensor
}


class SensorTypes(IntEnum):
    PUSH = 0  # Node pushes data at regular intervals
    POLL = 1  # Server polls the node


class SensorBase:
    def __init__(
            self,
            sensor_type: SensorTypes,
            update_rate: int,
            requires_confirmation: bool,
            packet_length: int
    ):
        self._last_message_ts: Optional[float] = None
        self._sensor_type: SensorTypes = sensor_type
        self._update_rate: int = update_rate
        self._requires_confirmation: bool = requires_confirmation
        self._packet_length: int = packet_length

    @property
    def last_active(self):
        """Last message from the remote node"""
        if self._last_message_ts is None:
            return None
        return self._last_message_ts

    @property
    def should_be_polled(self):
        """Whether the sensor should be polled"""
        if self._sensor_type == SensorTypes.POLL:
            return True

    @property
    def requires_confirmation(self):
        """Whether a confirmation message should be sent after receipt"""
        return self._requires_confirmation

    def next_poll(self) -> float:
        """Whether the sensor should be polled"""
        if self._last_message_ts is None:
            return time.time()
        return self._last_message_ts + self._update_rate
