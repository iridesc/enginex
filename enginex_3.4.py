import requests, re, time,random,os,traceback,json
from bs4 import BeautifulSoup
from multiprocessing import Process, Pool, Manager
from  retry import retry
from multiprocessing.managers import BaseManager

# #################### E setting #####################
timeout = 3
decorator = ' 下载'
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
logcache=''
# #################### E setting end #####################


class connectMerro(RuntimeError):
    def __init__(self,info):
        self.info=info
class kid():
    def __init__(self, keyword,page,Egap):
        self.keyword=keyword
        self.page = page
        self.Egap=Egap
        self.progress = 0

        self.lastacttime=0
        self.statu='waiting'
    #engine
    def active(self):
        self.lastacttime=time.time()
    #engine
    def is_active(self):
        return time.time()-self.lastacttime<self.Egap
class cachemanager(BaseManager):
    pass
class log():
    def __init__(self):
        self.logcache=''
    def make(self,log):
        if log!=self.logcache:
            print('-+-+-+-+-+-+-+-+-+-+-+-+-+-\n')
            print(log)
            self.logcache=log


def inittask(task):
    task['keyword'] = None
    task['page'] = None
    task['progress'] = 0
    task['done'] = False
    task['reslist']=[]
    return task

def resourceworm(xlist):
    @retry(delay=2, tries=3)
    def net(link):
        head = {
            'User-Agent': random.choice(UA)
        }
        r = requests.get(link, headers=head, timeout=10, allow_redirects=False)
        r.raise_for_status()
        return r


    weblink=xlist[0]
    task=xlist[1]

    # 获取页面html
    webhtml=''
    try:
        n=0
        status_code=302
        while status_code in [302,301] and n<4:
            r=net(weblink)
            status_code=r.status_code
            if status_code in [301, 302]:
                weblink=r.headers['location']
                n=n+1
            else:
                r.encoding=r.apparent_encoding
                webhtml=r.text
    except:
        pass


    if webhtml!='':
        # 获取html资源
        bd_r=re.compile(r'''pan\.baidu\.com[/\\]\S+?(?=['"“”‘’《》<>,，；;])''')
        th_r=re.compile(r'''thunder://[ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/=]+''')
        ed_r=re.compile(r'''ed2k://[\s\S]+?(?:[/])''')
        magnet_r=re.compile(r'''magnet:\?\S+?(?=['"“”‘’《》<>$()（）：])''')
        #print('提取资源')
        th = th_r.findall(webhtml)
        ed = ed_r.findall(webhtml)
        magnet = magnet_r.findall(webhtml)
        bd = bd_r.findall(webhtml)
        #print('提取成功')
        for i in th:
            if len(i)<800:
                l=task['reslist']
                l.append([i, weblink,'thunder'])
                task['reslist']=l
        for i in ed:
            if len(i) < 800:
                l = task['reslist']
                l.append([i, weblink, 'ed2k'])
                task['reslist'] = l
        for i in magnet:
            if len(i) < 800:
                l = task['reslist']
                l.append([i, weblink, 'magnet'])
                task['reslist'] = l
        for i in bd:
            if len(i) < 800:
                l = task['reslist']
                l.append([i, weblink, 'baidu'])
                task['reslist'] = l
    #更新statu
    task['progress']=2+ task['progress']

def cpu(task,pn):
    def getweblink(skey,page):
        #get baidu html
        url = 'http://www.baidu.com/s?'
        aa = {'wd': skey, 'pn': int(page) * 50, 'rn': 50}

        head = {
            'User-Agent': random.choice(UA)
        }
        try:
            r = requests.get(url, params=aa, headers=head, timeout=10)

            r.raise_for_status()

            r.encoding = r.apparent_encoding
            tag = BeautifulSoup(r.text, 'html.parser').find_all('h3', class_="t")
        except:
            tag=[]
        #获取链接
        return [BeautifulSoup(str(n), "html.parser").a['href'] for n in  tag]

    while True:
        time.sleep(10)
        if task['keyword']!=None and not  task['done']:
            keyword = task['keyword']
            page = task['page']
            #获取weblink
            weblinklist=getweblink(keyword + decorator,page)
            # 建立并开始wprmpool
            webworm_pool = Pool(pn)
            spsset = webworm_pool.map_async(func=resourceworm,
                                            iterable=[[link,task] for link in weblinklist])
            webworm_pool.close()
            # 检查是否超时
            try:
                spsset.get(timeout=60)
            except:
                webworm_pool.terminate()
            task['done']=True
        else:time.sleep(1)

def bootloader(enginename,task,cache):
    checktime = 0
    progressrecoder=0
    while True:

            #两秒交互一次
            t0 = time.time()
            if t0 - checktime > 2:
                checktime = time.time()
                # postdata
                if task['done']:
                    sucess=False
                    while not sucess:
                            cache.postres(enginename,task['keyword'],task['page'],task['reslist'])
                            # 重置task
                            task = inittask(task)
                            sucess=True

                # gettask
                elif task['keyword']==None:

                        kid=cache.gettask(enginename)
                        if kid != None:
                            task['keyword']=kid.keyword
                            task['page']=kid.page

                # updatestatu
                elif task['progress']!=progressrecoder:

                        cache.updateprogress(enginename,task['keyword'],task['page'],task['progress'])

                #active
                else:
                        cache.activeengine(enginename)

            else:
                time.sleep(0.2)

if __name__ == '__main__':
    logfile=log()
    starttime=0
    while True:
        if time.time()-starttime>2:
            try:
                starttime = time.time()

                # setting
                with open('./setting.json') as f:
                    setting=json.load(f)

                enginename=setting['enginename']
                password=setting['password']
                host=setting['host']
                port=setting['port']
                pn=setting['processnumber']
                decorator=setting['decorator']


                cachemanager.register('cacheobj')
                manager = cachemanager(address=(host, port), authkey=bytes(password,encoding='utf8'))

                manager.connect()
                cache = manager.cacheobj()

                task = inittask(Manager().dict())

                bootloader_P = Process(target=bootloader, args=(enginename, task, cache,))
                cpu_P = Process(target=cpu, args=(task,pn,))

                bootloader_P.start()
                cpu_P.start()
                logfile.make(
                    '--------engine-start-------' + \
                    '\ntime:' + time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()) + \
                    '\nhost:' + host + '\nengineneme:' + enginename + '\npassword:' + str(password) + \
                    '\nprocess:' + \
                    str(pn) + \
                    '\ndecorator:' + \
                    decorator + \
                    '\n'
                )
                #进程检测
                while True:
                    if bootloader_P.is_alive() and cpu_P.is_alive():
                        time.sleep(1)
                    else:
                        bootloader_P.terminate()
                        cpu_P.terminate()
                        logfile.make('connection down! reboot now!\n')
                        break
            except Exception as e:
                logfile.make('waiting for net connection!\n'+str(e)+'\n')
        else:time.sleep(1)
