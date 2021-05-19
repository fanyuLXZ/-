import urllib3

import ConfigUtil
import bdqnRequest
import kgcRequest
import StrUtil
import traceback
import requests
import RequestUtil

print("欢迎进入云题库自动刷题小程序 7.0")
print("正在初始化数据中。。。")
try:
    # 初始化info.ini
    configInfo = ConfigUtil.configInfo("info.ini", {
        "账号": {
            "豆号": "",
            "密码": "",
            "课程码": "",
        },
        "刷题": {
            "刷题入口": "",
            "刷题次数": "",
            "正确率": "",
            "每道题刷题的时间": "",
        },
        "刷题入口细分项": {
            "自动选择刷题入口地址": True,
            "刷题入口地址": "",
            "专项技能型刷到100%是否继续刷": False
        },
        "配置相关": {
            "是否记住账号相关配置": True,
            "是否记住刷题相关配置(包括刷题入口细分项)": False
        }
    }, "utf-8-sig")
    # 获取到info.ini中的数据 (没有section的)
    config = configInfo.get_dic_not_section()
    # 初始化bdqn请求的对象
    bdqnRequestObj = bdqnRequest.bdqnRequest({
        "username": config["豆号"],
        "password": config["密码"],
        "productId": config["课程码"]
    })
    # 登陆
    if bdqnRequestObj.bdqnData["username"] == "" or bdqnRequestObj.bdqnData["password"] == "":
        bdqnRequestObj.bdqnData["username"] = input("请输入账号：")
        bdqnRequestObj.bdqnData["password"] = input("请输入密码：")
    else:
        print("检测到配置文件的账号和密码,正在使用配置文件的账户和密码登陆。。。")
    while not bdqnRequestObj.login():
        bdqnRequestObj.bdqnData["username"] = input("请输入账号：")
        bdqnRequestObj.bdqnData["password"] = input("请输入密码：")
    config["豆号"] = bdqnRequestObj.bdqnData["username"]
    config["密码"] = bdqnRequestObj.bdqnData["password"]
    # 加载课程码
    config["课程码"] = bdqnRequestObj.load_product_id()
    # 获取到课工场的地址
    kgcPath = bdqnRequestObj.get_kcg_path()
    # 初始化kgc请求的对象
    kgcRequestObj = kgcRequest.kgcRequest({
        "kgc_index_path": kgcPath,
        "entry_name": config["刷题入口"],
        "get_paper_href": config["刷题入口地址"],
        "100%go_on": StrUtil.str_to_bool(config["专项技能型刷到100%是否继续刷"]),
        "auto_choice_get_paper_href": StrUtil.str_to_bool(config["自动选择刷题入口地址"]),
        "do_time": config["每道题刷题的时间"]
    })
    # 加载刷题入口
    config["刷题入口"] = kgcRequestObj.load_entry()
    # 如果不用自动选择地址
    if not kgcRequestObj.kgcData["auto_choice_get_paper_href"]:
        # 加载获取试卷地址
        config["刷题入口地址"] = kgcRequestObj.load_get_paper_href()
    print("刷题入口为：" + config["刷题入口"])
    # 加载刷题次数
    while True:
        try:
            if config["刷题次数"] == "" or not config["刷题次数"].isdigit() or int(config["刷题次数"]) == 0:
                print("输入次数：(题数=次数*每次刷题数(取决于你选择的刷题入口)")
                config["刷题次数"] = int(input())
            else:
                config["刷题次数"] = int(config["刷题次数"])
            break
        except ValueError:
            print("刷题次数应该为数字!")
    # 加载正确率
    while True:
        try:
            if config["正确率"] == "" or not config["正确率"].isdigit():
                print("输入正确率：(如：80 = 80%正确率,计算可能有所偏差,正确率仅为本次程序刷题的正确率，不代表云题库显示的正确率)")
                config["正确率"] = int(input())
            else:
                config["正确率"] = int(config["正确率"])
            break
        except ValueError:
            print("正确率应该为数字!")
    # 开始刷题
    i = 0
    while i < config["刷题次数"]:
        try:
            try:
                print("第" + str((i + 1)) + "次")
                # 如果要自动选择地址
                if kgcRequestObj.kgcData["auto_choice_get_paper_href"]:
                    # 加载获取试卷地址
                    kgcRequestObj.load_get_paper_href()
                if kgcRequestObj.do_test_paper(config["正确率"] / 100):
                    i += 1
                    kgcRequestObj.print_today_question_count_url()
            except RequestUtil.RequestUtilError:
                print("登陆过期！正在重新登陆课工场。。。。")
                # 重新加载课工场
                kgcRequestObj.reload(bdqnRequestObj.get_kcg_path())
        except RequestUtil.RequestUtilError:
            print("重新登陆课工场出错，正在重新登陆bdqn。。。。")
            # 重新登陆北大青鸟
            while not bdqnRequestObj.login():
                pass
            # 重新加载课工场
            kgcRequestObj.reload(bdqnRequestObj.get_kcg_path())
        except requests.exceptions.ConnectionError:
            print("链接超时, 正在重新尝试登陆")
            # 重新登陆北大青鸟
            while not bdqnRequestObj.login():
                pass
            # 加载课程码
            config["课程码"] = bdqnRequestObj.load_product_id()
            # 重新加载课工场
            kgcRequestObj.reload(bdqnRequestObj.get_kcg_path())
        except urllib3.exceptions.ProtocolError or requests.exceptions.ConnectionError:
            input("网络错误，请检查网络后按下回车继续刷题：")
        except Exception as e:
            if str(e) == "获取试卷的地址失效或网络错误！" or str(e) == "网络错误！":
                input("网络错误，请检查网络后按下回车继续刷题：")
            elif str(e) == "重复提交！":
                print("试卷已提交，尝试重新拉取试卷")
            else:
                print("出现错误:")
                traceback.print_exc()
                input("输入回车结束程序：")

    if input("刷题成功！如需保存本次配置输入1") == "1":
        # 如果不需要记住账号相关配置
        if not StrUtil.str_to_bool(config["是否记住账号相关配置"]):
            config["豆号"] = ""
            config["密码"] = ""
            config["课程码"] = ""
        # 如果不需要记住刷题相关配置
        elif not StrUtil.str_to_bool(config["是否记住刷题相关配置(包括刷题入口细分项)"]):
            config["刷题入口"] = ""
            config["刷题次数"] = ""
            config["正确率"] = ""
            config["每道题刷题的时间"] = ""
            config["刷题入口"] = True
            config["刷题入口地址"] = ""
            config["专项技能型刷到100%是否继续刷"] = False
        # 同步配置
        configInfo.synchronization(config, False, False)
except requests.exceptions.ProxyError as e:
    print("无法链接到代理，请检查是否退出vpn或其他代理程序，再重新启动本程序！")
except requests.exceptions.ConnectionError as e:
    print("无法链接网络，请检查是否链接网络，再重新启动本程序！")
# except Exception as e:
#     print("出现错误:")
#     traceback.print_exc()
#     input("输入回车结束程序：")
