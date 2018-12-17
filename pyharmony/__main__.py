#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""Module for querying and controlling Logitech Harmony devices."""

import argparse
import asyncio
import json
import logging

import pyharmony
import pyharmony.api
import pyharmony.client

# from pyharmony import client as harmony_client
from pyharmony.api import HarmonyAPI
from pyharmony.client import HarmonyClient as HarmonyClient

from pyharmony import api as harmony_api
from pyharmony import client as harmony_client
from pyharmony import discovery as harmony_discovery

import sys

logger = logging.getLogger(__name__)
logger.setLevel(logging.ERROR)

# Trim down log file spam
logging.getLogger('slixxmpp').setLevel(logging.CRITICAL)
logging.getLogger('requests').setLevel(logging.CRITICAL)
logging.getLogger('urllib3').setLevel(logging.CRITICAL)
logging.getLogger('pyharmony').setLevel(logging.CRITICAL)

shutdown_flag_is_set = False

def pprint(obj):
    """Pretty JSON dump of an object."""
    print(json.dumps(obj, sort_keys=True, indent=4, separators=(',', ': ')))


async def get_client(ip, port, activity_callback=None):
    """Connect to the Harmony and return a Client instance.

    Args:
        harmony_ip (str): Harmony hub IP address
        harmony_port (str): Harmony hub port
        activity_callback (function): Function to call when the current
                                      activity has changed.

    Returns:
        object: Authenticated client instance.
    """

    client = await harmony_client.create_and_connect_client(
        ip, port, activity_callback)
    return client


# Functions for use when module is imported by Home Assistant
async def ha_get_client(ip, port):
    """Connect to the Harmony and return a Client instance.

    Args:
        ip (str): Harmony hub IP address
        port (str): Harmony hub port
        token (str): Session token obtained from hub

    Returns:
        object: Authenticated client instance.
    """
    client = await harmony_client.create_and_connect_client(ip, port)
    return client


async def ha_get_config(ip, port):
    """Connects to the Harmony and generates a dictionary containing all
    activites and commands programmed to hub.

    Args:
        email (str):  Email address used to login to Logitech service
        password (str): Password used to login to Logitech service
        ip (str): Harmony hub IP address
        port (str): Harmony hub port

    Returns:
        Dictionary containing Harmony device configuration
    """
    client = await ha_get_client(ip, port)
    config = await client.get_config()
    client.disconnect(send_close=True)
    return config


def ha_write_config_file(config, path):
    """Connects to the Harmony huband generates a text file containing all

    activities and commands programmed to hub.

    Args:
        config (dict): Dictionary object containing configuration information
                       obtained from function ha_get_config
        path (str): Full path to output file

    Returns:
        True
    """
    with open(path, 'w+', encoding='utf-8') as file_out:
        file_out.write('Activities\n')
        for activity in config['activity']:
            file_out.write('  ' + activity['id'] + ' - ' + activity['label'] +
                           '\n')

        file_out.write('\nDevice Commands\n')
        for device in config['device']:
            file_out.write('  ' + device['id'] + ' - ' + device['label'] +
                           '\n')
            for controlGroup in device['controlGroup']:
                for function in controlGroup['function']:
                    action = json.loads(function['action'])
                    file_out.write('    ' + action['command'] + '\n')
    return True


def ha_get_activities(config):
    """Connects to the Harmony hub and returns configured activities.

    Args:
        config (dict): Dictionary object containing configuration information
                       obtained from function ha_get_config

    Returns:
        Dictionary containing activity label and ID number.
    """
    activities = {}
    for activity in config['activity']:
        activities[activity['label']] = activity['id']
    if activities != {}:
        return activities
    else:
        logger.error('Unable to retrieve hub\'s activities')
        return activities


async def ha_get_current_activity(config, ip, port):
    """Returns Harmony hub's current activity.

    Args:
        token (str): Session token obtained from hub
        config (dict): Dictionary object containing configuration information
                       obtained from function ha_get_config
        ip (str): Harmony hub IP address
        port (str): Harmony hub port

    Returns:
        String containing hub's current activity.
    """
    client = await ha_get_client(ip, port)
    current_activity_id = await client.get_current_activity()
    client.disconnect(send_close=True)
    activity = [x for x in config['activity']
                if int(x['id']) == current_activity_id][0]
    if type(activity) is dict:
        return activity['label']
    else:
        logger.error('Unable to retrieve current activity')
        return 'Unknown'


async def ha_start_activity(ip, port, config, activity):
    """Connects to Harmony Hub and starts an activity

    Args:
        token (str): Session token obtained from hub
        ip (str): Harmony hub IP address
        port (str): Harmony hub port
        config (dict): Dictionary object containing configuration information
                       obtained from function ha_get_config
        activity (str): Activity ID or label to start

    Returns:
        True if activity started, otherwise False
    """
    client = await ha_get_client(ip, port)
    status = False

    if (activity.isdigit()) or (activity == '-1'):
        status = await client.start_activity(activity)
        client.disconnect(send_close=True)
        if status:
            return True
        else:
            logger.info('Activity start failed')
            return False

    # provided activity string needs to be translated to activity ID from
    # config
    else:
        activities = config['activity']
        labels_and_ids = dict([(a['label'], a['id']) for a in activities])
        matching = [label for label in list(labels_and_ids.keys())
                    if activity.lower() in label.lower()]
        if len(matching) == 1:
            activity = matching[0]
            logger.info('Found activity named %s (id %s)',
                        activity, labels_and_ids[activity])
            status = await client.start_activity(labels_and_ids[activity])

    client.disconnect(send_close=True)
    if status:
        return True
    else:
        logger.error('Unable to find matching activity, start failed %s',
                     ' '.join(activity))
        return False


async def ha_power_off(ip, port):
    """Power off Harmony Hub.

    Args:
        token (str): Session token obtained from hub
        ip (str): Harmony hub IP address
        port (str): Harmony hub port

    Returns:
        True if PowerOff activity started, otherwise False

    """
    client = await ha_get_client(ip, port)
    status = await client.power_off()
    client.disconnect(send_close=True)
    if status:
        return True
    else:
        logger.error('Power Off failed')
        return False


async def ha_send_command(ip, port, device, command, repeat_num=1,
                          delay_secs=0.4, command_delay=0):
    """Connects to the Harmony and send a simple command.

    Args:
        token (str): Session token obtained from hub
        ip (str): Harmony hub IP address
        port (str): Harmony hub port
        device (str): Device ID from Harmony Hub configuration to control
        command (str): Command from Harmony Hub configuration to control
        repeat_num (int) : Number of times to repeat the command. Defaults to 1
        delay_secs (float): Delay between sending repeated commands. Not used
                            if only sending a single command. Defaults to 0.4
                            seconds
        command_delay (float): Delay between 'press' and 'release' for the
                               command. Defaults to 0

    Returns:
        Completion status
    """
    client = await ha_get_client(ip, port)
    for i in range(repeat_num):
        await client.send_command(device, command, command_delay)
        await asyncio.sleep(delay_secs)

    await asyncio.sleep(1)
    client.disconnect(send_close=True)
    return 0


async def ha_send_commands(ip, port, device, commands, repeat_num=1,
                           delay_secs=0.4, command_delay=0):
    """Connects to the Harmony and sends multiple simple commands.

    Args:
        token (str): Session token obtained from hub
        ip (str): Harmony hub IP address
        port (str): Harmony hub port
        device (str): Device ID from Harmony Hub configuration to control
        commands (list of str): List of commands from Harmony Hub configuration
                                to send
        repeat_num (int) : Number of times to repeat the list of commands.
                           Defaults to 1
        delay_secs (float): Delay between sending commands. Defaults to 0.4
                            seconds
        command_delay (float): Delay between 'press' and 'release' for the
                               commands. Defaults to 0

    Returns:
        Completion status
    """
    client = await ha_get_client(ip, port)
    for i in range(repeat_num):
        for command in commands:
            await client.send_command(device, command, command_delay)
            await asyncio.sleep(delay_secs)

    await asyncio.sleep(1)
    client.disconnect(send_close=True)
    return 0


async def ha_sync(ip, port):
    """Syncs Harmony hub to web service.
    Args:
        ip (str): Harmony hub IP address
        port (str): Harmony hub port

    Returns:
        Completion status
    """
    client = await ha_get_client(ip, port)
    await client.sync()
    client.disconnect(send_close=True)
    return 0


async def ha_change_channel(ip, port, channel):
    client = await ha_get_client(ip, port)
    status = await client.change_channel(channel)
    client.disconnect(send_close=True)
    if status:
        return True
    else:
        logger.error('Unable to change the channel')
        return False


def ha_discover(scan_attempts, scan_interval):
    """Discovers hubs on local network.
    Args:
        scan_attempts (int): Number of times to scan the network
        scan_interval (int): Seconds between running each network scan

    Returns:
        List of config info for any hubs found
    """
    hubs = harmony_discovery.discover(scan_attempts, scan_interval)
    return hubs


# Functions for use on command line
async def show_detailed_config(args):
    """Connects to the Harmony and return current configuration.

    Args:
        args (argparse): Argparse object containing required variables from
                         command line

    """

    client = HarmonyClient(ip_address=args.harmony_ip, port=args.harmony_port)
    if not client:
        return

    config = await client.get_config()
    disconnect_result = client.async_disconnect()
    pprint(config)
    await disconnect_result

async def show_config(args):
    """Connects to the Harmony and return current configuration.

    Args:
        args (argparse): Argparse object containing required variables from
                         command line

    """

    # When Block is true, execute call till completion and result is returned
    # When Block is false, execute for sending the request and then return
    # with a future. Later on this future can then be awaited up on get
    # result from the call.

    client = HarmonyAPI(ip_address=args.harmony_ip, port=args.harmony_port)
    if not client:
        return

    # Retrieve the configuration
    logger.debug("Get config")
    config = await client.get_config(True)

    logger.debug("Got configuration")

    # Disconnect
    logger.debug("Perform disconnect")
    disconnect_task = await client.disconnect(False)

    # pprint(config)

    print('Activities\n')
    for activity in config['activity']:
        print('  {0} - {1}\n'.format(activity['id'], activity['label']))

    print('\nDevice Commands\n')
    for device in config['device']:
        print('  {0} - {1}\n'.format(device['id'], device['label']))
        for controlGroup in device['controlGroup']:
            for function in controlGroup['function']:
                action = json.loads(function['action'])
                print('    {0}\n'.format(action['command']))

    logger.debug("Wait for disconnect")
    result = await disconnect_task

async def show_current_activity(args):
    """Returns Harmony hub's current activity.

    Args:
        args (argparse): Argparse object containing required variables from
                         command line

    """
    client = HarmonyAPI(ip_address=args.harmony_ip, port=args.harmony_port)
    if not client:
        return

    # Initiate connect and wait till complete.
    logger.debug("Starting connect")
    await client.connect(True)

    # Start request to retrieve the configuration
    logger.debug("Get config")
    config_task = await client.get_config(False)

    # Start request to current activity
    logger.debug("Starting current activity")
    current_activity_id = await client.get_current_activity(True)

    # Now wait for both requests to complete
    logger.debug("Wait for config")
    config = await config_task

    # Start request already for disconnect
    logger.debug("Start disconnect")
    disconnect_task = await client.disconnect(False)

    if current_activity_id:
        activity = [x for x in config['activity']
                    if int(x['id']) == current_activity_id][0]
        if type(activity) is dict:
            print(activity['label'])
        else:
            logger.error('Unable to retrieve current activity')
            print('Unknown')

    logger.debug("Wait for disconnect")
    result = await disconnect_task


def activity_name(config, activity_id):
    """Looks up an activity in the config, returning its name.

    Args:
        config (dict): Dictionary object containing configuration information
                       obtained from function ha_get_config.
        activity_id (int): Harmony ID of the activity.

    Returns:
        The name of the activity, or None if not found.
    """

    ids_and_labels = dict([(int(a['id']), a['label'])
                          for a in config['activity']])
    return ids_and_labels.get(int(activity_id))


def activity_id(config, activity):
    """Looks up an activity in the config, returning its ID.

    Args:
        config (dict): Dictionary object containing configuration information
                       obtained from function ha_get_config.
        activity (string/int): Harmony name of the activity. Providing an ID
                               returns itself.

    Returns:
        The ID of the activity, or None if not found.
    """

    if activity.isdigit() or activity == '-1':
        if activity_name(config, activity):
            return activity
    labels_and_ids = dict([(a['label'].lower(), int(a['id']))
                          for a in config['activity']])
    return labels_and_ids.get(activity.lower())


async def start_activity(args):
    """Connects to Harmony Hub and starts an activity

    Args:
        args (argparse): Argparse object containing required variables from
                         command line

    """
    client = HarmonyAPI(ip_address=args.harmony_ip, port=args.harmony_port)
    if not client:
        return

    status = False

    if (args.activity.isdigit()) or (args.activity == '-1'):
        status = await client.start_activity(args.activity)
        if status:
            print('Started Actvivity')
        else:
            logger.info('Activity start failed')
    else:
        config = await client.get_config()
        activities = config['activity']
        labels_and_ids = dict([(a['label'], a['id']) for a in activities])
        matching = [label for label in list(labels_and_ids.keys())
                    if args.activity.lower() in label.lower()]
        if len(matching) == 1:
            activity = matching[0]
            logger.info('Found activity named %s (id %s)',
                        activity, labels_and_ids[activity])
            status = await client.start_activity(
                activity_id=labels_and_ids[activity])
        if status:
            print('Started:', args.activity)
        else:
            logger.error('found too many activities! %s',
                         ' '.join(matching))
    await client.disconnect()

async def power_off(args):
    """Power off Harmony Hub.

    Args:
        args (argparse): Argparse object containing required variables from
                         command line

    """
    client = HarmonyClient(ip_address=args.harmony_ip, port=args.harmony_port)
    if not client:
        return
    status = await client.power_off()
    if status:
        print('Powered Off')
    else:
        logger.error('Power off failed')
    await client.disconnect()

async def send_command(args):
    """Connects to the Harmony and send a simple command.

    Args:
        args (argparse): Argparse object containing required variables from
                         command line

    """
    client = HarmonyAPI(ip_address=args.harmony_ip, port=args.harmony_port)
    if not client:
        return

    # Retrieve the configuration
    logger.debug("Send Command")

    for i in range(args.repeat_num):
        result = await client.send_command(
            Block=True, device=args.device_id,
            command=args.command, command_delay=args.hold_secs)
        print('Command Sent')
        await asyncio.sleep(args.delay_secs)

    # Disconnect
    # await result
    logger.debug("Perform disconnect")
    disconnect_task = await client.disconnect(True)


def discover(args):
    hubs = harmony_discovery.discover()
    pprint(hubs)


async def sync(args):
    """Syncs Harmony hub to web service.
    Args:
        args (argparse): Argparse object containing required variables from
                         command line

    Returns:
        Completion status
    """
    client = HarmonyClient(ip_address=args.harmony_ip, port=args.harmony_port)
    if not client:
        return

    await client.sync()
    await client.disconnect()
    print('Sync complete')


async def main(loop):
    """Main method for the script."""
    parser = argparse.ArgumentParser(
        description='Pyharmony - Harmony device control',
        formatter_class=argparse.ArgumentDefaultsHelpFormatter)

    required_flags = parser.add_mutually_exclusive_group(required=True)

    # Required flags go here.
    required_flags.add_argument('--harmony_ip',
                                help='IP Address of the Harmony device.')
    required_flags.add_argument('--discover',
                                action='store_true',
                                help='Scan for Harmony devices.')

    # Flags with default values go here.
    loglevels = dict((logging.getLevelName(level), level)
                     for level in [10, 20, 30, 40, 50])
    parser.add_argument('--harmony_port',
                        required=False,
                        default=5222,
                        type=int,
                        help=('Network port that the Harmony is listening'
                              ' on.'))
    parser.add_argument('--loglevel',
                        default='INFO',
                        choices=list(loglevels.keys()),
                        help='Logging level for all components to '
                             'print to the console.')
    parser.add_argument('--loglevel_harmony',
                        default='WARNING',
                        choices=list(loglevels.keys()),
                        help='Logging level for harmony components to '
                             'print to the console.')
    block_parser = parser.add_mutually_exclusive_group(required=False)
    block_parser.add_argument('--block',
                              dest='block',
                              action='store_true',
                              help='Have each call complete before '
                                   'continuing.'
                    )
    block_parser.add_argument('--no-block',
                              dest='block',
                              action='store_false',
                              help='Initiate all requests and then '
                                   'complete.'
                              )
    parser.set_defaults(block=False)

    subparsers = parser.add_subparsers()

    show_config_parser = subparsers.add_parser(
        'show_config', help='Print the Harmony device configuration.')
    show_config_parser.set_defaults(func=show_config)

    show_detailed_config_parser = subparsers.add_parser(
        'show_detailed_config', help='Print the detailed Harmony device'
        ' configuration.')
    show_detailed_config_parser.set_defaults(func=show_detailed_config)

    show_activity_parser = subparsers.add_parser(
        'show_current_activity', help='Print the current activity config.')
    show_activity_parser.set_defaults(func=show_current_activity)

    start_activity_parser = subparsers.add_parser(
        'start_activity', help='Switch to a different activity.')
    start_activity_parser.add_argument(
        '--activity', help='Activity to switch to, id or label.')
    start_activity_parser.set_defaults(func=start_activity)

    power_off_parser = subparsers.add_parser(
        'power_off', help='Stop the activity.')
    power_off_parser.set_defaults(func=power_off)

    sync_parser = subparsers.add_parser('sync', help='Sync the harmony.')
    sync_parser.set_defaults(func=sync)

    command_parser = subparsers.add_parser(
        'send_command', help='Send a simple command.')
    command_parser.add_argument(
        '--device_id',
        help='Specify the device id to which we will send the command.')
    command_parser.add_argument(
        '--command', help='IR Command to send to the device.')
    command_parser.add_argument(
        '--repeat_num', type=int, default=1,
        help='Number of times to repeat the command. Defaults to 1')
    command_parser.add_argument(
        '--delay_secs', type=float, default=0.4,
        help='Delay between sending repeated commands. Not used if only '
        'sending a single command. Defaults to 0.4 seconds')
    command_parser.add_argument(
        '--hold_secs', type=float, default=0,
        help='Number of seconds to "hold" before releasing. Defaults to 0.4'
        'seconds')
    command_parser.set_defaults(func=send_command)

    args = parser.parse_args()

    logging.basicConfig(
        level=loglevels[args.loglevel],
        format='%(asctime)s:%(levelname)s:\t%(name)s\t%(message)s')

    # harmony_client.logger.setLevel(loglevels[args.loglevel])
    # logging.getLogger('pyharmony').setLevel(loglevels[args.loglevel_harmony])
    # logging.getLogger('pyharmony.api').setLevel(loglevels[
    # args.loglevel_harmony])
    # logging.getLogger('pyharmony.client').setLevel(loglevels[
    # args.loglevel_harmony])
    pyharmony.logger.setLevel(loglevels[args.loglevel_harmony])
    harmony_api.logger.setLevel(loglevels[args.loglevel_harmony])
    harmony_client.logger.setLevel(loglevels[args.loglevel_harmony])
    harmony_discovery.logger.setLevel(loglevels[args.loglevel_harmony])
    logger.setLevel(loglevels[args.loglevel_harmony])

    if args.discover:
        discover(args)
    else:
        coroutine = args.func(args)
        loop = asyncio.get_event_loop()
        task = loop.create_task(coroutine)
        await task

if __name__ == '__main__':
    loop = asyncio.new_event_loop()
    loop.run_until_complete(main(loop=loop))
    while asyncio.all_tasks(loop):
        loop.run_until_complete(asyncio.gather(*asyncio.all_tasks(loop)))
    loop.close()

    sys.exit()
