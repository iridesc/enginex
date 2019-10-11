import json

def config():
    data=json.load(open('setting.json'))

    for key,value in data.items():
        v=input('please input {} (current:{}):'.format(key,value))
        if v!='':
            data[key] = v
            
    json.dump(data,open('setting.json','w'),ensure_ascii=False,indent=4)
    print('enginex config done!')

if __name__ == '__main__':
    config()