import asyncio
import collections
import datetime
import json
import logging
import re

from async_timeout import timeout

ET_SERVER_RESPONSE_TIMEOUT = datetime.timedelta(seconds=3)


class ETClientProtocol(asyncio.DatagramProtocol):

    PROTOCOL_VERSION = 84

    def __init__(self, loop):
        self.loop = loop
        self.transport = None
        self.message_queue = []
        self._waiter = None

    def connection_made(self, transport):
        self.transport = transport

    def send_message(self, data):
        self.transport.sendto(
            b'\xff\xff\xff\xff' + data
        )

    def send_getservers(self):
        self.send_message(f'getservers {ETClientProtocol.PROTOCOL_VERSION}'.encode())

    def send_getinfo(self):
        self.send_message('getinfo\n'.encode())

    def decode_dict(self, raw):
        value = dict()
        raw_list = raw[1:].split('\\')
        for i in range(0, len(raw_list), 2):
            value[raw_list[i]] = raw_list[i+1]
        return value

    def decode_getserversResponse(self, data):
        servers = []
        for server_raw in data.split('\\'):
            if server_raw == b'EOT':
                break
            unpacked_ip_and_port = struct.unpack('!BBBBH', server_raw)
            ip = '.'.join(map(str, unpacked_ip_and_port[:-1]))
            port = int(unpacked_ip_and_port[-1])
            servers.append((ip, port))
        return servers

    def decode_infoResponse(self, data):
        message_parts = data.decode().split('\n')
        host_info = self.decode_dict(message_parts[1])

        host_info['hostname_plaintext'] = re.sub(r'\^\d', '', host_info['hostname'])
        logging.debug(json.dumps(host_info, indent=4, sort_keys=True))
        # Known values:
        # 'challenge', 'version', 'protocol', 'hostname', 'serverload', 'mapname', 'clients', 'humans', 'sv_maxclients',
        # 'gametype', 'pure', 'game', 'friendlyFire', 'maxlives', 'needpass', 'gamename', 'g_antilag', 'weaprestrict',
        # 'balancedteams'

        host_info['players'] = []
        for player_info_raw in message_parts[2:]:
            player_info_dict = re.match(r'(?P<score>\d+) (?P<ping>\d+) "(?P<name>.+)"', player_info_raw).groupdict()
            host_info['players'].append(player_info_dict)

        return host_info

    def datagram_received(self, data, _):
        data = data[4:]  # drop \0xff\0xff\0xff\0xf

        if data.startswith('infoResponse'):
            message_type = 'infoResponse'
            message_content = self.decode_infoResponse(data)
        elif data.startswith('getserversResponse'):
            message_type = 'getserversResponse'
            message_content = self.decode_getserversResponse(data)
        else:
            logging.warning(f'Parsing message with first bytes "{data[:20]}" not implemented, ignoring message.')
            return

        logging.debug(f'Received {message_type}')
        self.message_queue.append((message_type, data_content))

        # Wake up waiter.
        if self._waiter is not None:
            self._waiter.set_result(None)

    async def wait_for_message(self):
        if self._waiter is not None:
            raise RuntimeError('ETClientProtocol.wait_for_message called while another coroutine is already '
                               'waiting.')
        self._waiter = self.loop.create_future()
        try:
            await self._waiter
        finally:
            self._waiter = None

    def error_received(self, exc):
        logging.error(f'ETClientProtocol: Error received: {str(exc)}')

    def connection_lost(self, exc):
        logging.debug('ETClientProtocol: Socket closed')


class ETClient(object):

    MASTER_SERVER_HOST = 'etmaster.idsoftware.com'
    MASTER_SERVER_PORT = 27950

    def __init__(self, loop=None):
        self.loop = loop or asyncio.get_event_loop()

    async def get_server_list(self):
        transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: ETClientProtocol(self.loop),
            remote_addr=(socket.gethostbyname(ETClient.MASTER_SERVER_HOST), ETClient.MASTER_SERVER_PORT)
        )
        protocol.send_getservers()
        try:
            async with timeout(ET_SERVER_RESPONSE_TIMEOUT.total_seconds()):
                while True:
                    await protocol.wait_for_message()
        finally:
            transport.close()

        servers = []
        for message_type, servers_part in protocol.message_queue:
            if message_type != 'getserversResponse':
                raise ValueError()
            servers.extend(servers_part)

        return servers

    async def get_server_info(self, server, port):
        transport, protocol = await self.loop.create_datagram_endpoint(
            lambda: ETClientProtocol(self.loop),
            remote_addr=(server, port)
        )
        protocol.send_getinfo()
        try:
            async with timeout(ET_SERVER_RESPONSE_TIMEOUT.total_seconds()):
                await protocol.wait_for_message()
                message_type, message_content = protocol.message_queue.pop()
                if message_type != 'infoResponse':
                    raise ValueError()
                return message_content
        finally:
            logging.info('closing transport!')
            transport.close()
