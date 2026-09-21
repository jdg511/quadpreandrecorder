import os,json,urllib.request,urllib.error
body={'model':'qwen/qwen3.8-27b','messages':[{'role':'user','content':'Reply with OK.'}],'max_tokens':7000}
req=urllib.request.Request('http://localhost:1234/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['LM_API_TOKEN']})
try:
    d=json.load(urllib.request.urlopen(req,timeout=120)); print(d['choices'][0]['message'].get('content')[:200], d.get('usage'))
except urllib.error.HTTPError as e:
    print(e.code, e.read()[:800])
