import requests

import config

class RequestError(RuntimeError):
    pass

# TODO: 'Host' header
class HeadersHelper:

    base = ({
        'User-Agent': 'Mozilla/5.0 (X11; Ubuntu; Linux x86_64; rv:99.0) Gecko/20100101 Firefox/99.0',
        'Accept-Language': 'zh-CN,zh;q=0.8,en-US;q=0.5,en;q=0.3',
        'Accept-Encoding': 'gzip, deflate',  # 'br'
        'Connection': 'keep-alive',
        'Pragma': 'no-cache',
        'Cache-Control': 'no-cache',
    })

    def merge(self, defaultHeaders, headers):
        mergedHeaders = dict(defaultHeaders)
        mergedHeaders.update(headers)
        return mergedHeaders

    # Other: 'Host', 'Cookie', 'Referer'
    def document(self, headers={}):
        return self.merge({
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
            'Upgrade-Insecure-Requests': '1',
            'Sec-Fetch-Dest': 'document',
            'Sec-Fetch-Mode': 'navigate',
            'Sec-Fetch-Site': 'same-origin',
        }, headers)

    # Other: 'Host', 'Cookie', 'Referer'
    def image(self, headers={}):
        return self.merge({
            'Accept': 'image/avif,image/webp,*/*',
            'Sec-Fetch-Dest': 'image',
            'Sec-Fetch-Mode': 'no-cors',
            'Sec-Fetch-Site': 'same-origin',
        }, headers)

    # Other: 'Host', 'Content-Length', 'Origin', 'Referer', 'Cookie'
    def ajaxPost(self, headers={}):
        return self.merge({
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Content-Type': 'application/x-www-form-urlencoded; charset=UTF-8',
            'X-Requested-With': 'XMLHttpRequest',
            'Sec-Fetch-Dest': 'empty',
            'Sec-Fetch-Mode': 'cors',
            'Sec-Fetch-Site': 'same-origin',
        }, headers)

class Session():

    def __init__(self):
        self.session = requests.session()
        self.headersHelper = HeadersHelper()
        self.reset()

    def reset(self):
        self.session.cookies.clear()
        self.session.headers.clear()
        self.session.headers.update(self.headersHelper.base)

    def requestGuarded(self, method, url, timeout=config.requestTimeout, **kwargs):
        res = self.session.request(method, url, timeout=timeout, **kwargs)
        if res.ok:
            return res
        raise RequestError('response ' + str(res.status_code))

    def getDocument(self, url, headers={}, **kwargs):
        headers = self.headersHelper.document(headers)
        return self.requestGuarded('GET', url, headers=headers, **kwargs)

    def getImage(self, url, headers={}, **kwargs):
        headers = self.headersHelper.image(headers)
        return self.requestGuarded('GET', url, headers=headers, **kwargs)

    def postAjax(self, url, headers={}, **kwargs):
        headers = self.headersHelper.ajaxPost(headers)
        return self.requestGuarded('POST', url, headers=headers, **kwargs)
