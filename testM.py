import time



def initManager(isManager=False, obj=None,host='0.0.0.0', port=2335, password=''):
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

class People:
    def eat(self):
        print('eatting...')
        time.sleep(2)
        print('Done')

initManager(isManager=True, obj=People())
while True:
    time.sleep(1)
