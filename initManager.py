def initManager(host='0.0.0.0', port=23333, password='',isManager=False, obj=None,):
    from multiprocessing.managers import BaseManager    
    class Manager(BaseManager):
        pass
    if isManager:
        def getObj():
            return obj
        obj = obj
        Manager.register('getObj', getObj)
        manager = Manager(address=(host, port),authkey=bytes(password, encoding='utf8'))
        manager.start()
        obj = manager.getObj()    
    else:
        Manager.register('getObj')
        manager = Manager(address=(host, port),authkey=bytes(password, encoding='utf8'))
        manager.connect()
        obj = manager.getObj()
    return obj
