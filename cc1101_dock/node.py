import datetime
import asyncio
from typing import Optional, List
from enum import IntEnum

from sensors import *
from cc1101 import CC1101, ReceivedPacket


class NodeTypes(IntEnum):
  PUSH = 0  # Node pushes data at regular intervals
  POLL = 1  # Server polls the node


class NodePool:

  def __init__(self):
    self.nodes: List[Node] = []

  async def initialize_nodes(self, config: dict):
    """
    Initialize all nodes on startup and add them to the node pool
    """
    for node_name, node_config in config.items():
      if node_config.get('combine_sensors',
                         False) is True:  # we use a single node with multiple sensors
        node = Node(node_config)
        self.nodes.append(node)
      else:
        for sensor in node_config['sensors']:
          for sensor_name, sensor_config in sensor.items():
            sensor_node_config = {
                "name": f"{node_config['name']}_{sensor_name}",
                "id": node_config['id'],
                "sensors": [sensor_config],
            }
            node = Node(sensor_node_config)
            self.nodes.append(node)
            
  async def main(self):
    for node in self.nodes:
      if node.should_be_polled():
        await node.poll()
        to_transmit = await node._wait_for_received()
      elif node.type == NodeTypes.PUSH:  # Check nodes that push data
        to_transmit = await node._wait_for_received()


class Node:

  def __init__(
      self,
      node_config: dict,
  ):
    self.sensors: List[SensorBase] = []
    self._channel: int = 0  # the rf channel the node is at
    self._node_timeout: float = 1  # Timeout in seconds for the node to respond
    self._combined: bool = False

    # Build the node
    self._build_node(node_config)

  def _build_node(self, node_config: dict):
    for sensor in node_config.get('sensors', []):
      for sensor_type, values in sensor.items():
        sensor_class = SENSORS.get(sensor_type, None)
        if sensor_class is None:
          raise ValueError(f"Sensor type {sensor_type} not found")
        sensor_type: SensorTypes = values.get('type', 'poll')
        if sensor_type == 'poll':
          sensor_type = SensorTypes.POLL
        else:
          sensor_type = SensorTypes.PUSH
        update_rate = values.get('update_rate', 0)
        requires_confirmation = values.get('confirmation', False)
        packet_length = values.get('packet_length', 0)

        self.sensors.append(
            sensor_class(
                sensor_type, update_rate, requires_confirmation, packet_length))

    self._channel = node_config.get('channel', 0)
    self._node_timeout = node_config.get('node_timeout', self._node_timeout)
    self._combined = node_config.get('combine_sensors', self._combined)

  @property
  def last_active(self):
    """Return the latest last_active timestamp from all sensors or None."""
    if not self.sensors:
      return None

    if self._combined:
      return self.sensors[0].last_active

    latest_timestamp = None
    for sensor in self.sensors:
      if sensor.last_active is not None:
        if latest_timestamp is None or sensor.last_active > latest_timestamp:
          latest_timestamp = sensor.last_active

    return latest_timestamp

  @property
  def channel(self):
    """The nodes rf channel"""
    return self._channel

  @property
  def combined(self):
    """Whether the node combines multiple sensors that should be sent together"""
    return self._combined

  async def send_confirmation(self):
    """Send a confirmation of receipt to the node"""
    CC1101.set_channel(self._channel)
    await CC1101.send_data(0)

  def next_poll_times(self):
    """Return a list of next poll times for each sensor or the combined next poll time."""
    if self._combined:
      return [self.sensors[0].next_poll()]

    return [sensor.next_poll() for sensor in self.sensors]

  def should_be_polled(self):
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
