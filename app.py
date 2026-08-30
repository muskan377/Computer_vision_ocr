from __future__ import annotations
import json, mimetypes, re, uuid
from pathlib import Path
from urllib.parse import unquote
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from src.pipeline import analyze
from src.config import OUTPUT_DIR

BASE=Path(__file__).resolve().parent; UPLOADS=BASE/'uploads'; UPLOADS.mkdir(exist_ok=True); OUTPUT_DIR.mkdir(exist_ok=True)

class Handler(BaseHTTPRequestHandler):
    def _send(self, status, body, content_type='text/html; charset=utf-8'):
        data=body.encode('utf-8') if isinstance(body,str) else body
        self.send_response(status); self.send_header('Content-Type',content_type); self.send_header('Content-Length',str(len(data))); self.end_headers(); self.wfile.write(data)
    def do_GET(self):
        path=unquote(self.path.split('?',1)[0])
        if path=='/':
            return self._file(BASE/'templates/index.html','text/html; charset=utf-8')
        if path.startswith('/static/'):
            p=BASE/'static'/path[len('/static/'):]; return self._file(p,mimetypes.guess_type(p.name)[0] or 'application/octet-stream')
        if path.startswith('/api/jobs/'):
            rel=path[len('/api/jobs/'):].split('/',1)
            if len(rel)==2:
                job,file=rel; p=OUTPUT_DIR/job/file
                if p.exists() and p.is_file(): return self._file(p,mimetypes.guess_type(p.name)[0] or 'application/octet-stream', download=False)
        self._send(404,b'Not found','text/plain')
    def _file(self,p,ctype,download=False):
        if not p.exists() or not p.is_file(): return self._send(404,b'Not found','text/plain')
        data=p.read_bytes(); self.send_response(200); self.send_header('Content-Type',ctype); self.send_header('Content-Length',str(len(data)));
        if download:self.send_header('Content-Disposition',f'attachment; filename="{p.name}"')
        self.end_headers(); self.wfile.write(data)
    def do_POST(self):
        if self.path!='/api/analyze': return self._send(404,b'Not found','text/plain')
        try:
            length=int(self.headers.get('Content-Length','0'))
            if length>250*1024*1024: return self._json(413,{'error':'Video is larger than 250 MB.'})
            body=self.rfile.read(length); ctype=self.headers.get('Content-Type','')
            m=re.search(r'boundary=(?:"([^"]+)"|([^;]+))',ctype)
            if not m: return self._json(400,{'error':'Invalid multipart upload.'})
            boundary=(m.group(1) or m.group(2)).encode()
            part=body.split(b'--'+boundary)[1]
            header_end=part.find(b'\r\n\r\n')
            if header_end<0: return self._json(400,{'error':'Could not read uploaded video.'})
            headers=part[:header_end].decode('utf-8','ignore')
            content=part[header_end+4:]
            if content.endswith(b'\r\n'): content=content[:-2]
            fm=re.search(r'filename="([^"]+)"',headers)
            name=re.sub(r'[^A-Za-z0-9_.-]','_',fm.group(1) if fm else 'video.mp4')
            if Path(name).suffix.lower() not in {'.mp4','.mov','.avi','.mkv'}: return self._json(400,{'error':'Supported formats: MP4, MOV, AVI, MKV'})
            token=uuid.uuid4().hex[:10]; path=UPLOADS/f'{token}_{name}'; path.write_bytes(content)
            result=analyze(path,OUTPUT_DIR/token); self._json(200,result['data'] | {'job_id':result['job_id']})
        except Exception as e:
            self._json(500,{'error':str(e)})
    def _json(self,status,obj): self._send(status,json.dumps(obj),'application/json; charset=utf-8')
    def log_message(self,fmt,*args): print(fmt%args)

if __name__=='__main__':
    print('ScoreVision running at http://127.0.0.1:5000')
    ThreadingHTTPServer(('127.0.0.1',5000),Handler).serve_forever()
