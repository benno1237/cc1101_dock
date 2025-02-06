import pytest
import pytest_asyncio
import asyncio
import yaml
import os
from cc1101_dock.config import AsyncConfigManager


@pytest.mark.asyncio
class TestAsyncConfigManager:

  @pytest_asyncio.fixture
  async def config_manager(self, tmp_path):
    # Create a temporary config file
    config_file = tmp_path / "test_config.yaml"
    config_data = {"test_key": "test_value"}
    with open(config_file, 'w') as f:
      yaml.dump(config_data, f)

    manager = AsyncConfigManager(str(config_file))
    await manager.start()
    yield manager
    # Cleanup
    await manager.stop()

  async def test_init(self, tmp_path):
    config_file = tmp_path / "config.yaml"
    manager = AsyncConfigManager(str(config_file))
    assert manager.config_file == str(config_file.absolute())
    assert manager.config == {}
    assert manager.config_dir == str(tmp_path)
    assert manager._watch_task is None

  async def test_load_config(self, config_manager):
    await config_manager.load_config()
    assert config_manager.config == {"test_key": "test_value"}

  async def test_get_existing_key(self, config_manager):
    await config_manager.load_config()
    assert config_manager.get("test_key") == "test_value"

  async def test_get_nonexistent_key(self, config_manager):
    await config_manager.load_config()
    assert config_manager.get("nonexistent_key") is None
    assert config_manager.get("nonexistent_key", "default") == "default"

  async def test_start_stop(self, config_manager):
    # await config_manager.start()
    assert config_manager._watch_task is not None
    assert not config_manager._watch_task.done()

    await config_manager.stop()
    assert config_manager._watch_task.done()

  async def test_reload_callback(self, tmp_path):
    config_file = tmp_path / "test_config.yaml"
    config_data = {"test_key": "test_value"}
    with open(config_file, 'w') as f:
      yaml.dump(config_data, f)

    callback_called = False
    callback_config = None

    def on_reload(config):
      nonlocal callback_called, callback_config
      callback_called = True
      callback_config = config

    manager = AsyncConfigManager(str(config_file), on_reload=on_reload)
    await manager.load_config()

    assert callback_called
    assert callback_config == {"test_key": "test_value"}

  async def test_async_reload_callback(self, tmp_path):
    config_file = tmp_path / "test_config.yaml"
    config_data = {"test_key": "test_value"}
    with open(config_file, 'w') as f:
      yaml.dump(config_data, f)

    callback_called = False
    callback_config = None

    async def on_reload(config):
      nonlocal callback_called, callback_config
      callback_called = True
      callback_config = config

    manager = AsyncConfigManager(str(config_file), on_reload=on_reload)
    await manager.load_config()

    assert callback_called
    assert callback_config == {"test_key": "test_value"}

  async def test_invalid_config_file(self, tmp_path):
    config_file = tmp_path / "invalid_config.yaml"
    with open(config_file, 'w') as f:
      f.write("invalid: yaml: content:")

    manager = AsyncConfigManager(str(config_file))
    try:
      await manager.load_config()
    except yaml.scanner.ScannerError:
      assert True

  async def test_missing_config_file(self, tmp_path):
    config_file = tmp_path / "nonexistent.yaml"
    manager = AsyncConfigManager(str(config_file))
    try:
      await manager.load_config()
    except FileNotFoundError:
      assert True
