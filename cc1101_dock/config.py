import asyncio
import yaml
import os
from watchgod import awatch
import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
# output to console
ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
logger.addHandler(ch)


class AsyncConfigManager:

  def __init__(self, config_file, on_reload=None):
    self.config_file = os.path.abspath(config_file)
    self.config = {}
    self.config_dir = os.path.dirname(self.config_file)
    self.on_reload = on_reload  # Optional callback function
    self._watch_task = None

  async def start(self):
    """Start the config manager and begin watching the config file for changes."""
    logger.info(f"Starting config manager for {self.config_file}")
    await self.load_config()
    self._watch_task = asyncio.create_task(self._watch_config())

  async def stop(self):
    """Stop watching the config file."""
    if self._watch_task:
      self._watch_task.cancel()
      try:
        await self._watch_task
      except asyncio.CancelledError:
        pass
      logger.info(f"Stopped config manager for {self.config_file}")

  async def load_config(self):
    """Load the configuration from the YAML file."""
    try:
      with open(self.config_file, 'r') as f:
        self.config = yaml.safe_load(f)
    except FileNotFoundError as e:
      logger.error(f"Config file not found: {self.config_file}")
      raise e
    except yaml.scanner.ScannerError as e:
      logger.error(f"Error parsing config file: {self.config_file}")
      raise e
      
    if self.on_reload:
      if asyncio.iscoroutinefunction(self.on_reload):
        await self.on_reload(self.config)
      else:
        self.on_reload(self.config)
    logger.debug(f"Loaded config: {self.config}")

  async def _watch_config(self):
    """Watch the config file for changes and reload it when modified."""
    try:
      async for changes in awatch(self.config_dir):
        for change_type, changed_file in changes:
          if os.path.abspath(changed_file) == self.config_file:
            await self.load_config()
            logger.debug("Config reloaded.")
            break  # Exit the inner loop once the config file is reloaded
    except asyncio.CancelledError:
      pass

  def get(self, key: str, default=None):
    """
    Retrieves a configuration value by key.

    Args:
      key (str): The key of the configuration value.
      default (Any, optional): The default value if the key is not found. Defaults to None.

    Returns:
      Any: The configuration value or the default if not found.
    """
    return self.config.get(key, default)
