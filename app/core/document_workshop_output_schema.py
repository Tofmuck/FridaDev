"""Single OpenRouter output schema for the existing documentary envelope.

Closed objects, required properties, nullable leaves and nested anyOf/$ref only.
Semantic/Unicode/volume/authority guards remain in the local validators.
Return a fresh tree: neither a caller nor a builder owns the next request's schema.
"""
from .document_workshop_contract import DOCUMENT_PROFILE
from .document_workshop_envelope import DOCUMENT_LIMITATION_CODES


def _object(properties):
    return dict(type='object', properties=properties, required=list(properties), additionalProperties=False)


def _array(items):
    return dict(type='array', items=items)


def document_response_format() -> dict:
    span = _object(dict(text=dict(type='string'), bold=dict(type='boolean'),
                        italic=dict(type='boolean'), link=dict(type=['string', 'null'])))
    spans = _array({'$ref': '#/$defs/span'})
    block = dict(anyOf=[
        _object(dict(type=dict(type='string', enum=['paragraph', 'quote']), spans=spans)),
        _object(dict(type=dict(type='string', enum=['heading']),
                     level=dict(type='integer', enum=[1, 2, 3, 4, 5, 6]), spans=spans)),
        _object(dict(type=dict(type='string', enum=['list']), ordered=dict(type='boolean'), items=_array(spans))),
        _object(dict(type=dict(type='string', enum=['table']), rows=_array(_array(spans)))),
        _object(dict(type=dict(type='string', enum=['page_break']))),
    ])
    canonical = _object(dict(schema_version=dict(type='integer', enum=[1]),
                             profile=dict(type='string', enum=[DOCUMENT_PROFILE]),
                             blocks=_array({'$ref': '#/$defs/block'})))
    proposal = _object(dict(
        operation=dict(type='string', enum=['create', 'copy', 'update']),
        format=dict(type='string', enum=['markdown', 'docx', 'pdf']),
        relative_path=dict(type='string'), source_file_ids=_array(dict(type='string')),
        limitations=_array(dict(type='string', enum=sorted(DOCUMENT_LIMITATION_CODES))),
        canonical=canonical,
    ))
    schema = _object(dict(
        schema_version=dict(type='integer', enum=[1]),
        status=dict(type='string', enum=['prepared', 'clarify', 'refuse']),
        surface_text=dict(type='string'),
        proposal=dict(anyOf=[proposal, dict(type='null')]),
    ))
    schema['$defs'] = dict(span=span, block=block)
    return dict(type='json_schema', json_schema=dict(name='frida_document_envelope_v1', strict=True, schema=schema))
