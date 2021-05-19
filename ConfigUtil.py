# -*- coding: UTF-8 -*-
import configparser
import os


class configInfo:
    template = {}
    config = configparser.ConfigParser()
    fileName = ""
    encoding = ""

    def __init__(self, fileName: str, template: dict, encoding: str = "utf-8-sig"):
        self.template = template
        self.fileName = fileName
        self.encoding = encoding
        # 读取配置文件
        if os.path.exists(fileName):
            self.config.read(fileName, encoding=encoding)
            # 验证模板里的 文件里是否都拥有 没有则添加
            self.synchronization(template, True)
        else:
            # 写入模板数据
            self.synchronization(template)

    def get_dic(self):
        result = {}
        for section in self.config.sections():
            options = self.config.options(section)
            result[section] = {}
            for options in options:
                result[section][options] = self.config.get(section, options)
        return result

    def get_dic_not_section(self):
        result = {}
        for section in self.config.sections():
            options = self.config.options(section)
            for options in options:
                result[options] = self.config.get(section, options)
        return result

    def get_list(self):
        result = []
        for section in self.config.sections():
            options = self.config.options(section)
            for options in options:
                result.append(self.config.get(section, options))
        return result

    def save(self):
        self.config.write(open(self.fileName, 'w', encoding=self.encoding))

    # 传入对象同步config
    def synchronization(self, obj: dict, addNot: bool = False, haveSection: bool = True):
        if addNot:
            if haveSection:
                # 验证obj里的 文件里是否都拥有 没有则添加
                for objKey in obj.keys():
                    if objKey not in self.config.sections():
                        self.config.add_section(objKey)
                    for templateObjectKey in obj[objKey].keys():
                        if templateObjectKey not in self.config.options(objKey):
                            self.config.set(objKey, templateObjectKey, str(obj[objKey][templateObjectKey]))
            else:
                for section in self.config.sections():
                    for objKey in obj.keys():
                        if objKey in self.config.options(section):
                            self.config.set(section, objKey, obj[objKey])
                        else:
                            if "其他" not in self.config.sections():
                                self.config.add_section("其他")
                            self.config.set("其他", objKey, str(obj[objKey]))
        else:
            if haveSection:
                # 写入模板数据
                for objKey in obj.keys():
                    self.config.add_section(objKey)
                    for templateObjectKey in obj[objKey].keys():
                        self.config.set(objKey, templateObjectKey, str(obj[objKey][templateObjectKey]))
            else:
                for section in self.config.sections():
                    for objKey in obj.keys():
                        if objKey in self.config.options(section):
                            self.config.set(section, objKey, str(obj[objKey]))
        self.save()

    def set(self, section: str, option: str, value: str):
        self.config.set(section, option, value)
