import asyncio
import mock

from et_discord_bot.bot import ETBot
from et_discord_bot.etwolf_client import ETClient


class TestBot(object):

    @pytest.mark.asyncio
    async def test_post_serverstatus(self):
        loop = asyncio.get_event_loop()
        host_details = [
            {
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
                'ip': '192.168.1.1',
                'port': 27960,
            },
        ]
        mocker dhclient_mock:
            async def send_message(channel, embed):
                pass
            dhclient_mock.send_message = send_message

            bot = ETBot('test_token', loop)
            loop.run_until_complete(bot._post_serverstatus(host_details))
            import ipdb; ipdb.set_trace()
            assert('test')

    def test_get_serverstatus(self):
        bot = ETBot('test_token', asyncio.get_event_loop())
        bot._get_serverstatus()
