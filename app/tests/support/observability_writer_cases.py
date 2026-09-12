"""Synthetic inputs through the runtime builders, never copied from operator data."""
from types import SimpleNamespace
from contextlib import nullcontext
from datetime import datetime, timezone

from biblio.conversation_state import BiblioConversationState, update_state_from_runtime
from biblio.observability import build_biblio_event_payload
from core import conversations_prompt_window
from core.hermeneutic_node.inputs.memory_retrieved_input import build_memory_retrieved_input
from core.hermeneutic_node.inputs.memory_arbitration_input import build_memory_arbitration_input
from memory.memory_pre_arbiter_basket import build_pre_arbiter_basket
from memory.memory_trace_summary_store import get_summary_for_trace
from observability.memory_chain_snapshot import build_memory_chain_snapshot_payload
from observability.prompt_injection_summary import build_memory_prompt_injection_summary


GENERATION_ID = 'gen-1800000000-aBcD0123456789EfGhIjKl'


def memory_inputs():
    traces = [
        {'role': 'user', 'content': 'synthetic memory', 'conversation_id': 'fixture',
         'timestamp': f'2026-09-01T00:00:0{i}Z', 'score': 0.9}
        for i in range(2)
    ]
    retrieved = build_memory_retrieved_input(retrieval_query='synthetic', top_k_requested=8, traces=traces)
    basket = build_pre_arbiter_basket(memory_retrieved=retrieved, retrieved_candidates=traces, internal_traces=traces)
    candidate_id = basket.candidates[0]['candidate_id']
    arbitration = build_memory_arbitration_input(
        memory_retrieved=retrieved, raw_candidates_count=2, status='ok',
        basket_candidates=basket.candidates, injected_candidate_ids=[candidate_id],
        decisions=[{'candidate_id': candidate_id, 'keep': True, 'semantic_relevance': 0.9,
                    'contextual_gain': 0.8, 'redundant_with_recent': False,
                    'reason': 'synthetic explanation', 'decision_source': 'llm'}],
    )
    return dict(current_mode='normal', memory_retrieved=retrieved, memory_arbitration=arbitration,
                memory_traces=basket.prompt_candidates, context_hints=[])


def memory_payload():
    return build_memory_chain_snapshot_payload(**memory_inputs())


def biblio_state_and_transition():
    before = BiblioConversationState.empty(conversation_id='fixture')
    anchor = dict(document_id='abcdef0123456789', doc_id_short='abcdef01', page_no=3,
                  para_no=2, paragraph_id=7, passage_hash='012345abcdef', status='extracted',
                  reason_code='biblio_passage_extracted', interval_hint={
                      'kind': 'page_range', 'mode': 'bounded', 'state': 'complete',
                      'end_page_no': 4, 'end_para_no': 3, 'requested_end_page_no': 4,
                      'section_no': 1, 'chapter_no': 1, 'section_kind': 'chapter',
                      'section_level': 1, 'next_page_no': 5, 'next_para_no': 1,
                  })
    return update_state_from_runtime(before, library_result=SimpleNamespace(state_anchor=anchor),
                                     conversation_id='fixture', now_iso='2026-09-01T00:00:00Z')


def biblio_payload():
    state, transition = biblio_state_and_transition()
    return build_biblio_event_payload(enabled=False, status='disabled', reason_code='biblio_disabled',
                                     biblio_state=state, state_transition=transition)


def prompt_memory_summary():
    row = ('aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee', 'fixture',
           datetime(2026, 9, 1, tzinfo=timezone.utc), datetime(2026, 9, 2, tzinfo=timezone.utc),
           'synthetic parent content')
    cursor = SimpleNamespace(execute=lambda *a: None, fetchone=lambda: row)
    connection = SimpleNamespace(cursor=lambda: nullcontext(cursor))
    parent = get_summary_for_trace({'summary_id': row[0]}, conn_factory=lambda: nullcontext(connection),
                                   logger=SimpleNamespace(warning=lambda *a: None))
    return build_memory_prompt_injection_summary(
        [{'role': 'system', 'content': conversations_prompt_window.MEMORY_CONTEXT_BLOCK_HEADER_PREFIX}],
        memory_traces=[{'candidate_id': 'cand-0123456789abcdef', 'parent_summary': parent}],
    )


def web_sources():
    return [{'url': 'https://www.source.invalid/item', 'rank': i + 1,
             'content_used': 'synthetic source', 'used_in_prompt': True,
             'used_content_kind': 'snippet', 'crawl_status': 'ok'} for i in range(4)]
