class regionUrl:
    # 协议
    agreement = "http"
    # 域名
    domain_name = ""
    # 端口
    post = ""
    # 可能性链接 存在的意义在于能自定义url名 增加可读性
    urls = {}

    def __init__(self, agreement, domain_name, post="80", urls=None):
        if urls is None:
            urls = {}
        self.agreement = agreement
        self.domain_name = domain_name
        self.post = post
        for urlKey in urls.keys():
            self.put(urlKey, urls[urlKey])

    def get(self, key):
        if key in self.urls:
            return self.agreement + "://" + self.domain_name + self.urls[key]
        else:
            return self.agreement + "://" + self.domain_name + key

    def put(self, key, value=""):
        if value.startswith(self.agreement + "://" + self.domain_name):
            value = value.replace(self.agreement + "://" + self.domain_name, "")
            value = value.replace(":" + self.post, "")
        if not value.startswith("/"):
            value = "/" + value
        self.urls[key] = value
