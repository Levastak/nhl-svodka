"""Link maintenance changes captions in place and preserves a text post's preview."""
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
import tg


class LinkUpdates(unittest.TestCase):
    def test_site_footer_uses_custom_domain(self):
        self.assertIn('href="https://nhl-stats.ru/"', tg.FOOT)
        self.assertNotIn('github.io', tg.FOOT)

    def test_caption_only_update_is_silent_and_keeps_message_id(self):
        with tempfile.TemporaryDirectory() as directory:
            p = Path(directory) / 'edits.json'
            text = '<b>Прежний текст</b> <a href="https://nhl-stats.ru/#news">Сайт</a>'
            p.write_text(json.dumps({'items':[{'message_id':299,'text':text,'status':'ready','notify':False}]}))
            with patch.object(tg,'TG',directory), patch.object(tg,'LOG',{'ok':[],'fail':[]}), \
                    patch.object(tg,'_call') as call, patch.object(tg,'_admin_send') as admin, patch.object(tg.time,'sleep'):
                tg.apply_edits(1,{}, {'admin_chat_id':2})
                call.assert_called_once_with('editMessageCaption', {'chat_id':1,'message_id':299,'caption':text,'parse_mode':'HTML'})
                admin.assert_not_called()
                self.assertEqual(json.loads(p.read_text())['items'][0]['status'],'done')

    def test_long_text_retains_preview_and_never_reuploads_media(self):
        with tempfile.TemporaryDirectory() as directory:
            p=Path(directory)/'edits.json';text='Прежний текст '*100
            p.write_text(json.dumps({'items':[{'message_id':291,'text':text,'preview_url':'https://example.com/card.png','status':'ready','notify':False}]}))
            with patch.object(tg,'TG',directory), patch.object(tg,'LOG',{'ok':[],'fail':[]}), \
                    patch.object(tg,'_call') as call, patch.object(tg.time,'sleep'):
                tg.apply_edits(1,{})
                call.assert_called_once_with('editMessageText', {'chat_id':1,'message_id':291,'text':text,'parse_mode':'HTML','link_preview_options':{'url':'https://example.com/card.png','prefer_large_media':True,'show_above_text':True}})


class TelegramRateLimit(unittest.TestCase):
    def test_explicit_retry_after_retries_same_request(self):
        import io
        import urllib.error
        from unittest.mock import MagicMock
        failed=urllib.error.HTTPError('https://example.com',429,'Too Many Requests',None,
               io.BytesIO(json.dumps({'ok':False,'error_code':429,'parameters':{'retry_after':30}}).encode()))
        ok=MagicMock();ok.__enter__.return_value.read.return_value=b'{"ok":true,"result":true}'
        with patch.object(tg,'TOKEN','test'), patch.object(tg.urllib.request,'urlopen',side_effect=[failed,ok]) as request, patch.object(tg.time,'sleep') as sleep:
            self.assertTrue(tg._call('editMessageCaption',{'chat_id':1,'message_id':299,'caption':'Same caption'}))
            self.assertEqual(request.call_count,2)
            self.assertIs(request.call_args_list[0].args[0],request.call_args_list[1].args[0])
            sleep.assert_called_once_with(31)

if __name__=='__main__':unittest.main()
