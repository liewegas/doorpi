#!/usr/bin/env python

import argparse
import asyncio
import logging
import os

import hangups
import appdirs

import RPi.GPIO as GPIO


class Doorpi:
    def __init__(self):
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(10, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setup(11, GPIO.IN, pull_up_down=GPIO.PUD_DOWN)
        GPIO.setmode(GPIO.BOARD)
        GPIO.setup(7, GPIO.OUT)
        self.client = None
        self.last_status = None
        self.subs = set()

    def get_garage_status(self):
        top = GPIO.input(10)
        bottom = GPIO.input(11)
        if top == GPIO.HIGH:
            if bottom == GPIO.LOW:
                status = 'OPEN'
            else:
                status = 'ERROR (both open and closed?)'
        else:
            if bottom == GPIO.HIGH:
                status = 'CLOSED'
            else:
                status = 'PARTIALLY-OPEN'
#        print('....Door is %s' % status)
        return status

    async def push_garage_button(self):
        print('Pushing garage button...', end='')
        GPIO.output(7, True)
        await asyncio.sleep(.5)
        GPIO.output(7, False)
        print('done.')

    async def on_event(self, conv_event):
        if isinstance(conv_event, hangups.ChatMessageEvent):
            print('conv %s received chat message "%s" from %s' % (
                conv_event.conversation_id,
                conv_event.text,
                conv_event.user_id.chat_id))
            cmd = conv_event.text.lower()
            if cmd == 'status':
                status = self.get_garage_status()
                await self.send_message(conv_event.conversation_id, status)
            elif cmd == 'push':
                await self.push_garage_button()
            elif cmd == 'open':
                if self.get_garage_status() != 'OPEN':
                    await self.push_garage_button()
            elif cmd == 'close':
                if self.get_garage_status() != 'CLOSED':
                    await self.push_garage_button()
            elif cmd == 'sub':
                self.subs.add(conv_event.conversation_id)
            elif cmd == 'unsub':
                if conv_event.conversation_id in self.subs:
                    self.subs.remove(conv_event.conversation_id)
            elif cmd == 'lssubs':
                await self.send_message(
                    conv_event.conversation_id,
                    'Subs are %s' % self.subs,
                )
            elif cmd == 'whoami':
                await self.send_message(
                    conv_event.conversation_id,
                    'You are %s' % conv_event.conversation_id
                )
                    

    async def main(self, args):
        print('Loading conversation list...')
        user_list, conv_list = (
            await hangups.build_user_conversation_list(self.client)
        )
        conv_list.on_event.add_observer(self.on_event)

        print('Waiting for chat messages...')
        while True:
#            print('tick')
            status = self.get_garage_status()
            if status != self.last_status:
                print('Garage door is now %s' % status)
                self.last_status = status
                for sub in self.subs:
                    await self.send_message(sub, status)

            await asyncio.sleep(1)

    async def send_message(self, conv, msg):
        print('Sending "%s" to %s...' % (msg, conv), end='')
        request = hangups.hangouts_pb2.SendChatMessageRequest(
            request_header=self.client.get_request_header(),
            event_request_header=hangups.hangouts_pb2.EventRequestHeader(
                conversation_id=hangups.hangouts_pb2.ConversationId(
                    id=conv
                ),
                client_generated_id=self.client.get_client_generated_id(),
            ),
            message_content=hangups.hangouts_pb2.MessageContent(
                segment=[
                    hangups.ChatMessageSegment(msg).serialize()
                ],
            ),
        )
        await self.client.send_chat_message(request)
        print('done.')

    
    

###########

def _get_parser(extra_args):
    """Return ArgumentParser with any extra arguments."""
    parser = argparse.ArgumentParser(
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    dirs = appdirs.AppDirs('hangups', 'hangups')
    default_token_path = os.path.join(dirs.user_cache_dir, 'refresh_token.txt')
    parser.add_argument(
        '--token-path', default=default_token_path,
        help='path used to store OAuth refresh token'
    )
    parser.add_argument(
        '-d', '--debug', action='store_true',
        help='log detailed debugging messages'
    )
    for extra_arg in extra_args:
        parser.add_argument(extra_arg, required=True)
    return parser

async def _async_main(example_coroutine, client, args):
    """Run the example coroutine."""
    # Spawn a task for hangups to run in parallel with the example coroutine.
    task = asyncio.ensure_future(client.connect())

    # Wait for hangups to either finish connecting or raise an exception.
    on_connect = asyncio.Future()
    client.on_connect.add_observer(lambda: on_connect.set_result(None))
    done, _ = await asyncio.wait(
        (on_connect, task), return_when=asyncio.FIRST_COMPLETED
    )
    await asyncio.gather(*done)

    # Run the example coroutine. Afterwards, disconnect hangups gracefully and
    # yield the hangups task to handle any exceptions.
    try:
        await example_coroutine(args)
    except asyncio.CancelledError:
        pass
    finally:
        await client.disconnect()
        await task

if __name__ == '__main__':
    extra_args = []
    args = _get_parser(extra_args).parse_args()
    logging.basicConfig(level=logging.DEBUG if args.debug else logging.WARNING)

    doorpi = Doorpi()
    # Obtain hangups authentication cookies, prompting for credentials from
    # standard input if necessary.
    cookies = hangups.auth.get_auth_stdin(args.token_path)
    doorpi.client = hangups.Client(cookies)
    loop = asyncio.get_event_loop()
    task = asyncio.ensure_future(_async_main(doorpi.main, doorpi.client, args),
                                 loop=loop)

    try:
        loop.run_until_complete(task)
    except KeyboardInterrupt:
        task.cancel()
        loop.run_until_complete(task)
    finally:
        loop.close()

