import json
import random
import re
import time

import execjs

import RequestUtil
import StrUtil
import UrlUtil


def get_page_sub_href(page):
    # 获取提交试卷的地址 并返回
    return re.findall('<aid="putIn"href="javascript:void\(0\);"data="(.*?)"title=""',
                      StrUtil.formatting(page.text))[0]


class kgcRequest:
    session = RequestUtil.session({
        "http://tiku.kgc.cn/testing/error": "课工场页面异常"
    })

    # kgc网站上的路径
    urls = UrlUtil.regionUrl("http", "tiku.kgc.cn", "80", {
        "my_exam_js": "resources/V12.0.0.5/js/myexam.js"
    })

    # kgc网站上的请求结果集合
    results = {

    }

    kgcData = {
        "kgc_index_path": "",
        "entry_name": "",
        "entry_href": "",
        "get_paper_href": "",
        "100%go_on": True,
        "auto_choice_get_paper_href": True,
        "do_time": "",
        "last_data": ["", ""]
    }

    def __init__(self, kgcData: dict):
        for dataKey in self.kgcData.keys():
            try:
                self.kgcData[dataKey] = kgcData[dataKey]
            except KeyError:
                kgcData[dataKey] = ""
        kgc_index = self.session.get(self.kgcData["kgc_index_path"])
        if kgc_index.status_code == 200:
            if '对应的passport不存在' not in kgc_index.text:
                self.urls.put("index", self.kgcData["kgc_index_path"])
                self.results[self.urls.get("index")] = kgc_index
                # 加载js
                self.load_js()
                # 加载查询刷题数的url
                self.load_today_question_count_url(kgc_index)
                # 加载我的历史地址
                self.load_history_href(kgc_index)
            else:
                raise RequestUtil.RequestUtilError
    def reload(self, kgc_index_path: str):
        self.kgcData["kgc_index_path"] = kgc_index_path
        self.__init__(self.kgcData)

    # 加载入口 返回加载好的入口名
    def load_entry(self, choiceEntry=None, kgc_index_result=None):
        if choiceEntry is None:
            choiceEntry = self.kgcData["entry_name"]
        if kgc_index_result is None:
            kgc_index_result = self.results[self.urls.get("index")]

        class entry:
            name = ""
            href = ""

            def __init__(self, entry_block):
                self.name = re.findall('<spanclass="test_list_name">(.*?)<imgsrc=', entry_block)[0]
                self.href = re.findall('<spanclass="test_list_go"><a.+href="(.*?)">进入</a>', entry_block)[0]

        print("正在加载刷题入口。。。")
        # 获取所有参数入口块
        entry_blocks = re.findall('<divclass="test_listitem\\d">(.*?)</div>', StrUtil.formatting(kgc_index_result.text))
        # 入口对象
        entryObjects = []
        for entryBlock in entry_blocks:
            entryObjects.append(entry(entryBlock))
            # 如果地址不在a链接
            last_entryObject = entryObjects[len(entryObjects) - 1]
            if last_entryObject.href == "javascript:void(0);":
                last_entryObject.href = re.findall('<spanclass="test_list_go"><a.+data="(.*?)"', entryBlock)[0]

        # 遍历入口名看有没有和传入入口名一样的
        for entryObject in entryObjects:
            if entryObject.name == choiceEntry:
                self.kgcData["entry_name"] = entryObject.name
                self.kgcData["entry_href"] = entryObject.href
                return entryObject.name

        # 循环完了还是没有
        print("请选择入口：")
        print("序号\t入口名")
        for index in range(len(entryObjects)):
            print(str(index + 1) + "\t" + entryObjects[index].name)
        while True:
            try:
                entryObject = entryObjects[int(input("请选择：")) - 1]
                self.kgcData["entry_name"] = entryObject.name
                self.kgcData["entry_href"] = entryObject.href
                return entryObject.name
            except ValueError:
                print("请输入数字！")
            except IndexError:
                print("请输入1-" + str(len(entryObjects)) + "范围的数字！")

    # 根据入口加载获取试卷的地址
    def load_get_paper_href(self):
        # 获取试卷之前先判断是否加载入口过
        if self.kgcData["entry_name"] == "" and self.kgcData["entry_href"] == "":
            print("错误！：未加载入口")
            self.load_entry()
        # 请求入口
        entry_result = self.session.get(self.kgcData["entry_href"])
        if entry_result.url == '':
            raise IndexError("list index out of range")
        else:
            # 判断入口是否直接进入试卷(直接进入试卷代表是模拟真题型)
            if len(re.findall('<p class="f14">考试剩余时间</p>', entry_result.text)) == 0:
                # 入口块类
                class entryBlock:
                    enter_fun_name = ""
                    enter_fun_arguments = []
                    data = []
                    a_id = 0
                    title = ""

                    def __init__(self, enter_fun_name, enter_fun_arguments, title=""):
                        self.enter_fun_name = enter_fun_name
                        self.enter_fun_arguments = enter_fun_arguments
                        self.title = title

                # 转化后的请求入口
                format_entry_result = StrUtil.formatting(entry_result.text)
                # 获取所有一级入口 进入测试 执行的js方法
                do_js_funs = re.findall('javascript:(.*?);?"', format_entry_result)
                # 获取执行的方法名
                do_js_fun_name = re.findall('(.*?)\(', do_js_funs[0])[0]
                # 如果为专项技能型 进入测试 执行的js方法会多匹配到一个添加二级入口方法
                if do_js_fun_name == "percentAlert":
                    do_js_funs = do_js_funs[:-1]
                # 获取function块
                functions = re.findall("function\s+.+\(.+\)\{[\s\S]*?\}", entry_result.text)
                # 定义script块
                script = ""
                # 使用的方法
                use_fun = [do_js_fun_name, "percentOutlineAlert", "percentChapterAlert"]
                # 排除未使用方法
                index = 0
                length = len(functions)
                while index < length:
                    if re.findall('function\s*(.*?)\(', functions[index])[0] not in use_fun:
                        del functions[index]
                        index -= 1
                        length -= 1
                    index += 1
                for function in functions:
                    attr_data = re.findall('\$\("#(.*?)"\).attr\("(.*?)"\)', function)
                    if len(attr_data) > 0:
                        attr_data = attr_data[0]
                    func = function
                    if len(attr_data) > 0:
                        func = function.replace("){", "," + attr_data[1] + "){"). \
                            replace('$("#' + attr_data[0] + '").attr("' + attr_data[1] + '")', "data")
                    func = func.replace("window.location.href=", "return ")
                    func = func.replace("var data =", "return ")
                    script += "\n" + func
                function_names = re.findall('function\s+(.*?)\(', script)
                script = execjs.compile(script)
                # 获取方法可能性的拼接字符串
                function_names_joint = ""
                for index in range(len(function_names)):
                    if index != 0:
                        function_names_joint += "|"
                    function_names_joint += function_names[index]
                # 查找所有测试方法入口对象 (当前包含一级入口)
                entryBlocks = []
                for do_js_fun in do_js_funs:
                    name = re.findall('(.*?)\(', do_js_fun)[0]
                    try:
                        arguments = re.findall('[' + function_names_joint + ']\((.*?)\)', do_js_fun)[0].split(",")
                    except re.error:
                        print()
                    entryBlocks.append(entryBlock(name, arguments))
                if do_js_fun_name == "unitExam":
                    # 加载data
                    data_s = re.findall('data="(.*?)"title="进入测试"', format_entry_result)
                    for index in range(len(data_s)):
                        entryBlocks[index].enter_fun_arguments.append(data_s[index])
                elif do_js_fun_name == "percentAlert":
                    # 获取所有a_id data title percent
                    a_data_title_percent_s = re.findall(
                        ';position:relative"><aid="(.*?)"href="#"title=""class="no-sj"data="(.*?)"'
                        'style="padding-left:30px">(.*?)</a><p><spanstyle="width:(.*?)"></span>', format_entry_result)
                    # 将所有a_id 和 data加入口类块
                    for index in range(len(a_data_title_percent_s)):
                        entryBlocks[index].a_id = a_data_title_percent_s[index][0]
                        entryBlocks[index].data = a_data_title_percent_s[index][1].split(",")
                        entryBlocks[index].title = a_data_title_percent_s[index][2] + "\t" + \
                                                   a_data_title_percent_s[index][3]
                # 二级入口点击事件的js代码块
                skillList_click_js_block = ""
                # 二级入口的方法名
                skillList_fun_name = ""

                # 加载获取二级入口地址的js方法
                def load_skill_list_click_js_block():
                    nonlocal skillList_click_js_block
                    nonlocal skillList_fun_name
                    print("正在加载专项技能型的二级入口。。。。")
                    # 获取到二级入口点击事件的js代码块
                    skillList_click_js_block = re.findall('if\s?\(pos\s?!=\s?-1\)\s?\{'
                                                          '[\s\S]*'
                                                          '\}[\s\t\n\r]*'
                                                          'obj\.toggleClass\("yes-sj"\);[\s\t\n\r]*'
                                                          '\}[\s\t\n\r]*'
                                                          '\}[\s\t\n\r]*'
                                                          '\}\);[\s\t\n\r]*'
                                                          '[\s\t\n\r]*\}[\s\t\n\r]?else[\s\t\n\r]?(\{'
                                                          '[\s\S]*'
                                                          '\})[\s\t\n\r]*'
                                                          '\}[\s\t\n\r]*'
                                                          '\$\(this\)\.toggleClass\("yes-sj"\);',
                                                          entry_result.text)[0]
                    # 二次处理二级入口点击事件的js代码
                    # 将代码块转化为方法
                    skillList_click_js_block = "\nfunction click(a_id,data){\r" + skillList_click_js_block[
                                                                                  1:] + "\r"
                    # 将js代码拆解为一行一行
                    skillList_click_js_block_lines = re.findall('\n(.*?)\r', skillList_click_js_block)

                    # 在集合中删除一对指定字符
                    def remove_pair(char, list_, start_index):
                        char_dic = {
                            "{": "}",
                            "[": "]",
                            "<": ">",
                            "(": ")",
                        }
                        # 删除之前先判断当前行是否带有指定字符
                        if char in list_[start_index]:
                            index = start_index + 1
                            deep = 0
                            while index < len(list_):
                                if char in list_[index] and char_dic[char] not in list_[index]:
                                    deep += 1
                                elif char_dic[char] in list_[index] and deep == 0 and True if list_[index].find(
                                        char) == -1 \
                                        else list_[index].find(char_dic[char]) < list_[index].find(char):
                                    result_index = [index]
                                    # 如果要移除的行内还有指定字符
                                    if char in list_[index]:
                                        for result_index_ in remove_pair(char, list_, index):
                                            result_index.append(result_index_)
                                    # 返回需要删除的下标
                                    return result_index
                                elif char_dic[char] in list_[index] and char not in list_[index]:
                                    deep -= 1
                                index += 1

                    # 排除带有jquery的防报错
                    skillList_click_js_block_lines_index = 0
                    skillList_click_js_block_lines_length = len(skillList_click_js_block_lines)
                    while skillList_click_js_block_lines_index < skillList_click_js_block_lines_length:
                        # 如果当前行带有$.ajax(
                        if "$.ajax(" in skillList_click_js_block_lines[skillList_click_js_block_lines_index]:
                            del_index = remove_pair(
                                "(", skillList_click_js_block_lines, skillList_click_js_block_lines_index)
                            for i in del_index:
                                skillList_click_js_block_lines[i] = skillList_click_js_block_lines[i].replace(
                                    ")", "")

                            # 将$.ajax 替换为 return
                            skillList_click_js_block_lines[skillList_click_js_block_lines_index] = \
                                skillList_click_js_block_lines[skillList_click_js_block_lines_index].replace(
                                    "$.ajax(", "return")
                        # 如果当前行带有$
                        elif "$" in skillList_click_js_block_lines[skillList_click_js_block_lines_index]:
                            if "{" in skillList_click_js_block_lines[skillList_click_js_block_lines_index]:
                                del_index = remove_pair("{", skillList_click_js_block_lines,
                                                        skillList_click_js_block_lines_index)
                                for index in range(len(del_index)):
                                    if index < len(del_index) - 1:
                                        # 删除当前行
                                        del skillList_click_js_block_lines[del_index[index]]
                                        skillList_click_js_block_lines_length -= 1
                                        skillList_click_js_block_lines_index -= 1
                                    skillList_click_js_block_lines[del_index[index]] = \
                                        skillList_click_js_block_lines[del_index[index]].replace("}", "")
                            # 删除当前行
                            del skillList_click_js_block_lines[skillList_click_js_block_lines_index]
                            skillList_click_js_block_lines_length -= 1
                            skillList_click_js_block_lines_index -= 1
                        # 如果当前行带有//注释
                        elif StrUtil.formatting(
                                skillList_click_js_block_lines[
                                    skillList_click_js_block_lines_index]).startswith("//"):
                            # 删除当前行
                            del skillList_click_js_block_lines[skillList_click_js_block_lines_index]
                            skillList_click_js_block_lines_length -= 1
                            skillList_click_js_block_lines_index -= 1
                        skillList_click_js_block_lines_index += 1
                    # 查找出申明的变量
                    skillList_click_js_block_variables = ["a_id", "data"]
                    for skillList_click_js_block_line in skillList_click_js_block_lines:
                        re_result = re.findall('var\s*(\w+)\s*=\s*',
                                               StrUtil.formatting(skillList_click_js_block_line))
                        if len(re_result) != 0:
                            skillList_click_js_block_variables.append(re_result[0])
                    # 移除使用未申明变量的代码行
                    skillList_click_js_block_lines_index = 0
                    skillList_click_js_block_lines_length = len(skillList_click_js_block_lines)
                    while skillList_click_js_block_lines_index < skillList_click_js_block_lines_length:
                        re_results = re.findall('(\w+)\s*[=].*;',
                                                StrUtil.formatting(skillList_click_js_block_lines[
                                                                       skillList_click_js_block_lines_index]))
                        if len(re_results) > 0:
                            for re_result in re_results:
                                if re_result not in skillList_click_js_block_variables and not re_result.startswith(
                                        "var"):
                                    # 移除当前行
                                    del skillList_click_js_block_lines[skillList_click_js_block_lines_index]
                                    skillList_click_js_block_lines_index -= 1
                                    skillList_click_js_block_lines_length -= 1
                                    break
                        re_results = re.findall('(\w+)\s*[.\[].*;',
                                                StrUtil.formatting(skillList_click_js_block_lines[
                                                                       skillList_click_js_block_lines_index]))
                        if len(re_results) > 0:
                            for re_result in re_results:
                                if re_result not in skillList_click_js_block_variables:
                                    # 移除当前行
                                    del skillList_click_js_block_lines[skillList_click_js_block_lines_index]
                                    skillList_click_js_block_lines_index -= 1
                                    skillList_click_js_block_lines_length -= 1
                        re_results = re.findall('[+]+(\w+)\s*.*;',
                                                StrUtil.formatting(skillList_click_js_block_lines[
                                                                       skillList_click_js_block_lines_index]))
                        skillList_click_js_block_lines_index += 1
                    # 一行一行的js代码合并
                    skillList_click_js_block = ""
                    for skillList_click_js_block_line in skillList_click_js_block_lines:
                        skillList_click_js_block += skillList_click_js_block_line
                    skillList_click_js_block = execjs.compile(skillList_click_js_block)
                    # 获取二级入口的方法名
                    skillList_fun_name = re.findall("html\+='<aid=\"unitexam\"href=\"javascript:(.*?)\(",
                                                    format_entry_result)[0]

                # 根据入口对象获取二级入口对应的入口对象集合
                def get_skill_list_entry_block_s(entry_block):
                    # 获取请求二级入口的路径
                    url = skillList_click_js_block.call("click", entry_block.a_id,
                                                        entry_block.data)["url"]
                    # 请求二级入口
                    skillListResult = self.session.get(url)
                    skillList = json.loads(skillListResult.text)
                    skill_list_entry_block_s = []
                    for skill in skillList:
                        # 根据二级入口创建入口对象
                        skill_list_entry_block_s.append(entryBlock(skillList_fun_name,
                                                                   [skill['percent'], entry_block.data[0], skill["id"]],
                                                                   "\t" + skill["name"] + "\t" + str(
                                                                       skill["percent"]) + "%"))
                    return skill_list_entry_block_s

                # 判断是否自动选择入口地址
                if self.kgcData["auto_choice_get_paper_href"]:
                    choose_entry_block = ""
                    # 判断如果为课程复习型 或 为专项技能型且到100%继续刷
                    if do_js_fun_name == "unitExam" or (
                            do_js_fun_name == "percentAlert"
                            and self.kgcData["100%go_on"]):
                        choose_entry_block = entryBlocks[random.randint(0, len(entryBlocks) - 1)]
                    elif do_js_fun_name == "percentAlert" and not self.kgcData["100%go_on"]:
                        load_skill_list_click_js_block()
                        # 找到第一个不为100%的
                        for entryBlock_ in entryBlocks:
                            if int(re.findall("\t(.*?)%", entryBlock_.title)[0]) != 100:
                                # 判断当前入口的二级入口是否有不为100%(因为kgc有bug)
                                skill_list_entry_block_s = get_skill_list_entry_block_s(entryBlock_)
                                # 是否全为100%
                                is_all_100 = True
                                for skill_list_entry_block in skill_list_entry_block_s:
                                    if int(re.findall("\t.*\t(.*?)%", skill_list_entry_block.title)[0]) != 100:
                                        is_all_100 = False
                                        choose_entry_block = skill_list_entry_block
                                        break
                                if not is_all_100:
                                    choose_entry_block = entryBlock_
                                    break
                                # 如果全为100%
                                else:
                                    choose_entry_block = entryBlocks[0]

                    try:
                        get_paper_href = script.call(choose_entry_block.enter_fun_name,
                                                     *choose_entry_block.enter_fun_arguments)
                    except AttributeError:
                        print()
                    self.kgcData["get_paper_href"] = get_paper_href
                    return self.kgcData["get_paper_href"]
                # 如果不是自动选择入口地址
                else:
                    # 判断刷题入口地址是否有匹配的
                    if self.kgcData["get_paper_href"] != "":
                        for entryBlock_ in entryBlocks:
                            get_paper_href = script.call(entryBlock_.enter_fun_name, *entryBlock_.enter_fun_arguments)
                            if self.kgcData["get_paper_href"] == get_paper_href:
                                self.kgcData["get_paper_href"] = get_paper_href
                                return self.kgcData["get_paper_href"]
                    # 没有匹配的
                    # 判断如果为专项技能型
                    if do_js_fun_name == "percentAlert":
                        load_skill_list_click_js_block()
                        # 循环请求二级入口
                        index = 0
                        length = len(entryBlocks)
                        while index < length:
                            skill_list_entry_block_s = get_skill_list_entry_block_s(entryBlocks[index])
                            for skill_list_entry_block in skill_list_entry_block_s:
                                # 判断刷题入口地址是否有匹配的
                                if self.kgcData["get_paper_href"] != "":
                                    get_paper_href = script.call(skill_list_entry_block.enter_fun_name,
                                                                 *skill_list_entry_block.enter_fun_arguments)
                                    if self.kgcData["get_paper_href"] == get_paper_href:
                                        self.kgcData["get_paper_href"] = get_paper_href
                                        return self.kgcData["get_paper_href"]
                                # 将二级入口加人入口集合
                                entryBlocks.insert(index + 1, skill_list_entry_block)
                            length += len(skill_list_entry_block_s)
                            index += 1 + len(skill_list_entry_block_s)
                        print("刷题刷题入口地址失效")
                    # 判断如果为课程复习型
                    elif do_js_fun_name == "unitExam":
                        print("刷题入口地址失效")
                        # 加载title
                        titles = re.findall('<li><span>(.*?)</span><aid="unitexam"', format_entry_result)
                        for index in range(len(titles)):
                            entryBlocks[index].title = titles[index]
                    else:
                        raise Exception("出现未知课程!请联系作者添加!")

                    print("请选择课程：")
                    print("序号\t课程名")
                    for index in range(len(entryBlocks)):
                        print(str(index + 1) + "\t" + entryBlocks[index].title)
                    while True:
                        try:
                            case = int(input("请选择：")) - 1
                            if 0 <= case < len(entryBlocks):
                                self.kgcData["get_paper_href"] = script.call(entryBlocks[case].enter_fun_name,
                                                                             *entryBlocks[case].enter_fun_arguments)
                            else:
                                raise IndexError
                            return self.kgcData["get_paper_href"]
                        except ValueError:
                            print("请输入数字！")
                        except IndexError:
                            print("请输入1-" + str(len(entryBlocks)) + "范围的数字！")
            else:
                self.kgcData["get_paper_href"] = self.kgcData["entry_href"]
                return self.kgcData["get_paper_href"]

    # 根据获取试卷的地址加载试卷 返回试卷
    def load_test_paper(self, get_paper_href=None):
        if get_paper_href is None:
            get_paper_href = self.kgcData["get_paper_href"]
        # 测试获取试卷的地址是否可用
        test_paper = self.session.get(get_paper_href)
        if test_paper.status_code != 200:
            raise Exception("获取试卷的地址失效或网络错误！")
        self.results["test_page"] = test_paper
        # 返回试卷
        return test_paper

        # 将提交地址加入urls
        # self.urls.put("current_sub_href", sub_href)
        # return self.kgcData["current_page_code"]

    # 加载试卷试题分析
    def load_solutions_paper(self, sub_test_paper_result):
        if sub_test_paper_result["result"]:
            # 获取到试卷报告页面
            report_page_result = self.session.get(self.urls.get("go_back_url"))
            # 获取到试卷分析地址
            solutions_href = re.findall('>查看报告</a><ahref="(.*?)"title=""[\s\S]*>查看解析</a>',
                                        StrUtil.formatting(report_page_result.text))[0]
            return self.session.get(solutions_href)
        else:
            raise Exception("提交试卷,未知错误！")

    # 加载答案
    def load_answer(self, solutions_paper=None):
        if solutions_paper is None:
            solutions_paper = self.load_solutions_paper(self.sub_test_paper())
        # 获取所有答案块
        subjects = re.findall(r'<ulclass="sec2grays">(.*?)</ul><divclass="sec3reportfont-yaheif14strong">',
                              StrUtil.formatting(solutions_paper.text))
        # 获取所有题目id
        # 答案和获取每道题的正确答案并填入题目信息数组
        correctAnswers = []
        for i, su in enumerate(subjects):
            questionAnswers = re.findall(
                r'<lic?l?a?s?s?=?"?g?r?e?e?n?"?><pre><span>([A-Z]):</span><imagestyle="vertical-align:middle"src="('
                r'.*?)"/></pre>',
                su)
            for index in range(len(questionAnswers)):
                questionAnswers[index] = list(questionAnswers[index])
            answer_li = re.findall(r'<liclass="green"><pre><span>[A-Z]:</span>', su)
            an = []
            # 多选题的可能性
            if len(answer_li) > 1:
                for answer in answer_li:
                    an.append(re.findall(r"<span>(.*):</span>", answer)[0])
                correctAnswers.append(an)
            # 单选题的可能性
            else:
                an.append(re.findall(r"<span>(.*):</span>", answer_li[0])[0])
                correctAnswers.append(an)

        # 将答案转成01234
        answers_num_str = []
        for i in range(len(correctAnswers)):
            if len(correctAnswers[i]) == 1:
                answers_num_str.append(str(ord(correctAnswers[i][0].upper()) - 65))
            else:
                j = ""
                for anwer in correctAnswers[i]:
                    j += str(ord(anwer.upper()) - 65) + ","
                answers_num_str.append(j[:-1])

        return answers_num_str

    # 问题数据类
    class question_data:
        paper_code = ""
        question_id = ""
        sub_question_id = ""
        question_index = ""
        question_type = ""

        def __init__(self, paper_code, question_id, sub_question_id,
                     question_index, question_type):
            self.paper_code = paper_code
            self.question_id = question_id
            self.sub_question_id = sub_question_id
            self.question_index = question_index
            self.question_type = question_type

    # 加载问题数据集合
    def load_question_data(self, test_paper=None):
        if test_paper is None:
            test_paper = self.load_test_paper()
        # 获取所有题数据块
        data_s = list(set(re.findall(r'<dddata="(.*?)">', StrUtil.formatting(test_paper.text))))
        data = []
        # 循环将题库数据块转化为问题数据对象
        for index in range(len(data_s)):
            data = data_s[index].split(",")
            data_s[index] = self.question_data(data[1], data[2], data[3], data[4], data[5])
        # 将data_s填入last_data
        self.kgcData["last_data"][0] = data[0]
        self.kgcData["last_data"][1] = data[1]
        # 排序
        for index_ in range(len(data_s) - 1):
            for index in range(len(data_s) - index_ - 1):
                if int(data_s[index].question_index) > int(data_s[index + 1].question_index):
                    temp_data = data_s[index]
                    data_s[index] = data_s[index + 1]
                    data_s[index + 1] = temp_data
        return data_s

    # 加载查询刷题数的url
    def load_today_question_count_url(self, kgc_index_result=None):
        if kgc_index_result is None:
            kgc_index_result = self.results[self.urls.get("index")]
        try:
            today_question_count_url = \
                re.findall('\.val\(\'\'\);\$\.ajax\(\{url:"(.*?)",', StrUtil.formatting(kgc_index_result.text))[0]
        except IndexError:
            print()
        if self.session.get(today_question_count_url).status_code == 200:
            self.urls.put("today_question_count_url", today_question_count_url)
        else:
            raise Exception("网络异常")

    # 加载我的历史地址
    def load_history_href(self, kgc_index_result=None):
        if kgc_index_result is None:
            kgc_index_result = self.results[self.urls.get("index")]
        history_href = \
            re.findall('<liseq="2"><ahref="(.*?)"', StrUtil.formatting(kgc_index_result.text))[0]
        if self.session.get(history_href).status_code == 200:
            self.urls.put("history_href", history_href)
        else:
            raise Exception("网络异常")

    # 加载我的历史页面
    def load_history_page(self):
        history_page_result = self.session.get(self.urls.get("history_href"))
        if history_page_result.status_code != 200:
            self.load_history_href()
            history_page_result = self.session.get(self.urls.get("history_href"))
        return history_page_result

    # 获取对应试卷再做一遍页面
    def get_again_answer_page(self, test_paper=None):
        if test_paper is None:
            test_paper = self.load_test_paper()
        # 加载我的历史
        history_page_result = self.load_history_page()
        # 获取进入再做一遍页面的方法名
        again_answer_fun_name = re.findall('查看报告</a><ahref="javascript:(.*?)\(',
                                           StrUtil.formatting(history_page_result.text))[0]
        # 获取进入再做一遍页面的方法
        again_answer_fun = re.findall('function ' + again_answer_fun_name + "[\s\S]+?}", history_page_result.text)[0]
        again_answer_fun = again_answer_fun.replace("location.href =", "return ")
        again_answer_fun = execjs.compile(again_answer_fun)
        # 获取试卷id
        paper_id = re.findall('<aid="putIn"href="javascript:void\(0\);"'
                              'data=".*?/([0-9]*?)"title=""class="f14restacenterpater"'
                              '>我要交卷</a>',
                              StrUtil.formatting(test_paper.text))[0]
        # 获取再做一遍页面的地址
        again_answer_href = again_answer_fun.call(again_answer_fun_name, *[paper_id, time.time()])
        again_answer_result = self.session.get(again_answer_href)
        if again_answer_result.status_code == 200:
            return again_answer_result
        else:
            raise Exception("网络错误！")

    # 输出答题数和正确率
    def print_today_question_count_url(self):
        print("正在查询答题数和正确率。。。")
        today_question_count_result = self.session.get(self.urls.get("today_question_count_url"))
        if today_question_count_result.status_code != 200:
            self.load_today_question_count_url()
            today_question_count_result = self.session.get(self.urls.get("today_question_count_url"))
        AnswerNum = json.loads(today_question_count_result.text)
        if AnswerNum["result"]:
            msgs = AnswerNum["msg"].split(";")
            print("累计答题数：" + msgs[0] + "\t实际答题数：" + msgs[1] + "\t正确率：" + msgs[2])
        else:
            print("今天还没有做题哟~加油！")

    # 提交试卷 返回转为json的结果
    def sub_test_paper(self, question_data_s, sub_data, test_paper=None):
        if test_paper is None:
            test_paper = self.load_test_paper()
        # 如果提交数据不为空就需要提交答案
        if len(sub_data) > 0:
            # 获取提交答案的地址
            sub_js = re.findall("\.length;(\$\.ajax\(\{url:[\s\S]+?),",
                                StrUtil.formatting(
                                    self.results[self.urls.get("my_exam_js")]
                                        .text))[0].replace("$.ajax({url:", "return ")
            sub_js = "var lastData=" + str(self.kgcData["last_data"]) + ";" + sub_js
            sub_js = sub_js.replace("\'", "\"")
            paramQuestionId = ""
            question_data_s_len = len(question_data_s)
            for index in range(question_data_s_len):
                paramQuestionId += question_data_s[index].question_id
                if index != question_data_s_len - 1:
                    paramQuestionId += ","

            sub_js = "var paramQuestionId=\"" + paramQuestionId + "\";" + sub_js
            sub_js = "function a(){" + sub_js
            sub_js += "}"
            sub_href = execjs.compile(sub_js).call("a")
            # 提交答案
            self.session.post(sub_href, data=sub_data)
        # 获取提交试卷地址
        sub_href = get_page_sub_href(test_paper)
        # 获取试卷id并填入data
        self.kgcData["current_page_code"] = sub_href.split("/")[-1].split("?")[0]
        # 提交试卷
        try:
            result = json.loads(self.session.post(sub_href).text)
        except json.decoder.JSONDecodeError as e:
            if "Expecting value: line" in str(e):
                raise Exception("重复提交！")
            else:
                raise e
        if result["result"]:
            self.urls.put("go_back_url", result["gobackUrl"])
            return result
        else:
            raise Exception("提交试卷,未知错误！")

    # 刷题 正确率
    def do_test_paper(self, accuracy=1):
        # 获取试卷
        test_paper = self.load_test_paper()
        # 提交的数据
        sub_data = {
            "psqId": [],
            "time": [],
            "uAnswers": []
        }
        # 获取问题数据
        question_data_s = self.load_question_data(test_paper)
        # 提交空卷
        sub_test_paper_result = self.sub_test_paper([], [], test_paper)
        # 获取试卷分析
        solutions_paper = self.load_solutions_paper(sub_test_paper_result)
        # 加载答案
        answers = self.load_answer(solutions_paper)
        # 题数
        question_num = len(answers)
        # 计算错题数
        F_num = int(question_num - accuracy * question_num)
        # 循环写入错题
        for i in range(int(F_num)):
            while True:
                ran = str(random.randint(0, 3))
                if ran != answers[i]:
                    answers[i] = ran
                    break
        # 判断每道题刷题时间
        do_time = self.kgcData["do_time"]
        if do_time == "":
            do_time = str(random.randint(10, 20))
        # 将问题数据填入sub_data
        for index in range(len(question_data_s)):
            sub_data["psqId"].append(question_data_s[index].sub_question_id)
            sub_data["time"].append(do_time)
            try:
                sub_data["uAnswers"].append(answers[index])
            except IndexError as e:
                print()
        # 获取再做一次
        again_answer = self.get_again_answer_page(test_paper)
        # 提交答卷
        sub_test_paper_result = self.sub_test_paper(question_data_s, sub_data, again_answer)
        # 返回是否成功
        return sub_test_paper_result["result"]

    def load_my_exam_js(self):
        self.results[self.urls.get("my_exam_js")] = \
            self.session.get(self.urls.get("my_exam_js"))
        return self.results[self.urls.get("my_exam_js")]

    def load_js(self):
        print("正在加载js")
        self.load_my_exam_js()
