import json

def config():
    print('enginex config done!')
    data=json.load(open('setting.json'))

    for key,value in data.items():
        v=input('please input{} (default:{}):'.format(key,value))
        if v!='':
            data[key]=v
    json.dump(data,open('setting.json','w'),)
    print('enginex config done!')
if __name__ == '__main__':

    
    config