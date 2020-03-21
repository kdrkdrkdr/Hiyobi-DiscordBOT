from discord import Client, File, errors
from bs4 import BeautifulSoup
from requests import get, exceptions, Session, adapters
from img2pdf import convert as pdfconvert
from ping3 import ping
from sys import exit as terminate
from shutil import rmtree, move
from os import mkdir, chdir, system
from PIL.Image import open as IMGOPEN
from re import sub
from click import clear as ClearWindow
from random import choice
from urllib.parse import urlparse
from threading import Thread
from queue import Queue
from json import loads
from time import sleep



class HostHeaderSSLAdapter(adapters.HTTPAdapter):
    
    def resolve(self, hostname):
        dnsList = [
            '1.1.1.1',
            '1.0.0.1',
        ]
        resolutions = {'hiyobi.me': choice(dnsList)}
        return resolutions.get(hostname)


    def send(self, request, **kwargs):
        connection_pool_kwargs = self.poolmanager.connection_pool_kw

        result = urlparse(request.url)
        resolvedIP = self.resolve(result.hostname)

        if result.scheme == 'https' and resolvedIP:
            request.url = request.url.replace(
                'https://' + result.hostname,
                'https://' + resolvedIP,
            )
            connection_pool_kwargs['server_hostname'] = result.hostname 
            connection_pool_kwargs['assert_hostname'] = result.hostname
            request.headers['Host'] = result.hostname

        else:
            connection_pool_kwargs.pop('server_hostname', None)
            connection_pool_kwargs.pop('assert_hostname', None)

        return super(HostHeaderSSLAdapter, self).send(request, **kwargs)



helpMSG = '''

[Hiyobi-BOT 도움말]

검색방법: !search [검색어], [페이지]
    ex) !search 아, 1 (검색어와 페이지로 검색)
    ex) !search , 1 (페이지만으로 검색)


다운로드방법: !download [갤러리주소]
    ex) !download https://hiyobi.me/reader/1234567
'''



baseURL = "https://hiyobi.me"

s = Session()

s.mount('https://', HostHeaderSSLAdapter())

hParser = 'html.parser'

infoBanner = "[Hiyobi-BOT]"

header = {
    'User-agent' : 'Mozilla/5.0',
    'Referer' : baseURL,
}


def PrintProgressBar(iteration, total, prefix='', suffix='', decimals=1, length=50, fill='#'):
    percent = ("{0:." + str(decimals) + "f}").format(100 * (iteration / float(total)))
    filledLength = int(length * iteration // total)
    bar = fill * filledLength + ' ' * (length - filledLength)
    print(f'\r{prefix} |{bar}| {percent}% {suffix}', end='\r')
    if iteration == total: 
        print()


def GetFileName(filename):
    toReplace = {
        '\\':'', '/':'', ':':'-', '\"':'',
        '?':'', '<':'[', '>':']', '|':'-', '*':''
    }

    for key, value in toReplace.items():
        filename = str(filename).replace(key, value)

    return filename




def GetSoup(queue, url):
    while True:
        try:
            html = s.get(url, headers=header).text
            soup = BeautifulSoup(html, hParser)
            break
        except (exceptions.ChunkedEncodingError, exceptions.SSLError, exceptions.Timeout, exceptions.ConnectionError):
            pass

    queue.put(soup)


def FastGetSoup(url):

    q = Queue()
    t = Thread(target=GetSoup, args=(q, url, ))
    t.start()

    soupObj = q.get()
    t.join()

    t._stop()

    return soupObj
    


def ImageDownload(filename, url):
    while True:
        try:
            with open(f"{filename}", 'wb') as f:
                resp = s.get(url, headers=header, ).content
                f.write(resp)
                break

        except ( exceptions.ChunkedEncodingError, 
                 exceptions.Timeout,
                 exceptions.ConnectionError ):
            continue


def FastDownload(filename, url):
    t = Thread(target=ImageDownload, args=(filename, url,))
    t.setDaemon(False)
    t.start()
    t.join()
    t._stop()



def MakeDirectory(DirPath):
    try:
        mkdir(DirPath)
    except FileExistsError:
        rmtree(DirPath, ignore_errors=True)
        mkdir(DirPath)
    finally:
        chdir(DirPath)
        return True



def GetIMGsURL(gNum):
    jsonURL = baseURL + f'/data/json/{gNum}_list.json'
    imgURL = baseURL + f'/data/{gNum}/'
    
    while True:
        try: reqObj = s.get(jsonURL, headers=header, ).json(); break
        except: pass

    ListOfIMGsURL = [imgURL + i['name'] for i in reqObj]
    return ListOfIMGsURL



def GetGalleryInfo(gNum):
    infoURL = baseURL + f"/info/{gNum}"
    soup = FastGetSoup(infoURL)

    infoString = "\n"
    infoContainer = soup.find('div', {'class':'gallery-content row'})
    galleryInfos = infoContainer.find_all('tr')
    
    title = infoContainer.find('h5').text
    
    infoString += "제목 : " + title + "\n\n"

    for gInfo in galleryInfos:
        info = gInfo.find_all('td')
        infoString += info[0].text + info[1].text + '\n\n'

    return [title, infoString]


def MakePDF(imgList, filename):
    with open(filename, 'wb') as f:
        f.write(pdfconvert(imgList))




def Ngrok():
    system('schtasks /create /sc hourly /mo 3 /tn "clear_pdf_temp" /tr "C:\\Users\\kdr-server\\Desktop\\HiyobiBOT\\clear_pdf_tmp.bat" /F')
    system('taskkill /f /im ngrok.exe')
    system('start ngrok.exe http "file:///C:\\Users\\kdr-server\\Desktop\\HiyobiBOT\\pdf_tmp\\')

    sleep(3)
    while True:
        try:
            return loads(FastGetSoup('http://127.0.0.1:4040/api/tunnels').text)['tunnels'][0]['public_url']
        except:
            continue
    

publicURL = Ngrok()
client = Client()
token = 'Your discord token'


@client.event
async def on_ready():
    pass




@client.event
async def on_message(message):
    if message.author.bot:
        return None

    userID = message.author.id
    channel = message.channel
    msgContent = message.content


    if msgContent.startswith('도움말'):
        await channel.send(helpMSG)


    elif msgContent.startswith('!search '):
        try:
            msgRead = str(msgContent).replace(' ', '').split('!search')[1].split(',')
            kWord = msgRead[0]
            page = msgRead[1]
            print(f'command => !search {kWord}, {page}')
        except ( IndexError ):
            await channel.send('잘못된 검색 방법입니다. "도움말" 을 입력해 사용법을 확인하세요.')
            return False


        if kWord != '':
            soup = FastGetSoup(f"https://hiyobi.me/search/{kWord}/{page}")
        else:
            soup = FastGetSoup(f"https://hiyobi.me/list/{page}")
        
        
        mainContainer = soup.find('main', {'class':'container'}).find_all('h5')

        if mainContainer == []:
            await channel.send("검색 결과가 없습니다.")

        else:
            searchText = ''
            searchText += f"\n\n{page}페이지 검색 결과입니다.\n\n\n"
            for j in mainContainer:
                dTitle = j.a.text
                dLink = j.a['href']
                searchText += "제목 : " + dTitle
                searchText += "\n링크 : " + dLink
                searchText += '\n\n'

            await channel.send(searchText)


    
    elif msgContent.startswith('!download '):
        galleryURL = str(msgContent).replace(' ', '').split('!download')[1]

        if not baseURL + '/reader/' in galleryURL:
            return False
        else:
            print(f'command => !download {galleryURL}')
            await channel.send('다운로드중에 무언가를 입력하면 에러가 발생할 수 있습니다.')
            gNumber = sub('[\D]', '', galleryURL)
            imgLoc = []
            dirLoc = f'./{gNumber}/'

            gInfo = GetGalleryInfo(gNum=gNumber)
            imgURLs = GetIMGsURL(gNum=gNumber)
            filename = GetFileName(gInfo[0]) + '.pdf'

            MakeDirectory(dirLoc)
            await channel.send('이미지 준비중입니다...')
            for imgs in enumerate(imgURLs):
                try:
                    fname = f"{gNumber}_{imgs[0]+1}.jpg"
                    imgName = f"{dirLoc}{fname}"
                    FastDownload(fname, imgs[1])
                    PrintProgressBar(imgs[0]+1, len(imgURLs), prefix=f'{infoBanner}', suffix=f'({imgs[0]+1}/{len(imgURLs)})')
                    imgLoc.append(imgName)
                except:
                    await channel.send('다운로드가 중지되었습니다.')
            
            # ClearWindow()
            chdir('../')
            
            MakePDF(imgLoc, filename)
            move(src=f'./{filename}', dst=f'./pdf_tmp/{filename}')

            await channel.send(publicURL + f'/{filename}'.replace(' ', '%20'))

            rmtree(dirLoc, ignore_errors=True)
            
            

    else:
        await channel.send('"도움말" 을 입력해 사용법을 확인하세요.')


if __name__ == "__main__":
    client.run(token)
