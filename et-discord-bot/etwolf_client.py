import asyncio
import collections
import logging
import re
import json


class ETGameClientProtocol(asyncio.DatagramProtocol):
    InfoResponseMessage = collections.namedtuple('InfoResponseMessage', ['server_info', 'players_info'])
    PlayerInfo = collections.namedtuple('PlayerInfo', ['score', 'ping', 'name'])

    def __init__(self, loop):
        self.loop = loop
        self.transport = None
        self.message_queue = []
        self._waiter = None

    def connection_made(self, transport):
        self.transport = transport

    def send_message(self, message_parts):
        self.transport.sendto(
            b'\xff\xff\xff\xff' +
            b'\n'.join([part.encode() for part in message_parts]) +
            b'\n'
        )

    def send_getinfo(self):
        self.send_message(['getinfo'])

    def decode_dict(self, raw):
        value = dict()
        raw_list = raw[1:].split('\\')
        for i in range(0, len(raw_list), 2):
            value[raw_list[i]] = raw_list[i+1]
        return value

    def decode_infoResponse(self, message_parts):
        server_info = self.decode_dict(message_parts[1])
        server_info['hostname_plaintext'] = re.sub(r'\^\d', '', server_info['hostname'])
        logging.debug(json.dumps(server_info, indent=4, sort_keys=True))
        # Known values:
        # 'challenge', 'version', 'protocol', 'hostname', 'serverload', 'mapname', 'clients', 'humans', 'sv_maxclients',
        # 'gametype', 'pure', 'game', 'friendlyFire', 'maxlives', 'needpass', 'gamename', 'g_antilag', 'weaprestrict',
        # 'balancedteams'

        players_info = []
        for player_info_raw in message_parts[2:]:
            player_info_dict = re.match(r'(?P<score>\d+) (?P<ping>\d+) "(?P<name>.+)"', player_info_raw).groupdict()
            message.players_info.append(ETGameClientProtocol.PlayerInfo(**player_info_dict))

        return ETGameClientProtocol.InfoResponseMessage(server_info, players_info)

    def datagram_received(self, data, addr):
        try:
            message_parts = data[4:].decode().split('\n')
            message_type = message_parts[0]
        except (KeyError, ValueError, TypeError, UnicodeDecodeError):
            data_repr = data.decode('ASCII', errors='backslashreplace').replace('\n', '\\n')
            logging.warning(f'Unable to parse message, ignoring message. Raw data: "{data_repr}"')
            return

        if message_type == 'infoResponse':
            message = self.decode_infoResponse(message_parts)
        else:
            logging.warning(f'Parsing message of type "{message_type}" not implemented, ignoring message.')
            return

        logging.info(f'Received {message_type}')
        self.message_queue.append((message_type, message))

        # Wake up waiter.
        if self._waiter is not None:
            self._waiter.set_result(None)

    async def wait_for_message(self):
        if self._waiter is not None:
            raise RuntimeError('ETGameClientProtocol.wait_for_message called while another coroutine is already '
                               'waiting.')
        self._waiter = self.loop.create_future()
        try:
            await self._waiter
        finally:
            self._waiter = None

    def error_received(self, exc):
        logging.error(f'ETGameClientProtocol: Error received: {str(exc)}')

    def connection_lost(self, exc):
        logging.error('ETGameClientProtocol: Socket closed')


class ETClient(object):

    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()

    async def get_server_info(self, server, port):
        transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: ETGameClientProtocol(self.loop),
            remote_addr=(server, port)
        )
        protocol.send_getinfo()
        await protocol.wait_for_message()
        message_type, message = protocol.message_queue.pop()
        assert(message_type == 'infoResponse')
        transport.close()
        return message
