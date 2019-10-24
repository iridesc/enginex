import re
import os
import time
import json
import random
import requests
import traceback
from bs4 import BeautifulSoup
from retry import retry
# from guppy import hpy
from multiprocessing import Pool, Queue, TimeoutError, cpu_count
from multiprocessing.managers import BaseManager


class RawRes:
    def __init__(self, keyword, reslink, weblink, restype):
        self.reslink = reslink
        self.weblink = weblink
        self.type = restype
        self.keyword = keyword
        self.filename = None
        self.filesize = 0

    def reslinkparser(self, parselink):
        def base64decode(link):
            link = link.split('//')[1]
            example = base64.b64decode(link)
            for i in ['utf-8', 'gbk', 'ascii', 'gb2312', 'GB18030', 'iso8859-1', 'utf-16', ]:
                try:
                    example = example.decode(encoding=i)[2:][:-2]
                    return example
                except:
                    pass

        parselink = parse.unquote(parselink)
        t = parselink.split(':')[0]
        filename = None
        size = 0
        try:
            if t == 'http':
                filename = parselink.split('/')[-1].split('?')[0]
            elif t == 'ftp':
                filename = parselink.split('/')[-1]
            elif t == 'magnet':
                if '&amp;' in parselink:
                    infolist = parselink.split('&amp;')
                else:
                    infolist = parselink.split('&')
                for info in infolist:
                    if info.split('=')[0] == 'dn':
                        filename = info.split('=')[1]
                    elif info.split('=')[0] == 'xl':
                        size = int(info.split('=')[1])
            elif t == 'ed2k':
                infolist = parselink.split('|')
                filename = infolist[2]
                size = int(infolist[3])
            elif t == 'thunder':
                filename, size = reslinkparser(base64decode(parselink))

        except Exception as e:
            pass
        self.filename = filename
        self.filesize = size / 1024 ** 2


class Task:
    def __init__(self, keyword, subtaskqueue):
        self.keyword = keyword
        self.statu = 'waiting'
        self.progress = 0
        self.subtask_done_counter = 0
        self.subtask_total_counter = 0
        self.reslist = []
        for page in range(DEEPTH):
            subtaskqueue.put(
                SubTask(
                    task_type='ParseTask',
                    keyword=keyword,
                    page=page
                )
            )
        self.last_active_time=time.time()
        makelog('Task inited {}'.format(self.keyword))

    def getdict(self):
        return {
            'keyword': self.keyword,
            'taskstatu': self.statu,
            'progress': self.progress,
            'statu': self.statu
        }

    def putrawres(self, rawres_list):
        def rawres_to_res(rawres):
            return Resourcetable(
                keyword=rawres.keyword,
                link=rawres.reslink,
                web=rawres.weblink,
                type=rawres.type,
                filename=rawres.filename,
                filesize=rawres.filesize
            )

        # 更新状态和进度
        self.subtask_done_counter += 1
        self.progress = self.subtask_done_counter*100/self.subtask_total_counter
        if self.subtask_done_counter == self.subtask_total_counter:
            self.statu = 'done'
        else:
            self.statu = 'digging'
        for rawres in rawres_list:
            self.reslist.append(rawres_to_res(rawres))
        # makelog('SubTask done! {}'.format(self.keyword))


class SubTask:
    def __init__(self, task_type: str, keyword: str, page: int, weblink=None):
        self.task_type = task_type
        self.keyword = keyword
        self.page = page
        if weblink == None and task_type == 'ParseTask':
            self.link = 'http://www.baidu.com/s?'
        elif task_type == 'MiniTask':
            self.link = weblink
        else:
            makelog('Task type error!')
            raise
        # makelog('SubTask inited:{}'.format(self.task_type))

    def do(self):
        @retry(tries=2)
        def net(link, params=None, allow_redirects=True):
            UA = [
                'User-Agent,Mozilla/5.0 (Macintosh; U; Intel Mac OS X 10_6_8; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
                'User-Agent,Mozilla/5.0 (Windows; U; Windows NT 6.1; en-us) AppleWebKit/534.50 (KHTML, like Gecko) Version/5.1 Safari/534.50',
                'User-Agent,Mozilla/5.0 (compatible; MSIE 9.0; Windows NT 6.1; Trident/5.0;',
                'User-Agent, Mozilla/5.0 (Macintosh; Intel Mac OS X 10.6; rv,2.0.1) Gecko/20100101 Firefox/4.0.1    ',
                'User-Agent,Mozilla/5.0 (Windows NT 6.1; rv,2.0.1) Gecko/20100101 Firefox/4.0.1',
                'User-Agent, Mozilla/5.0 (Macintosh; Intel Mac OS X 10_7_0) AppleWebKit/535.11 (KHTML, like Gecko) Chrome/17.0.963.56 Safari/535.11',
                'User-Agent, Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Maxthon 2.0)',
                'User-Agent, Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; The World)',
                'User-Agent, Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; Trident/4.0; SE 2.X MetaSr 1.0; SE 2.X MetaSr 1.0; .NET CLR 2.0.50727; SE 2.X MetaSr 1.0)',
                'User-Agent, Mozilla/4.0 (compatible; MSIE 7.0; Windows NT 5.1; 360SE)',
            ]

            head = {
                'User-Agent': random.choice(UA)
            }
            r = requests.get(
                link,
                headers=head,
                timeout=5,
                params=params,
                allow_redirects=allow_redirects
            )
            r.raise_for_status()
            return r

        def minitask():
            def get_source_code():
                sourcecode = ''
                try:
                    n = 0
                    status_code = 302
                    while status_code in [302, 301] and n < 3:
                        r = net(self.link, allow_redirects=False)
                        status_code = r.status_code
                        if status_code in [301, 302]:
                            self.link = r.headers['location']
                            n = n + 1
                        else:
                            r.encoding = r.apparent_encoding
                            # 收集网页源码
                            sourcecode = r.text
                except:
                    pass

                return sourcecode

            def get_rawres(sourcecode):
                # 匹配表达式
                th_r = re.compile(
                    r'''thunder://[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=]+''')
                ed_r = re.compile(r'''ed2k://[\s\S]+?(?:[/])''')
                magnet_r = re.compile(
                    r'''magnet:\?\S+?(?=['"“”‘’《》<>$()（）：])''')

                # 匹配资源
                rawres_list = []
                for res_container in [
                    [th_r.findall(sourcecode), 'thunder'],
                    [ed_r.findall(sourcecode), 'ed2k'],
                    [magnet_r.findall(sourcecode), 'magnet'],
                ]:
                    for reslink in res_container[0]:
                        if len(reslink) < 800:
                            rawres_list.append(
                                RawRes(
                                    self.keyword,
                                    reslink,
                                    self.link,
                                    res_container[1])
                            )
                return rawres_list
            st=time.time()
            sourcecode = get_source_code()
            rawres_list = get_rawres(sourcecode)
            # 找到任务并放入rawres
            CACHE.rawres_upload(self.keyword, rawres_list)
            # now_time=time.time()
            # makelog('MiniTask Done!  {} con_time:{} total_time:{}'.format(self.keyword,now_time-t,now_time-st,))

        def parsetask():
            def get_tags():
                params = {'wd': self.keyword+' 下载',
                          'process_number': int(self.page) * 50, 'rn': 50}

                try:
                    r = net(self.link, params=params)
                    r.encoding = r.apparent_encoding
                    tags = BeautifulSoup(r.text, 'html.parser').find_all(
                        'h3', class_="t")
                except:
                    makelog(traceback.format_exc())
                    tags = []

                return tags

            # 获取标签
            tags = get_tags()
            # 获取链接
            self.weblinklist = [BeautifulSoup(
                str(n), "html.parser").a['href'] for n in tags]
            # 上传SubTask
            CACHE.subtaskqueue_puts(
                self.keyword,
                [
                    SubTask(
                        task_type='MiniTask',
                        keyword=self.keyword,
                        page=self.page,
                        weblink=weblink
                    ) for weblink in self.weblinklist
                ]
            )

        # makelog('{} Start!'.format(self.task_type))

        if self.task_type == 'MiniTask':
            minitask()
        elif self.task_type == 'ParseTask':
            parsetask()
        else:
            makelog('Error unknow task{}'.format(self.task_type))



class cachemanager(BaseManager):
    pass


def makelog(log):
    print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + '>>>', log)


def loaddetting():
    global ENGINENAME, PASSWORD, HOST, PORT, PROCESSAMOUNT
    with open('./setting.json') as f:
        setting = json.load(f)

    ENGINENAME = setting['EngineName']
    PASSWORD = setting['Password']
    HOST = setting['Host']
    PORT = setting['Port']
    process_override = setting['ProcessOverride']
    PROCESSAMOUNT = int(cpu_count()*float(process_override))

    makelog(
        'load setting success:\nEngineName:{}\nPassword:{}\nHost:{}\nPort:{}\nProcessOverride:{}\nProcess:{}'.format(
            ENGINENAME,
            PASSWORD,
            HOST,
            PORT,
            process_override,
            PROCESSAMOUNT,
        )
    )


def config():
    makelog('Enginex Config :')
    setting = {
        'EngineName': None,
        'Password': None,
        'Host': '0.0.0.0',
        'Port': 23333,
        'ProcessOverride': 2.0,
    }
    try:
        usersetting = json.load(open('setting.json'))
    except:
        usersetting = setting

    for key, value in setting.items():
        v = input('please input {} \nrecomend: {}\ncurrent: {}:'.format(
            key, value, usersetting[key]))
        if v == '':
            setting[key] = usersetting[key]
        else:
            setting[key] = v

    json.dump(setting, open('setting.json', 'w'), ensure_ascii=False, indent=4)
    makelog('enginex config done!')


def subtask_pool_fuc(subtask):
    subtask.do()


if __name__ == '__main__':
    # 载入设置
    loaddetting()
    while True:
        makelog('Enginex 4.0 start !')
        try:
            # 连接到服务器
            cachemanager.register('cacheobj')
            manager = cachemanager(
                address=(HOST, PORT),
                authkey=bytes(PASSWORD, encoding='utf8')
            )
            manager.connect()
            CACHE = manager.cacheobj()
            makelog('Manager-x connected !')
            # 建立进程池
            task_pool = Pool(processes=PROCESSAMOUNT, maxtasksperchild=1)
            # 建立一个结果清理队列
            results = []
            applyed_count = PROCESSAMOUNT

            # 循环检查新任务
            engine_status_update_time = 0
            while True:
                now_time = time.time()
                if now_time - engine_status_update_time > 5:
                    engine_status_update_time = now_time
                    CACHE.activeengine(ENGINENAME)
                    # makelog('Update Enginex Status!')
                elif applyed_count == 0:
                    # 销毁pool返回 释放内存
                    t = time.time()
                    new_results = []
                    for result in results:
                        try:
                            # 取出来释放内存
                            result.get(timeout=0.01)
                            # 销毁成功则更新信号量
                            applyed_count += 1
                        except TimeoutError:
                            new_results.append(result)
                    if applyed_count > 0:
                        results = new_results
                        new_results = []
                        # makelog('Clean Pool ! {}'.format(applyed_count))

                elif not CACHE.subtaskqueue_empty() and applyed_count > 0:
                    # 尽可能的 取回任务 填满 pool
                    while not CACHE.subtaskqueue_empty() and applyed_count > 0:
                        # 将结果加入result列表 以便销毁释放内存
                        results.append(
                            task_pool.apply_async(
                                func=subtask_pool_fuc,
                                args=(CACHE.subtaskqueue_get(),)
                            )
                        )

                        # 更新pool的信号量
                        applyed_count -= 1
                    # makelog('Applyed ! {}'.format(applyed_count))
                else:
                    time.sleep(2)

        except Exception as e:
            makelog('Exception in main process! Reboot after 2s！\n' +
                    traceback.format_exc())
            time.sleep(2)
        
