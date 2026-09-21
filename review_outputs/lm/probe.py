import os,json,urllib.request,time,sys
packets=json.load(open('packets.json',encoding='utf-8'))
body={'model':'mistralai/devstral-small-2-2512','messages':[{'role':'system','content':'You are a senior mixed-signal hardware reviewer. Find only real, concrete problems in the extract given; cite parts and nets; plain text; no generic advice.'},{'role':'user','content':'Packet A. Review it. List only real problems.\n\n'+packets['A_power']}],'max_tokens':1500,'temperature':0.2}
t=time.time()
req=urllib.request.Request('http://localhost:1234/v1/chat/completions',data=json.dumps(body).encode(),headers={'Content-Type':'application/json','Authorization':'Bearer '+os.environ['LM_API_TOKEN']})
d=json.load(urllib.request.urlopen(req,timeout=600))
print(round(time.time()-t,1),'s', d.get('usage'))
print(d['choices'][0]['message'].get('content'))
