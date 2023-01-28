import aiohttp
import base64

# Used https://github.com/oscie57/tiktok-voice/blob/main/main.py
class tTTS:
    def __init__(
        self,
        text: str,
        aiohttp_session: aiohttp.ClientSession = None,
        session_id: str = '57b7d8b3e04228a24cc1e6d25387603a',
        text_speaker: str = 'en_uk_001'
    ):
        self.session_id = session_id
        self.text = text
        self.aiohttp_session = aiohttp_session or aiohttp.ClientSession()
        self.text_speaker = text_speaker

    async def _send_request(self) -> dict:
        url = 'https://api16-normal-v6.tiktokv.com/media/api/text/speech/invoke/'
        headers = {
            'User-Agent': 'com.zhiliaoapp.musically/2022600030 (Linux; U; Android 7.1.2; es_ES; SM-G988N; Build/NRD90M;tt-ok/3.12.13.1)',
            'Cookie': f'sessionid={self.session_id}'
        }
        params = {
            'text_speaker': self.text_speaker,
            'req_text': self.text,
            'speaker_map_type': 0,
            'aid': 1233
        }

        async with self.aiohttp_session.post(url, headers=headers, params=params) as r:
            r_data = await r.json()
            b64_encoded = r_data['data']['v_str']
            output_data = {
                'data': base64.b64decode(b64_encoded),
                'status': r_data['message'],
                'status_code': r_data['status_code'],
                'duration': r_data['data']['duration'],
                'speaker': r_data['data']['speaker'],
                'log': r_data['extra']['log_id']
            }
            return output_data

    async def save(self, filename: str) -> dict:
        data = await self._send_request()
        with open(filename, 'wb') as f:
            f.write(data['data'])
        
        return data

