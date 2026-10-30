import time
import urllib.request
opener=urllib.request.build_opener(urllib.request.ProxyHandler({}))
for attempt in range(15):
    try:
        for url in ['http://127.0.0.1:8000/api/health','http://127.0.0.1:4321/']:
            with opener.open(url,timeout=3) as response:
                if response.status!=200:raise OSError('Health check failed')
        print('Both services are healthy.')
        break
    except OSError:
        if attempt==14:raise SystemExit('Health check failed; inspect systemd logs') from None
        time.sleep(1)
