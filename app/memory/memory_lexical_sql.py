from __future__ import annotations


LEXICAL_TRANSLATE_FROM = (
    '\u00e0\u00e1\u00e2\u00e4\u00e3\u00e5'
    '\u00e7'
    '\u00e8\u00e9\u00ea\u00eb'
    '\u00ec\u00ed\u00ee\u00ef'
    '\u00f1'
    '\u00f2\u00f3\u00f4\u00f6'
    '\u00f9\u00fa\u00fb\u00fc'
    '\u00fd\u00ff'
    '\u0153\u00e6'
)
LEXICAL_TRANSLATE_TO = 'aaaaaaceeeeiiiinoooouuuuyyoa'


def normalized_content_sql(*, column_name: str = 'content') -> str:
    normalized_column = str(column_name or '').strip()
    if not normalized_column:
        raise ValueError('column_name must not be empty')
    return (
        f"translate(lower({normalized_column}), "
        f"'{LEXICAL_TRANSLATE_FROM}', '{LEXICAL_TRANSLATE_TO}')"
    )
