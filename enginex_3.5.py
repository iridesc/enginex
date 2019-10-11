import requests
import re
import time
import random
import os
import traceback
import json
from bs4 import BeautifulSoup
from multiprocessing import Process, Pool, Manager
from retry import retry
from multiprocessing.managers import BaseManager

# #################### E setting #####################
# process pool 超时

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
TIMEOUT = 10
TIMES = 0
TIMER = 0
# #################### E setting end #####################


class connectMerro(RuntimeError):
    def __init__(self, info):
        self.info = info


class kid():
    def __init__(self, keyword, page, Egap):
        self.keyword = keyword
        self.page = page
        self.Egap = Egap
        self.progress = 0
        self.lastacttime = 0
        self.statu = 'waiting'

    # engine
    def active(self):
        self.lastacttime = time.time()

    # engine
    def is_active(self):
        return time.time() - self.lastacttime < self.Egap


class cachemanager(BaseManager):
    pass


def makelog(log):
    print(
        '\n-+-+-+-+-+-' +
        time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) +
        '-+-+-+-+-+-\n'+log
    )


def inittask(TASKCONTAINER):
    TASKCONTAINER['keyword'] = None
    TASKCONTAINER['page'] = None
    TASKCONTAINER['progress'] = 0
    TASKCONTAINER['done'] = False
    TASKCONTAINER['weblink_code'] = []
    TASKCONTAINER['reslist'] = []
    return TASKCONTAINER


def getsourcecode(xlist):
    @retry(delay=2, tries=3)
    def net(link):
        head = {
            'User-Agent': random.choice(UA)
        }
        r = requests.get(link, headers=head, timeout=10, allow_redirects=False)
        r.raise_for_status()
        return r

    weblink = xlist[0]
    TASKCONTAINER = xlist[1]

    # 获取页面html
    try:
        n = 0
        status_code = 302
        while status_code in [302, 301] and n < 4:
            r = net(weblink)
            status_code = r.status_code
            if status_code in [301, 302]:
                weblink = r.headers['location']
                n = n + 1
            else:
                r.encoding = r.apparent_encoding
                # 收集网页源码
                TASKCONTAINER_weblink_code = TASKCONTAINER['weblink_code']
                TASKCONTAINER_weblink_code.append([weblink, r.text])
                TASKCONTAINER['weblink_code'] = TASKCONTAINER_weblink_code
    except:
        pass
    # 更新statu
    TASKCONTAINER['progress'] = 2 + TASKCONTAINER['progress']


def loaddetting():
    global ENGINENAME, PASSWORD, HOST, PORT, PROCESSAMOUNT, DECORATOR, UNITAMOUNT
    with open('./setting.json') as f:
        setting = json.load(f)
    ENGINENAME = setting['enginename']
    PASSWORD = setting['password']
    HOST = setting['host']
    PORT = setting['port']
    PROCESSAMOUNT = int(setting['processnumber'])
    UNITAMOUNT = 2
    DECORATOR = setting['decorator']


def processor():
    
    def getweblink(skey, page):
        # get baidu html
        url = 'http://www.baidu.com/s?'
        aa = {'wd': skey, 'process_number': int(page) * 50, 'rn': 50}

        head = {
            'User-Agent': random.choice(UA)
        }
        try:
            r = requests.get(url, params=aa, headers=head, timeout=10)

            r.raise_for_status()

            r.encoding = r.apparent_encoding
            tag = BeautifulSoup(r.text, 'html.parser').find_all(
                'h3', class_="t")
        except:
            tag = []
        # 获取链接
        return [BeautifulSoup(str(n), "html.parser").a['href'] for n in tag]

    def parseres(TASKCONTAINER):
        # 匹配表达式
        bd_r = re.compile(
            r'''pan\.baidu\.com[/\\]\S+?(?=['"“”‘’《》<>,，；;])''')
        th_r = re.compile(
            r'''thunder://[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=]+''')
        ed_r = re.compile(r'''ed2k://[\s\S]+?(?:[/])''')
        magnet_r = re.compile(r'''magnet:\?\S+?(?=['"“”‘’《》<>$()（）：])''')
        for weblink_code in TASKCONTAINER['weblink_code']:
            weblink = weblink_code[0]
            source_code = weblink_code[1]
            # 匹配资源 并 收录
            for res_container in [
                [th_r.findall(source_code), 'thunder'],
                [ed_r.findall(source_code), 'ed2k'],
                [magnet_r.findall(source_code), 'magnet'],
                [bd_r.findall(source_code), 'baidu']
            ]:
                for res in res_container[0]:
                    if len(res) < 800:
                        l = TASKCONTAINER['reslist']
                        l.append([res, weblink, res_container[1]])
                        TASKCONTAINER['reslist'] = l

    global DECORATOR,TASKCONTAINER,PROCESSAMOUNT
    while True:
        if TASKCONTAINER['keyword'] != None and not TASKCONTAINER['done']:
            
            keyword = TASKCONTAINER['keyword']
            page = TASKCONTAINER['page']
            makelog('new task:{} - {}'.format(keyword, page))
            
            # 获取weblink
            weblink_list = getweblink(keyword + DECORATOR, page)
        
            
            # 建立并开始wprmpool
            web_worm_pool = Pool(PROCESSAMOUNT)
            spsset = web_worm_pool.map_async(
                func=getsourcecode,
                iterable=[[link, TASKCONTAINER] for link in weblink_list]
            )
            web_worm_pool.close()

            # 检查是否超时
            try:
                spsset.get(timeout=TIMEOUT)
            except:
                web_worm_pool.terminate()

            # for xlist in [[link, TASKCONTAINER] for link in weblink_list]:
            #     getsourcecode(xlist)
            
      

            # 解析资源 标记完成
            parseres(TASKCONTAINER)
            TASKCONTAINER['done'] = True

        else:
            time.sleep(0.1)


def syner():
    global CACHE, ENGINENAME, TASKCONTAINER, ET, ST,TIMER,TIMES
    ET=0
    checktime = 0
    progressrecoder = 0
    while True:
        # 0.5交互一次
        t0 = time.time()
        if t0 - checktime > 0.5:
            checktime = time.time()

            # 任务完成 上传数据
            if TASKCONTAINER['done']:
                sucess = False
                while not sucess:
                    CACHE.postres(
                        ENGINENAME, TASKCONTAINER['keyword'], TASKCONTAINER['page'], TASKCONTAINER['reslist'])
                    # 重置task
                    TASKCONTAINER = inittask(TASKCONTAINER)
                    sucess = True
                
               
                ET = time.time() - ST
                TIMER += ET
                TIMES +=1
                
                print('Preformance:{}'.format(TIMER/TIMES))


            # gettask
            elif TASKCONTAINER['keyword'] == None:
        
                ST = time.time()

                kid = CACHE.gettask(ENGINENAME)
                if kid != None:
                    TASKCONTAINER['keyword'] = kid.keyword
                    TASKCONTAINER['page'] = kid.page

            # updatestatu
            elif TASKCONTAINER['progress'] != progressrecoder:

                CACHE.updateprogress(
                    ENGINENAME, TASKCONTAINER['keyword'], TASKCONTAINER['page'], TASKCONTAINER['progress'])

            # 啥事都没有则打卡
            else:
                CACHE.activeengine(ENGINENAME)

        else:
            time.sleep(0.2)


if __name__ == '__main__':
    makelog('engine-start')
    starttime = 0
    while True:
        if time.time()-starttime > 2:
            try:
                starttime = time.time()

                # 载入设置
                loaddetting()
                makelog(
                    'load setting success:\n' +
                    'host:' + HOST +
                    '\nengineneme:' + ENGINENAME +
                    '\npassword:' + PASSWORD +
                    '\nprocess:' + str(PROCESSAMOUNT) +
                    '\ndecorator:' + DECORATOR
                )

                # 连接到服务器
                cachemanager.register('cacheobj')
                manager = cachemanager(
                    address=(HOST, PORT),
                    authkey=bytes(PASSWORD, encoding='utf8')
                )
                manager.connect()
                global CACHE, TASKCONTAINER
                CACHE = manager.cacheobj()

                # 获得一个ManagerDict对象 并初始化
                TASKCONTAINER = inittask(Manager().dict())

                # 定义引导进程 和 处理单元进程
                syner_process = Process(target=syner)
                processor_process = Process(target=processor)

                # 启动进程
                syner_process.start()
                processor_process.start()
                makelog('boot process success')
                # 进程检测
                while True:
                    if syner_process.is_alive() and processor_process.is_alive():
                        time.sleep(2)
                    elif not syner_process.is_alive():
                        syner_process.terminate()
                        makelog('syner_process down! reboot  process now!\n')
                        syner_process = Process(target=syner,)
                        syner_process.start()
                    else:
                        processor_process.terminate()
                        makelog('processor_process down! reboot process now!\n')
                        processor_process = Process(target=processor)
                        processor_process.start()

            except Exception as e:
                makelog('Exception in main process! reboot now！\n' + str(e))
                raise

        else:
            time.sleep(1)
