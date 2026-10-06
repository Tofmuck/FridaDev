"""Cancellation of the real owned loop while stdlib DNS is still blocked."""
import asyncio
import socket
import threading
import unittest
from types import SimpleNamespace
from unittest.mock import patch
from core import document_workshop_turn as turn
from core.document_workshop_progress import DocumentPreparation

class DocumentaryLoopOwnershipTests(unittest.TestCase):
    def proof(self, inactivity):
        dns_started, dns_release, returned = threading.Event(), threading.Event(), threading.Event()
        connects, result = [], []
        clock=[0.]
        owner=turn.DocumentTurn(SimpleNamespace(token=SimpleNamespace(turn_id='11111111-1111-4111-8111-111111111111')),{},())
        owner.progress=DocumentPreparation(monotonic=lambda:clock[0])
        llm=SimpleNamespace(build_payload=lambda messages,temperature,top_p,max_tokens,stream:dict(model='openai/gpt-5.1',messages=messages,
            temperature=temperature,top_p=top_p,max_tokens=max_tokens,stream=stream,reasoning={'exclude':True}),
            or_headers=lambda **_: {'Content-Type':'application/json'},strip_internal_provider_headers=lambda h:h,
            or_chat_completions_url=lambda:'http://blocked.invalid/v1/chat/completions')
        def dns(*_,**__):
            dns_started.set();dns_release.wait(5)
            return [(socket.AF_INET,socket.SOCK_STREAM,socket.IPPROTO_TCP,'',('127.0.0.1',1))]
        def connect(*_):
            connects.append(1);raise AssertionError('late DNS must never open a connection')
        def run():
            try:
                args=dict(counter=lambda *_:1,temperature=.7,top_p=1,llm_module=llm)
                # Before the correction this is the actual root call boundary.
                if hasattr(owner,'_run_exchange'):
                    owner._run_exchange([dict(role='user',content='Synthetic request')],**args)
                else:
                    asyncio.run(owner._exchange([dict(role='user',content='Synthetic request')],**args))
            except Exception as error: result.append(getattr(error,'reason_code',type(error).__name__))
            finally:returned.set()
        with patch.object(turn.actions,'check_active',lambda _:None), patch.object(socket,'getaddrinfo',dns), \
             patch.object(socket.socket,'connect',connect):
            worker=threading.Thread(target=run,daemon=True);worker.start()
            try:
                self.assertTrue(dns_started.wait(2))
                if inactivity:owner._loop.call_soon_threadsafe(clock.__setitem__,0,120.)
                else:owner._loop.call_soon_threadsafe(owner.progress.cancel)
                self.assertTrue(returned.wait(1),'root still waits for blocked DNS after cancellation')
                self.assertEqual(connects,[])
            finally:
                dns_release.set();worker.join(2)
            self.assertFalse(worker.is_alive())
            self.assertEqual(connects,[])
        self.assertEqual(result,['document_inactivity' if inactivity else 'document_cancelled'])

    def test_cancel_returns_before_dns_releases_and_never_connects_late(self):self.proof(False)
    def test_inactivity_at_120_returns_before_dns_releases_and_never_connects_late(self):self.proof(True)
