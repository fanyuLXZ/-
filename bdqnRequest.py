import re

import requests

import AipOcrUtil
import RequestUtil
import StrUtil
import UrlUtil


class bdqnRequest:
    session = RequestUtil.session().get_session()

    # bdqn网站上的路径
    urls = UrlUtil.regionUrl("https", "s.bdqn.cn", "80", {
        "verify_code": "captcha.shtml",
        "login": "login",
        "getProducts": "/course/getProducts",
    })

    # bdqn网站上的请求结果集合
    results = {

    }

    bdqnData = {
        "username": "",
        "password": "",
        "productId": ""
    }

    def __init__(self, bdqnData: dict):
        for dataKey in self.bdqnData.keys():
            try:
                self.bdqnData[dataKey] = bdqnData[dataKey]
            except KeyError:
                pass

    # 登陆方法 返回是否成功
    def login(self):
        # 初始化登陆时需要提交的验证信息
        data = {
            "LoginForm[username]": self.bdqnData["username"],
            "LoginForm[password]": StrUtil.to_password(self.bdqnData["password"])
        }
        while True:
            # 获取验证码图片
            print("正在获取验证码图片。。。")
            verify_code_result = self.session.get(self.urls.get("verify_code"), verify=False)
            # 识别图片
            print("正在识别图片。。。")
            data["LoginForm[verifyCode]"] = AipOcrUtil.get_str(verify_code_result.content)

            # 提交登陆表单 进入主页（存入cookie）
            print("正在登陆。。。。")
            login_result = self.session.post(self.urls.get("login"), data=data)
            # 判断是否登陆成功
            try:
                requests.utils.dict_from_cookiejar(self.session.cookies)["username"]
            except KeyError:
                if login_result.url == self.urls.get("login"):
                    error_messages = re.findall(r'<spanclass="errorMessage"(.*?)/span></p>',
                                                StrUtil.formatting(login_result.text))
                    for now_error_message in error_messages:
                        error_messages = re.findall(r'>(.*?)<', now_error_message)[0]
                        if error_messages != "":
                            break
                    if error_messages == "验证码不正确.":
                        print("验证码错误，正在尝试重新识别！")
                        continue
                    else:
                        if error_messages == "用户名或密码错误，请重新输入。" or \
                                error_messages == "用户不存在，请重新输入。" or \
                                error_messages == "用户名不能为空":
                            print("登陆失败！原因：" + error_messages)
                            return False
                        else:
                            raise Exception(str(error_messages) + "错误")
            print("登陆成功！")
            self.results[self.urls.get("login")] = login_result
            return True
    # 加载课程码 返回选择的课程码
    def load_product_id(self):
        # 加载课程码之前先判断是否登陆成功过
        try:
            login_result = self.results[self.urls.get("login")]
        except KeyError:
            print("错误！：未登陆")
            self.login()
            login_result = self.results[self.urls.get("login")]

        print("正在加载课程码。。。")
        # 请求课程码
        login_page = StrUtil.formatting(login_result.text)
        # 定义课程
        products = []
        # 获取所有课程码
        productIds = re.findall("data-productid=\"(.*?)\"", login_page)
        # 根据所有课程码获取对应课程信息
        for productId in productIds:
            text = re.findall("data-productid=\"" + productId + "\">(.*?)<span>", login_page)[0]
            deadline = \
                re.findall("data-productid=\"" + productId + "\">" + text + "<span>(.*?)</span>", login_page)[0]
            if re.compile("已过期").search(deadline) or re.compile("体验及专家课程").search(text):
                productIds.remove(productId)
                continue
            products.append({
                "id": productId,
                "text": text,
                "deadline": deadline
            })

        # 判断是否有有效productId
        if self.bdqnData["productId"] not in productIds:
            # 如果没有
            print("检测到课程无效")
            while self.bdqnData["productId"] not in productIds:
                print("序号\t课程名\t状态")
                for i in range(len(products)):
                    print(str(i + 1) + "\t" + products[i]["text"] + "\t" + products[i]["deadline"])
                try:
                    c = input("(已排除过期课程)请选择:")
                    self.bdqnData["productId"] = products[int(c) - 1]["id"]
                except IndexError:
                    self.bdqnData["productId"] = ""
                if self.bdqnData["productId"] not in productIds:
                    print("输入错误！请重新输入!")
        return self.bdqnData["productId"]

    # 获取云题库地址
    def get_kcg_path(self):
        # 获取云题库地址之前先判断是否登陆成功过
        try:
            login_result = self.results[self.urls.get("login")]
        except KeyError:
            print("错误！：未登陆")
            login_result = self.results[self.urls.get("login")]
            self.login()
        try:
            self.urls.put("ytk", re.findall('<aclass="nav-4courseUrl"href="(.*?)"target',
                                            StrUtil.formatting(login_result.text))[0])
        except IndexError:
            print("主页错误")
            return None
        return self.session.get(self.urls.get("ytk"), allow_redirects=False).headers['location']
