#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Client class for connecting to Logitech Harmony devices."""

import asyncio
import json
import time
import re
import slixmpp
from functools import partial
from slixmpp.exceptions import IqTimeout
from slixmpp.xmlstream import ET
from slixmpp.xmlstream.handler.callback import Callback
from slixmpp.xmlstream.matcher import MatchXPath
from slixmpp.xmlstream.matcher.base import MatcherBase
import logging

logger = logging.getLogger(__name__)

HARMONY_DEFAULT_PORT = '5222'
HARMONY_DEFAULT_RETRIES = 2
HARMONY_DEFAULT_TIMEOUT = 5
HARMONY_MIME = 'vnd.logitech.harmony/vnd.logitech.harmony.engine'
HARMONY_NS = 'connect.logitech.com'
HARMONY_USER = 'user@connect.logitech.com/gatorade.'
HARMONY_PASSWORD = 'password'


class HarmonyClient(slixmpp.ClientXMPP):
    """An XMPP client for connecting to the Logitech Harmony devices."""

    def __init__(self, loop=None, ip_address=None, port=None, timeout=None,
                 retries=None):
        self._ip_address = ip_address
        self._port = port if port else HARMONY_DEFAULT_PORT
        self._timeout = timeout if timeout else HARMONY_DEFAULT_TIMEOUT
        self._retries = retries if retries else HARMONY_DEFAULT_RETRIES

        self._event_loop = asyncio.get_event_loop()

        plugin_config = {
            # Enables PLAIN authentication which is off by default.
            'feature_mechanisms': {'unencrypted_plain': True},
        }
        super(HarmonyClient, self).__init__(
            HARMONY_USER, HARMONY_PASSWORD, plugin_config=plugin_config)

        # Set keep-alive to 30 seconds.
        self.whitespace_keepalive_interval = 30

        def handleHarmonyResponse(iq):
            """Change Harmony HUB response type from invalid 'get' to

            'result'."""
            if iq['type'] == 'get':
                iq['type'] = 'result'

        self.register_handler(
            Callback('Harmony Result',
                     MatchXPath('{{{0}}}iq/{{{1}}}oa'.format(self.default_ns,
                                                             HARMONY_NS)),
                     handleHarmonyResponse))



    async def send_request(self, timeout=None, mime=None,
                           request=None, command=None,Block=True,
                           callback=None, type='get'):
        """Send request to Harmony HUB."""
        timeout = self._timeout if timeout is None else timeout
        logger.debug("Timeout : %s", timeout)
        if not self.is_connected():
            # Try to connect, return if unable to connect.
            if not await self.async_connect(
                    ip_address=self._ip_address, port=self._port, Block=True):
                return

        mime = mime if mime else HARMONY_MIME

        if type == 'query':
            iq_stanza = self.make_iq_query()
        elif type == 'set':
            iq_stanza = self.make_iq_set()
        elif type == 'result':
            iq_stanza = self.make_iq_result()
        elif type == 'error':
            iq_stanza = self.make_iq_error()
        else:
            iq_stanza = self.make_iq_get()

        action_cmd = ET.Element('oa')
        action_cmd.attrib['xmlns'] = HARMONY_NS
        action_cmd.attrib['mime'] = '{}?{}'.format(
            mime, request) if request else '{}'.format(mime)
        action_cmd.text = command if command else None
        iq_stanza.set_payload(action_cmd)

        logger.debug("Sending request %s for mime %s", request, mime)
        try:
            if Block:
                try:
                    result = await iq_stanza.send(
                        callback=callback, timeout=timeout)
                except IqTimeout:
                    logger.error('XMPP timeout')
                    result = None
                    pass
            else:
                result = iq_stanza.send(callback=callback,
                                        timeout=timeout)
        except Exception as ex:
            logger.critical('XMPP Exception: %s', ex)
            raise
        return result

    async def async_connect(self, Block=True, ip_address=None, port=None):
        """Connect to Harmony HUB

        Args:
            Block (Optional, DEFAULT=False):
                True: Run till completion and return result.
                False: Executes and then returns future allowing to check
                       connection result later.

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
        loop = asyncio.get_event_loop()
        complete_future = loop.create_future()

        await self._async_perform_connect(future_result=complete_future,
                                          ip_address=ip_address, port=port)

        if Block:
            logger.debug("Waiting for connect to complete")
            return await complete_future

        return complete_future

    async def _async_perform_connect(self, future_result, ip_address=None,
                                     port=None):
        """Connect to Harmony HUB."""
        async def session_start(event):
            logger.debug("Connected to %s on port %s",
                self._ip_address, self._port)
            future_result.set_result(True)

        if self.is_connected():
            await self.async_disconnect(True)

        self._ip_address = ip_address if ip_address else self._ip_address
        self._port = port if port else self._port

        # Return if no IP address.
        if not self._ip_address:
            future_result.set_result(False)
            return future_result

        logger.debug("Initiating connection to %s on port %s",
            self._ip_address, self._port)
        self.add_event_handler('session_start', session_start, disposable=True)
        super(HarmonyClient, self).connect(
            address=(self._ip_address, self._port), disable_starttls=True,
            use_ssl=False)

        return

    async def async_disconnect(self, Block=True):
        """Disconnect from Harmony Hub.

        Args:
            Block (Optional, DEFAULT=False):
                True: Run till completion and return result.
                False: Executes and then returns future allowing to check
                       disconnect result later.

        Returns:
            Block=True: Boolean
            Block=False: Future that will have Boolean as its result

        Raises:
              Any exception except for timeout
        """
        loop = asyncio.get_event_loop()
        complete_future = loop.create_future()

        await self._async_perform_disconnect(future_result=complete_future)

        if Block:
            logger.debug("Waiting for disconnect to complete")
            return await complete_future

        return complete_future

    async def _async_perform_disconnect(self, future_result):
        """Disconnect from Harmony Hub."""

        async def disconnected(event):
            logger.debug("Disconnected from %s on port %s",
                self._ip_address, self._port)
            future_result.set_result(True)

        if not self.is_connected():
            return

        logger.debug("Initiating disconnect from %s on port %s",
            self._ip_address, self._port)
        self.add_event_handler('disconnected', disconnected, disposable=True)
        super(HarmonyClient, self).disconnect()

        return

    async def async_get_config(self, Block=True):
        """Retrieve Harmony Hub configuration

        Args:
            Block (Optional, DEFAULT=False):
                True: Run till completion and return result.
                False: Executes and then returns future allowing to
                       retrieve the configuration result later.

        Returns:
            Block=True: Configuration in json format
            Block=False: Future that will have Configuration in json format
                         as its result

        Raises:
              Any exception except for timeout
        """

        loop = asyncio.get_event_loop()
        complete_future = loop.create_future()

        await self._async_perform_get_config(
            future_result=complete_future, Block=Block)

        if Block:
            logger.debug("Waiting to receive configuration")
            return await complete_future

        return complete_future

    async def _async_perform_get_config(self, future_result, Block=True):
        """Retrieve Harmony Hub configuration."""
        def reply_received(result):
            logger.debug("Configuration received")
            future_result.set_result(self.parse_config(result))

        config = await self.send_request(request='config',
                                         callback=reply_received, Block=Block)

        return config

    def parse_config(self, config):
        """Parse provided  Harmony configuration

        Returns:
            A nested dictionary containing activities, devices, etc."""
        payload = config.get_payload()
        assert len(payload) == 1
        action_cmd = payload[0]
        assert action_cmd.attrib['errorcode'] == '200'
        device_list = action_cmd.text
        return json.loads(device_list)

    async def async_get_current_activity(self, Block=True):
        """Retrieve current activity

        Args:
            Block (Optional):
                True: Run till completion and return result.
                False: Executes and then returns future allowing to
                       retrieve the configuration result later.

        Returns:
            Block=True: Activity ID
            Block=False: Future that will have Activity ID

        Raises:
              Any exception except for timeout
        """

        loop = asyncio.get_event_loop()
        complete_future = loop.create_future()

        await self._async_perform_get_current_activity(
            future_result=complete_future, Block=Block)

        if Block:
            logger.debug("Waiting to receive current activity")
            return await complete_future

        return complete_future

    async def _async_perform_get_current_activity(self,
                                                  future_result, Block=True):
        """Retrieves the current activity ID."""
        def reply_received(result):
            logger.debug("Activity received")
            future_result.set_result(self.parse_current_activity(result))

        activity = await self.send_request(request='getCurrentActivity',
                                         callback=reply_received, Block=Block)

        return activity

    def parse_current_activity(self, activity):
        payload = activity.get_payload()
        assert len(payload) == 1
        action_cmd = payload[0]
        assert action_cmd.attrib['errorcode'] == '200'
        activity = action_cmd.text.split("=")
        return int(activity[1])

    async def async_start_activity(self, Block=True, activity_id=-1):
        """Start an activity

        Args:
            Block (Optional, DEFAULT=False):
                True: Run till completion and return result.
                False: Executes and then returns future allowing to
                       retrieve the configuration result later.

            activity_id (Optional, DEFAULT=-1):
                Activity ID to start

        Returns:
            Block=True: Activity ID
            Block=False: Future that will have Activity ID

        Raises:
              Any exception except for timeout
        """

        loop = asyncio.get_event_loop()
        complete_future = loop.create_future()

        await self._async_perform_start_activity(
            future_result=complete_future, Block=Block,
            activity_id=activity_id)

        if Block:
            logger.debug("Waiting for activity to complete")
            return await complete_future

        return complete_future

    async def _async_perform_start_activity(self, future_result, Block=True,
                                            activity_id=-1):
        """Starts an activity."""
        def reply_received(result):
            logger.debug("Activity started")
            future_result.set_result(self.parse_start_activity(result))

        command = 'activityId={0}:timestamp=0'.format(activity_id)
        activity = await self.send_request(request='runactivity',
                                           callback=reply_received,
                                           Block=Block,
                                           mime = 'harmony.activityengine',
                                           command=command)

        return activity

    def parse_start_activity(self, activity):
            payload = activity.get_payload()
            assert len(payload) == 1
            action_cmd = payload[0]
            logger.debug("Result : %s", action_cmd.text)
            if action_cmd.text is None:
                return True
            else:
                return False

    async def async_sync(self, Block=True):
        """Sync Harmony Hub with Web

        Args:
            Block (Optional, DEFAULT=False):
                True: Run till completion and return result.
                False: Executes and then returns future allowing to
                       retrieve the configuration result later.

        Returns:
            Block=True: Boolean confirming sync is completed
            Block=False: Future that will have Boolean confirming sync
                        is completed
        Raises:
              Any exception except for timeout
        """

        loop = asyncio.get_event_loop()
        complete_future = loop.create_future()

        await self._async_perform_sync(
            future_result=complete_future, Block=Block,
            activity_id=activity_id)

        if Block:
            logger.debug("Waiting for sync to complete")
            return await complete_future

        return complete_future

    async def _async_perform_sync(self, future_result, Block=True):
        """Perform sync between Hub and Web Service"""
        def reply_received(result):
            logger.debug("Activity started")
            future_result.set_result(self.parse_sync(result))

        command = 'activityId={0}:timestamp={1}'.format(
            activity_id, int(time.time()))
        activity = await self.send_request(callback=reply_received,
                                           Block=Block,
                                           mime='setup.sync')

        return activity

    def parse_sync(self, result):
        """Syncs the harmony hub with the web service.
        """
        if result:
            payload = result.get_payload()
            assert len(payload) == 1
            return True

        return False

    async def async_send_command(self, Block=True, device=None,
                                 command=None, command_delay=0):
        """Retrieve current activity

        Args:
            Block (Optional):
                True: Run till completion and return result.
                False: Executes and then returns future allowing to
                       retrieve the configuration result later.

        Returns:
            Block=True: Activity ID
            Block=False: Future that will have Activity ID

        Raises:
              Any exception except for timeout
        """

        loop = asyncio.get_event_loop()
        complete_future = loop.create_future()

        func=self._async_perform_send_command(
            future_result=complete_future, device=device,
            command=command, command_delay=command_delay)
        result = asyncio.ensure_future(func)

        if Block:
            logger.debug("Waiting to receive confirmation on send command")
            await result
            return await complete_future

        return complete_future

    async def _async_perform_send_command(self, future_result, device=None,
                                          command=None, command_delay=0
                                          ):
        if not device or not command:
            future_result.set_result(False)
            return

        send_command = 'action={{"type"::"IRCommand","deviceId"::"{0}",' \
                  '"command"::"{1}"}}:status='.format(device, command)

        logger.debug("Pressing button")
        result1 = await self.send_request(request='holdAction',
                                         Block=False,
                                         command=send_command + 'press',
                                         type='query')
        logger.debug("Button pressed")

        if command_delay > 0:
            await asyncio.sleep(command_delay)

        logger.debug("Releasing button")
        result2 = await self.send_request(request='holdAction',
                                         Block=False,
                                         command=send_command + 'release',
                                         type='query')
        logger.debug("Button released")

        future_result.set_result(True)

        return

    async def send_command(self, device, command, command_delay=0, Block=True):
        """Send a simple command to the Harmony Hub.

        Args:
            device_id (str): Device ID from Harmony Hub configuration to
                             control
            command (str): Command from Harmony Hub configuration to control
            command_delay (int): Delay in seconds between sending the press
                                 command and the release command.

        Returns:
            None if successful
        """

        # Send pressing the button.
        result = await self.send_request(
            request='holdAction',
            command=command + 'press'
            )

        if not result:
            return

        await asyncio.sleep(command_delay)

        # Send releasing the button.
        result = await self.send_request(
            request='holdAction',
            command=command + 'release',
            timeout=0)

        return result

    async def async_change_channel(self, Block=False, channel=None):
        """Retrieve current activity

        Args:
            Block (Optional):
                True: Run till completion and return result.
                False: Executes and then returns future allowing to
                       retrieve the configuration result later.

        Returns:
            Block=True: Activity ID
            Block=False: Future that will have Activity ID

        Raises:
              Any exception except for timeout
        """

        loop = asyncio.get_event_loop()
        complete_future = loop.create_future()

        await self._async_change_channel(
            future_result=complete_future, Block=Block, channel=channel)

        if Block:
            logger.debug("Waiting to receive confirmation on change channel")
            return await complete_future

        return complete_future

    async def async_perform_change_channel(self, future_result, Block=True,
                                           channel=None):
        """Changes a channel.
        Args:
            channel: Channel number
        Returns:
          An HTTP 200 response (hopefully)
        """
        def reply_received(result):
            logger.debug("Activity started")
            future_result.set_result(self.parse_change_channel(result))

        send_command = 'channel={0}:timestamp=0'.format(channel)
        activity = await self.send_request(request='changeChannel',
                                           callback=reply_received,
                                           Block=Block,
                                           mime='setup.sync',
                                           command=send_command)

        return activity

    def parse_change_channel(self, result):
        payload = result.get_payload()
        assert len(payload) == 1
        action_cmd = payload[0]
        if action_cmd.text is None:
            return True

        return False

    async def power_off(self, Block=True):
        """Turns the system off if it's on, otherwise it does nothing.

        Returns:
            True if the system becomes or is off
        """
        activity = await self.get_current_activity()
        if activity != -1:
            if not Block:
                return self.start_activity(-1, Block=Block)
            return await self.start_activity(-1)
        else:
            if not Block:
                result = self._event_loop.create_future()
                result.set_result(True)
                return result

            return True

    def register_activity_callback(self, activity_callback):
        """Register a callback that is executed on activity changes."""
        def hub_event(xml):
            match = re.search('activityId=(-?\d+)', xml.get_payload()[0].text)
            activity_id = match.group(1)
            if activity_id is not None:
                activity_callback(int(activity_id))

        self.registerHandler(Callback(
            'Activity Finished', MatchHarmonyEvent('startActivityFinished'),
            hub_event))


class MatchHarmonyEvent(MatcherBase):
    def match(self, xml):
        """Check if a stanza matches the Harmony event criteria."""
        payload = xml.get_payload()
        if len(payload) == 1:
            msg = payload[0]
            if msg.tag == '{connect.logitech.com}event' and\
               msg.attrib['type'] == 'harmony.engine?' + self._criteria:
                return True
        return False

class HarmonyError(Exception):
        pass

class HarmonySyncInAsyncError(HarmonyError):
        pass

async def create_and_connect_client(ip_address, port, activity_callback=None,
                                    connect_attempts=5):

    """Creates a Harmony client and initializes session.

    Args:
        ip_address (str): Harmony device IP address
        port (str): Harmony device port
        activity_callback (function): Function to call when the current
                                      activity has changed.


    Returns:
        A connected HarmonyClient instance
    """
    client = HarmonyClient(ip_address, port)
    await client.connect()
#    client.process(block=False)
    if activity_callback:
        client.register_activity_callback(activity_callback)
#    while not client.sessionstarted:
#        await asyncio.sleep(0.1)
    return client
