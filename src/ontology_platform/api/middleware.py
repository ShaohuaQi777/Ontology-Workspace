"""Actual stream budgets and exact Origin allowlist before JSON/route parsing."""
import json,re,uuid
from urllib.parse import urlsplit


class BoundaryMiddleware:
    def __init__(self,app,allowed_origins):
        self.app=app; self.allowed=frozenset(allowed_origins)
        if not self.allowed: raise ValueError('Explicit allowed origins are required')
        for origin in self.allowed:
            parsed=urlsplit(origin)
            if parsed.scheme not in ('http','https') or not parsed.hostname or parsed.username is not None or parsed.password is not None or parsed.path or parsed.query or parsed.fragment or '*' in origin:
                raise ValueError('Invalid allowed origin')
            if parsed.scheme=='http' and parsed.hostname not in ('127.0.0.1','localhost','::1'): raise ValueError('Insecure remote origin is forbidden')

    async def __call__(self,scope,receive,send):
        if scope['type']!='http': return await self.app(scope,receive,send)
        run_id='request-'+uuid.uuid4().hex
        scope.setdefault('state',{})['run_id']=run_id
        async def reject(status,code):
            body=json.dumps({'code':code,'run_id':run_id}).encode()
            await send({'type':'http.response.start','status':status,'headers':[(b'content-type',b'application/json'),(b'cache-control',b'no-store'),(b'content-length',str(len(body)).encode())]})
            await send({'type':'http.response.body','body':body})
        headers=scope.get('headers',[]); values=lambda key:[value.decode('latin1') for name,value in headers if name.lower()==key]
        method=scope['method']; raw=method=='POST' and re.fullmatch(r'/api/projects/[^/]+/sources',scope['path']) is not None
        lengths=values(b'content-length')
        if len(lengths)>1 or (lengths and (len(lengths[0])>10 or not lengths[0].isascii() or not lengths[0].isdigit())): return await reject(400,'INVALID_REQUEST')
        limit=1048576 if raw else 131072
        if lengths and int(lengths[0])>limit: return await reject(413,'BODY_TOO_LARGE')
        if method not in ('GET','HEAD','OPTIONS'):
            origins=values(b'origin')
            if len(origins)!=1 or origins[0] not in self.allowed: return await reject(403,'ORIGIN_FORBIDDEN')
            content_types=values(b'content-type')
            expected='application/octet-stream' if raw else 'application/json'
            if len(content_types)!=1 or content_types[0].split(';',1)[0].strip().lower()!=expected: return await reject(415,'UNSUPPORTED_MEDIA_TYPE')
        buffer=bytearray()
        while True:
            message=await receive()
            if message['type']=='http.disconnect': return
            chunk=message.get('body',b'')
            if len(buffer)+len(chunk)>limit: return await reject(413,'BODY_TOO_LARGE')
            buffer.extend(chunk)
            if not message.get('more_body',False): break
        delivered=False
        async def bounded_receive():
            nonlocal delivered
            if not delivered:
                delivered=True; return {'type':'http.request','body':bytes(buffer),'more_body':False}
            return await receive()
        async def no_store(message):
            if message['type']=='http.response.start':
                message={**message,'headers':[*message.get('headers',[]),(b'cache-control',b'no-store'),(b'x-content-type-options',b'nosniff')]}
            await send(message)
        await self.app(scope,bounded_receive,no_store)
