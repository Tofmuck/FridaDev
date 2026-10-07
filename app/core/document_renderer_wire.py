"""M8-C length-framed multipart messages only; no socket/HTTP connection."""
from dataclasses import dataclass
import re

@dataclass(frozen=True,repr=False)
class WireMessage:
    content_type: str
    body: bytes
    http_status: int = 200


def encode_multipart(parts,*,limit):
    from .document_renderer_contract import check_size,fail
    boundary='frida-render-v1'
    while any(b'--'+boundary.encode() in body for _,_,body in parts):
        boundary+='x'
        if len(boundary)>64:fail()
    chunks=[]
    for name,media,body in parts:
        if not re.fullmatch(r'[a-z]{1,16}',name) or type(body) is not bytes:fail()
        chunks.append((f'--{boundary}\r\nContent-Disposition: form-data; name="{name}"\r\n'
            f'Content-Type: {media}\r\nContent-Length: {len(body)}\r\n\r\n').encode('ascii'))
        chunks.extend((body,b'\r\n'))
    chunks.append(f'--{boundary}--\r\n'.encode('ascii'))
    check_size(sum(map(len,chunks)),limit)
    return WireMessage('multipart/form-data; boundary='+boundary,b''.join(chunks))


def parse_multipart(message,*,limit):
    from .document_renderer_contract import check_size,fail,MAX_JSON_BYTES,MAX_SOURCE_BYTES
    if type(message) is not WireMessage or type(message.body) is not bytes or type(message.content_type) is not str:fail()
    check_size(len(message.body),limit)
    match=re.fullmatch(r'multipart/form-data; boundary=([A-Za-z0-9_-]{8,64})',message.content_type)
    if not match:fail()
    delimiter=b'--'+match[1].encode();data=message.body;position=0;parts=[];seen=set()
    while True:
        if data[position:position+len(delimiter)]!=delimiter:fail()
        position+=len(delimiter)
        if data[position:position+4]==b'--\r\n':
            if position+4!=len(data) or not parts:fail()
            return parts
        if data[position:position+2]!=b'\r\n' or len(parts)>=3:fail()
        position+=2
        end=data.find(b'\r\n\r\n',position,position+512)
        if end<0:fail()
        header=data[position:end]
        match=re.fullmatch(br'Content-Disposition: form-data; name="([a-z]{1,16})"\r\nContent-Type: ([a-zA-Z0-9./+-]{1,128})\r\nContent-Length: (0|[1-9][0-9]{0,8})',header)
        if not match:fail()
        name,media=match[1].decode(),match[2].decode();size=int(match[3])
        if name in seen:fail()
        check_size(size,MAX_JSON_BYTES if name in ('request','manifest') else MAX_SOURCE_BYTES)
        seen.add(name);position=end+4
        body=data[position:position+size];position+=size
        if len(body)!=size or data[position:position+2]!=b'\r\n':fail()
        parts.append((name,media,body));position+=2
