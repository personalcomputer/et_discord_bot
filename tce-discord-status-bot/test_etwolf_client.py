import asyncio
import random
import logging

from etwolf_client import ETClient


class MockETServerProtocol(asyncio.DatagramProtocol):

    def __init__(self, *args, **kwargs):
        self.received_bytes = b''
        self.transport = None
        super().__init__(*args, **kwargs)

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        message_type = data[4:data.find(b'\n')]
        if message_type == b'getinfo':
            get_info_response = 'infoResponse\n\\challenge\\xxx\\version\\ET Legacy v2.75 linux-i386 Sep 13 2016\\protocol\\84\\hostname\\^9gg.^4ill^7wie^1ckz^9.net^8 #OBJ^6 { ^5le frag courtois^6 }\\serverload\\0\\mapname\\obj_stadtrand\\clients\\0\\humans\\0\\sv_maxclients\\10\\gametype\\5\\pure\\1\\game\\tcetest\\friendlyFire\\0\\maxlives\\0\\needpass\\0\\gamename\\et\\g_antilag\\1\\weaprestrict\\100\\balancedteams\\1'
            self.transport.sendto(b'\xff\xff\xff\xff'+get_info_response.encode(), addr)
        self.received_bytes += data


class TestServerStatus(object):

    def test_full(self):
        server_port = random.randint(47700, 48000)

        loop = asyncio.get_event_loop()
        listen = loop.create_datagram_endpoint(MockETServerProtocol, local_addr=('127.0.0.1', server_port))
        transport, protocol = loop.run_until_complete(listen)
        client = ETClient()
        raw_info = loop.run_until_complete(client.get_server_info('127.0.0.1', server_port))

        assert(int(raw_info.server_info['humans']) == 0)
        assert('illwieckz' in raw_info.server_info['hostname_plaintext'])

# import mock

# from bot import TCEBot
# class TCEBotTestCase(object):

#     def test_reply_dm(self):
#         with mock.patch('DiscordClient'):
#             bot = TCEBot(asyncio.get_event_loop(), 'faketoken')
#             bot._reply_dm

#     def test_reply_serverstatus(self):
