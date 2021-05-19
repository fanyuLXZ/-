import requests


class session:
    session = requests.Session()
    requestHeaders = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,"
                  "application/signed-exchange;v=b3;q=0.9",
        "Accept-Encoding": "gzip, deflate",
        "Accept-language": "zh-CN,zh;q=0.9",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) "
                      "Chrome/81.0.4044.138 Safari/537.36",
        "Upgrade-Insecure-Requests": "1"
    }
    session.headers = requestHeaders
    errorUrls = {}

    def __init__(self, errorUrls=None, headers=None):
        if errorUrls is None:
            errorUrls = {}
        if headers is None:
            headers = {}
        for headerKey in headers.keys():
            self.requestHeaders[headerKey] = headers[headerKey]
        self.errorUrls = errorUrls

    def get_session(self):
        return self.session

    def get(self, url, **kwargs):
        result = self.session.get(url, **kwargs)
        if result.status_code != 200:
            raise RequestUtilError("请求出错：\ncode:"+str(result.status_code)+"result"+result.text)
        elif result.url not in self.errorUrls.keys():
            return result
        else:
            raise RequestUtilError(self.errorUrls[result.url] + "错误")

    def post(self, url, **kwargs):
        result = self.session.post(url, **kwargs)
        if result.status_code != 200:
            raise RequestUtilError("请求出错：\ncode:"+str(result.status_code)+"result"+result.text)
        elif result.url not in self.errorUrls.keys():
            return result
        else:
            raise RequestUtilError(self.errorUrls[result.url] + "错误")


class RequestUtilError(BaseException):
    def __init__(self, msg):
        self.msg = msg

    def __str__(self):
        return self.msg
