import asyncio
import mock
import random

from et_discord_bot.etwolf_client import ETClient


class MockETServerProtocol(asyncio.DatagramProtocol):

    def __init__(self, *args, **kwargs):
        self.received_bytes = b''
        self.transport = None
        super().__init__(*args, **kwargs)

    def connection_made(self, transport):
        self.transport = transport

    def datagram_received(self, data, addr):
        if data.startswith(b'\xff\xff\xff\xffgetinfo'):
            self.transport.sendto(
                b'\xff\xff\xff\xff' + (
                    'infoResponse\n\\challenge\\xxx\\version\\ET Legacy v2.75 linux-i386 Sep 13 2016\\protocol\\84\\hostnam'
                    'e\\^9example^5host\\serverload\\0\\mapname\\obj_stadtrand\\clients\\0\\humans\\0\\sv_maxclients\\10\\g'
                    'ametype\\5\\pure\\1\\game\\etmain\\friendlyFire\\0\\maxlives\\0\\needpass\\0\\gamename\\et\\g_antilag'
                    '\\1\\weaprestrict\\100\\balancedteams\\1'
                ).encode(),
                addr
            )
        elif data.startswith(b'\xff\xff\xff\xffgetservers'):
            self.transport.sendto(
                b'\xff\xff\xff\xff\x67\x65\x74\x73\x65\x72\x76\x65\x72\x73\x52\x65\x73\x70\x6f\x6e\x73\x65\x5c'
                b'\x2e\x04\x39\x4e\x6d\x38\x5c\xd4\x53\x8f\x12\x6d\x3a\x5c\x5e\x0c\x10\x6b\x6d\x38\x5c\x6c\x3d\x15'
                b'\x5c\x6c\x9d\x5c\x53\x8d\x18\x6f\x6d\x38\x5c\x08\x06\x4a\x3a\x6d\x38\x5c\x94\xfb\x0c\x58\xf8\x1d'
                b'\x5c\x94\xfb\x2e\x31\x72\x83\x5c\x44\xe8\xac\x10\x6d\x38\x5c\x25\x3b\x30\x9c\x6d\x39\x5c\x94\xfb'
                b'\x2e\x31\x71\xbb\x5c\x5b\x86\xf1\x1d\x6d\x42\x5c\x57\x6a\x02\xb5\x6d\x38\x5c\x91\xef\x56\x5c\x00'
                b'\x0e\x5c\xc1\xc0\x3b\x92\x6d\x38\x5c\xc1\xc0\x3a\x2b\x6d\x38\x5c\x25\x78\xae\x0e\x6d\x3c\x5c\x05'
                b'\x87\xbd\x0b\x75\x3b\x5c\x94\xfb\xee\x87\x6d\x38\x5c\xc1\xc0\x3b\xc3\x75\x30\x5c\xc1\x21\xb1\xa2'
                b'\x6d\x38\x5c\x55\x0e\xe6\xac\x6d\x38\x5c\x33\xfe\x65\xa1\x6d\x4c\x5c\x3e\x4b\x9f\xf9\x6d\x42\x5c'
                b'\x54\xc8\xd5\xc7\x6d\x38\x5c\x31\xd4\xd2\x90\x6d\x39\x5c\xbc\x7a\x44\x47\x6d\x38\x5c\x3e\x4b\x9f'
                b'\xf9\x6d\x38\x5c\x25\x78\xae\x0e\x6d\x4e\x5c\x5b\x79\x01\x1c\x61\xa8\x5c\x4d\x4e\x64\xcb\x71\x22'
                b'\x5c\x55\x5d\x59\x52\x6d\x3e\x5c\x68\xee\xb6\x97\x6d\x38\x5c\x55\x5d\x59\x52\x6d\x3b\x5c\x94\xfb'
                b'\x2e\x31\x71\x48\x5c\x59\xa3\xbd\xc7\x6d\x38\x5c\x3e\xd2\x73\xb7\x6d\x38\x5c\x32\x07\x46\xd2\x6d'
                b'\x42\x5c\x6b\xbf\x33\x9f\x6d\x38\x5c\x94\xfb\x0c\x58\x1c\x78\x5c\x33\xfe\xe1\xe0\x6d\x38\x5c\x51'
                b'\xc4\x2c\x33\x6d\x38\x5c\x5e\x82\xae\x18\x6d\x38\x5c\xb2\x3f\x48\xa5\x6d\x4d\x5c\x57\x4f\xbb\x6c'
                b'\x6d\x38\x5c\x42\x37\x9a\xcc\x6d\x42\x5c\x25\xbb\x7d\x03\x6d\x38\x5c\x94\xfb\x2e\x31\x6f\xc7\x5c'
                b'\xb0\x39\x8e\xee\x6d\x38\x5c\x34\x43\xf8\x84\x6d\x39\x5c\xd5\xf6\x34\x24\x6a\x18\x5c\x1f\xcc\x83'
                b'\x04\x6d\x38\x5c\x91\xef\x14\x56\x6d\x38\x5c\x3e\x4b\x9f\xf9\x6d\x9c\x5c\x68\xee\xb1\xb4\x6d\x4c'
                b'\x5c\x91\xef\x56\x5c\x00\x02\x5c\x33\x8d\x53\xed\x6d\x38\x5c\x58\x01\x8a\x02\x6d\x3a\x5c\x05\x27'
                b'\xbc\xac\x65\xc2\x5c\x6c\x3d\x15\x5c\x6c\x98\x5c\x9e\x45\xcf\x89\x6d\x38\x5c\x2d\x4c\x5e\x53\x6d'
                b'\x38\x5c\xbc\xa5\xa2\x30\x6d\x38\x5c\x25\xbb\x17\xe5\x82\x35\x5c\x25\x3b\x30\x9c\x6d\x3c\x5c\x6c'
                b'\xb2\x37\xdf\x6d\x38\x5c\xb9\x20\xb5\x09\x6d\x38\x5c\x4d\x4e\x64\xcb\x6d\x3d\x5c\x5b\x79\xa0\xd4'
                b'\x6d\x4c\x5c\x42\xbb\x4b\x9e\x6d\x38\x5c\x6c\x3d\x12\x6d\x6d\x49\x5c\x51\x02\xf2\x0b\x6d\x38\x5c'
                b'\x33\xfe\x53\xa0\x6d\x38\x5c\x91\xef\x56\x5c\x00\x05\x5c\xc1\xc0\x3a\xbb\x6d\x38\x5c\x5d\xba\xcf'
                b'\x6b\x6d\x38\x5c\x25\x78\xae\x0e\x6d\x39\x5c\x88\xba\xe5\x20\x6d\x38\x5c\x2e\x04\x7c\x96\x6d\x5f'
                b'\x5c\x54\xc8\x07\x1d\x69\x78\x5c\x90\x4c\x64\x83\x6d\x38\x5c\xb0\x39\x8e\xfb\x6d\x38\x5c\xb9\x9d'
                b'\xf6\xa4\x6d\x38\x5c\x3e\x4b\x9f\xf9\x6d\x47\x5c\x94\xfb\x2e\x31\x6c\xf0\x5c\x56\x64\x73\x78\x6d'
                b'\x3a\x5c\xa5\xe3\x94\xf8\x6d\x38\x5c\x76\xf0\x3a\x33\x6d\x38\x5c\x51\x13\x2d\x1a\x6d\x38\x5c\xc1'
                b'\xc0\x3b\xba\x6d\x38\x5c\x91\xef\x56\x5c\x00\x0c\x5c\xb2\x3f\x48\xa5\x6d\x50\x5c\x49\x22\x92\xa4'
                b'\x6d\x38\x5c\x56\x64\x73\x78\x6d\x44\x5c\xc1\xb7\x63\xdd\x6d\x3c\x5c\x25\xbb\x17\xe5\xad\x9c\x5c'
                b'\x25\x72\x60\x77\x6d\x3f\x5c\x6c\x3d\xd2\x2f\x6d\x42\x5c\x25\xbb\x4f\x31\x6d\x3e\x5c\x45\x4f\x54',
                addr
            )
            self.transport.sendto(
                b'\xff\xff\xff\xff\x67\x65\x74\x73\x65\x72\x76\x65\x72\x73\x52\x65\x73\x70\x6f\x6e\x73\x65\x5c\x4d'
                b'\x4e\x64\xcb\x75\x31\x5c\x4d\x4e\x64\xcb\x71\x2c\x5c\x1f\x2a\x03\xee\x6d\x38\x5c\x5b\x79\xa0\xd4'
                b'\x6d\x38\x5c\x05\x27\xbc\xb1\x6d\x60\x5c\x44\xe8\xa0\xa1\x6d\x38\x5c\x90\x4c\x7a\x22\x6b\x26\x5c'
                b'\x55\x11\xbd\x75\x6d\x42\x5c\x25\x72\x60\x77\x6d\x38\x5c\xb0\x2e\x62\x6f\xc8\x69\x5c\x5b\x3e\xdc'
                b'\xe4\x6d\x38\x5c\x47\xc1\xf3\xf2\x6d\x38\x5c\xd4\x53\x8f\x12\x69\x78\x5c\x4d\x4e\x64\xcb\x71\x2b'
                b'\x5c\x6c\x3d\x79\x58\x6d\x42\x5c\xc1\x21\xb0\x24\x6d\x38\x5c\x6c\x3d\x12\x6d\x6d\x54\x5c\xc3\xc9'
                b'\x96\x07\x6d\x38\x5c\xb2\x20\x31\x48\x6d\x38\x5c\x94\xfb\x2e\x31\x6d\xd3\x5c\x42\x37\x9a\xcc\x6d'
                b'\x38\x5c\x25\xdd\xd1\x68\x6a\x42\x5c\x44\xbd\x21\x4d\x6d\x38\x5c\x58\xc6\x06\x54\x6d\x38\x5c\x25'
                b'\xbb\x4f\x31\x6d\x4c\x5c\x94\xfb\x4b\x0f\x6d\x38\x5c\x05\x39\xe0\x9d\x6d\x3d\x5c\x25\xdd\xd1\x68'
                b'\x69\xf0\x5c\x18\x84\x2f\x9f\x6d\x38\x5c\xcf\xf6\x43\xcb\x6d\x38\x5c\x40\xfb\x0d\x99\x6d\x38\x5c'
                b'\x8a\xc9\x5e\xc1\x6d\x39\x5c\x90\x4c\x7a\x22\x6b\x3a\x5c\x54\x8b\x6a\x0c\xd4\x4d\x5c\x90\xd9\x5b'
                b'\xff\x6d\x39\x5c\xbc\xa5\x15\xf5\x65\x9a\x5c\xbc\xd5\xa8\x82\x6d\x60\x5c\xae\x47\x16\xfa\x6d\x38'
                b'\x5c\x57\x5c\x55\x6b\x6d\x38\x5c\x55\xc3\xf3\x66\x6d\x39\x5c\xad\xc7\x69\x94\x6d\x42\x5c\x25\x78'
                b'\xae\x0e\x6d\x4d\x5c\xa8\xe8\xa5\xad\x6d\x39\x5c\x54\xc9\x01\x26\x6d\x38\x5c\x3a\xaf\xf1\xb0\x6d'
                b'\x38\x5c\xad\xc7\x69\x91\x6d\x42\x5c\xbc\x28\x60\x04\x6d\x38\x5c\xc7\xcc\xe6\x37\x6d\x3d\x5c\x3e'
                b'\xd2\x73\xb7\x6d\x3d\x5c\x53\x8d\x18\x6e\x6d\x38\x5c\xb9\x23\x4d\x3f\x6d\x38\x5c\xa3\xac\x33\xca'
                b'\x84\xd0\x5c\x25\xbb\x17\xe5\x56\xce\x5c\xc1\xc0\x3b\xa5\x6d\x38\x5c\x05\x87\xbd\x0b\x75\x34\x5c'
                b'\xad\xd4\xeb\xc6\x6d\x38\x5c\x25\x72\x60\x77\x6d\x3d\x5c\xd0\xa7\xf4\x38\x6d\x38\x5c\x6c\x3d\x68'
                b'\x62\x6d\x38\x5c\x25\xbb\x4f\x31\x6d\x3c\x5c\xb9\xf8\x8d\x3f\x6d\x38\x5c\x3e\x43\x2a\xc8\x6d\x38'
                b'\x5c\x45\xcb\xc7\xe6\x6d\x38\x5c\x2e\x1c\x6c\x7a\x6d\x39\x5c\x4d\x4e\x64\xcb\x71\x2e\x5c\xc1\x21'
                b'\xb0\x6b\x6d\x38\x5c\x5e\xf6\xaf\x52\xc8\x61\x5c\x05\x27\xbc\xac\x69\x78\x5c\x6c\x3d\x12\x6d\x6d'
                b'\x5f\x5c\x34\x43\xf8\x84\x6d\x3c\x5c\xad\xe6\x8d\x24\x6d\x38\x5c\x94\xfb\x2e\x31\x6d\x41\x5c\x3e'
                b'\xd2\x73\xb7\x6d\x3a\x5c\x68\xc0\xda\x14\x6d\x38\x5c\x05\x27\xbc\xac\x65\x90\x5c\xb2\x3f\x48\x6f'
                b'\x6d\x39\x5c\x50\x48\x21\x38\x6d\x38\x5c\x6c\x3d\x70\xb6\x6d\x38\x5c\xd5\xf6\x34\x24\x69\xc8\x5c'
                b'\x05\x2d\x6c\x90\x6d\x38\x5c\xa3\xac\x33\xca\x6d\x38\x5c\x59\x64\xbf\x57\x6d\x39\x5c\x91\xef\x56'
                b'\x5c\x00\x06\x5c\x94\xfb\x2e\x31\x52\x7a\x5c\x05\x27\xbc\xad\x6d\x38\x5c\xb9\x8e\x34\x27\x6d\x38'
                b'\x5c\x4d\x37\xdb\xcd\x6d\x38\x5c\x6c\x3d\x15\x5c\x6c\x9c\x5c\xc1\xc0\x3b\xc3\x6d\x38\x5c\xbc\xd5'
                b'\xa8\x82\x69\x78\x5c\x2d\x20\xeb\x54\x6d\x38\x5c\x46\x4d\xc8\x8a\x16\x7b\x5c\x94\xfb\x2e\x31\x6b'
                b'\xdf\x5c\x25\x3b\x30\x9c\x6d\x38\x5c\x94\xfb\x2e\x31\x6d\x38\x5c\xd4\x53\x8f\x12\x7d\x00\x5c\x3e'
                b'\xd2\x47\x2c\x6d\x3a\x5c\x58\xc6\x06\x54\x6d\x47\x5c\xd8\x75\x8f\x99\x6d\x39\x5c\x45\x4f\x54',
                addr
            )
        self.received_bytes += data


class TestServerStatus(object):

    def test_full(self):
        loop = asyncio.get_event_loop()
        listen = loop.create_datagram_endpoint(MockETServerProtocol, local_addr=('127.0.0.1', 47700))
        transport, protocol = loop.run_until_complete(listen)
        client = ETClient()
        host_info = loop.run_until_complete(client.get_server_info('127.0.0.1', 47700))

        assert(host_info == {
            'balancedteams': '1',
            'challenge': 'xxx',
            'clients': '0',
            'friendlyFire': '0',
            'g_antilag': '1',
            'game': 'etmain',
            'gamename': 'et',
            'gametype': '5',
            'hostname': '^9example^5host',
            'hostname_plaintext': 'examplehost',
            'humans': '0',
            'mapname': 'obj_stadtrand',
            'maxlives': '0',
            'needpass': '0',
            'protocol': '84',
            'pure': '1',
            'serverload': '0',
            'sv_maxclients': '10',
            'version': 'ET Legacy v2.75 linux-i386 Sep 13 2016',
            'weaprestrict': '100',
            'players': [],
        })


class TestServerList(object):

    def test_full(self):
        loop = asyncio.get_event_loop()
        listen = loop.create_datagram_endpoint(MockETServerProtocol, local_addr=('127.0.0.1', 47700))
        transport, protocol = loop.run_until_complete(listen)
        client = ETClient()
        servers = loop.run_until_complete(client.get_server_list(master_server_addr=('127.0.0.1', 47700)))
        assert(len(servers) == 198)
        assert(('62.210.71.44', 27962) in servers)