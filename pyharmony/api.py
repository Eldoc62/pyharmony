
"""API class to interact with Logitech Harmony devices."""

import asyncio
import logging

from pyharmony import client as harmony_client

HarmonyClient = harmony_client.HarmonyClient
HarmonySyncInAsyncError = harmony_client.HarmonySyncInAsyncError

logger = logging.getLogger(__name__)

DEFAULT_RETRIES = 2
DEFAULT_TIMEOUT = 5

class HarmonyAPI():
    """Harmony class to interact with Harmony device.

    Args:
        loop (Optional):
            asyncio event loop. Optional, defaults to current event loop

        ip_address (Optional):
            IP address (or hostname) of the Harmony Hub. If not provided then
            needs to be provided on explicit connect

        port (Optional, DEFAULT=5222):
            Port for Harmony Hub.

        timeout (Optional, DEFAULT=5):
            Timeout in seconds when sending requests.

        retries (Optional, DEFAULT=2):
            Number of retries on failure before returning a error.

    Returns:
        HarmonyAPI object
    """

    def __init__(self, loop=None, ip_address=None, port=None, timeout=None,
                 retries=None):
        self._timeout = timeout if timeout else DEFAULT_TIMEOUT
        self._retries = retries if retries else DEFAULT_RETRIES
        self._loop = loop if loop else asyncio.get_event_loop()

        self._harmonyclient = HarmonyClient(ip_address=ip_address, port=port)

        harmony_client.logger.setLevel(logging.getLevelName(
            logger.getEffectiveLevel()
        ))

    def _run_in_loop_now(self, name, func):
        # Get current loop, creates loop if none exist.
        loop = asyncio.get_event_loop()

        func_task = asyncio.ensure_future(func)
        if loop.is_running():
            # We're in a loop, task was added and we're good.
            logger.debug("Task %s added to loop", name)
            return func_task

        # We're not in a loop, execute it.
        logger.debug("Executing task %s", name)
        loop.run_until_complete(func_task)
        return func_task

    def connect(self, Block=True, ip_address=None, port=None):
        """Connect to Harmony Hub.

        Args:
            Block (Optional, DEFAULT=False):
                True: Task will block execution of calling task till complete
                      once awaited on.
                False: Task will return future instead when awaited on.
                       This allows for connect request to be send but
                       result of connect request can be checked later.

            ip_address (Optional):
                IP address (or hostname) for Harmony HUB to override IP
                address provided during initialization

            port (Optional):
                Port for Harmony Hub to override port provided during
                initialization

        Returns:
            Block=True: Boolean
            Block=False: Future that will have Boolean as its result

        Raises:
              Any exception except for timeout
        """
        func = self._harmonyclient.async_connect(ip_address=ip_address,
                                                 port=port, Block=Block)

        return self._run_in_loop_now('connect', func)

    def disconnect(self, Block=True):
        """Disconnect from Harmony Hub.

        Args:
            Block (Optional):
                True: Task will block execution of calling task till complete
                      once awaited on.
                False: Task will return future instead when awaited on.
                       This allows for disconnect request to be send but
                       result of disconnect request can be checked later.

        Returns:
            Block=True: Boolean
            Block=False: Future that will have Boolean as its result

        Raises:
              Any exception except for timeout
        """

        func = self._harmonyclient.async_disconnect(Block=Block)

        return self._run_in_loop_now('disconnect', func)

    def get_config(self, Block=True):
        """Retrieve configuration from Harmony

        Args:
            Block:
                True: Task will block execution of calling task till complete
                      once awaited on.
                False: Task will return future instead when awaited on.
                       This allows for disconnect request to be send but
                       result of disconnect request can be checked later.

        Returns:
             Future: Future result is a boolean.

        Raises:
              Any exception except for timeout
        """
        func = self._harmonyclient.async_get_config(Block=Block)

        return self._run_in_loop_now('get_config', func)

    def get_current_activity(self, Block=True):
        """Retrieve configuration from Harmony

        Args:
            Block:
                True: Task will block execution of calling task till complete
                      once awaited on.
                False: Task will return future instead when awaited on.
                       This allows for disconnect request to be send but
                       result of disconnect request can be checked later.

        Returns:
             Future: Future result is a boolean.

        Raises:
              Any exception except for timeout
        """
        func = self._harmonyclient.async_get_current_activity(Block=Block)

        return self._run_in_loop_now('get_current_activity', func)

    def start_activity(self, Block=True, activity_id=-1):
        """Retrieve configuration from Harmony

        Args:
            Block:
                True: Task will block execution of calling task till complete
                      once awaited on.
                False: Task will return future instead when awaited on.
                       This allows for disconnect request to be send but
                       result of disconnect request can be checked later.

            activity_id (Optional, DEFAULT=-1):
                Activity ID to start

        Returns:
             Future: Future result is a boolean.

        Raises:
              Any exception except for timeout
        """
        func = self._harmonyclient.async_start_activity(
            Block=Block, activity_id=activity_id)

        return self._run_in_loop_now('start_activity', func)

    def sync(self, Block=True):
        """Perform synchronization between Harmony Hub and Web Service

        Args:
            Block:
                True: Task will block execution of calling task till complete
                      once awaited on.
                False: Task will return future instead.

        Returns:
             Future: Future result is a boolean.

        Raises:
              Any exception except for timeout
        """
        func = self._harmonyclient.async_sync(Block=Block)

        return self._run_in_loop_now('sync', func)

    def change_channel(self, Block=True, channel=None):
        """Change the channel

        Args:
            Block:
                True: Task will block execution of calling task till complete
                      once awaited on.
                False: Task will return future instead when awaited on.

            channel (Required):
                Channel to switch to
        Returns:
             Future: Future result is a boolean.

        Raises:
              Any exception except for timeout
        """
        func = self._harmonyclient.async_change_channel(Block=Block,
                                                        channel=channel)

        return self._run_in_loop_now('change_channel', func)

    def send_command(self, Block=True, device=None,
                                 command=None, command_delay=0):
        """Sned provided command to device

        Args:
            Block:
                True: Task will block execution of calling task till complete
                      once awaited on.
                False: Task will return future instead when awaited on.

            device (Required):
                Device ID to send command to

            command (Required):
                Command that devices has to be send to

            command_delay (Optional, DEFAULT=0)
                Delay between press and release for command.

        Returns:
             Future: Future result is a boolean.

        Raises:
              Any exception except for timeout
        """
        func = self._harmonyclient.async_send_command(
            Block=Block, device=device, command=command,
            command_delay=command_delay)

        return self._run_in_loop_now('send_command', func)
