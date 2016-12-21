#!/usr/bin/env python3


import os
import sys
import logging
import time
import random
import json
import http.client
from bs4 import BeautifulSoup

#print(os.path.isdir("/home/el"))
#print(os.path.exists("/home/el/myfile.txt"))

#logging.basicConfig(filename='example.log',level=logging.DEBUG)
#logging.basicConfig(level=logging.WARNING)
logging.basicConfig(level=logging.DEBUG)
LOGGER = logging.getLogger(os.path.basename(__file__))


def constant(f):
    def fset(self, value):
        raise TypeError
    def fget(self):
        return f()
    return property(fget, fset)


class _Const(object):
    @constant
    def resource_name():
        return "tvsea"
    @constant
    def feedlib_path_name():
        return "feedlib"
    @constant
    def dramafeedlib_name():
        return "drama.json"

CONST = _Const()

def checkrspath():
    global rspath
    rspath = os.path.join(os.path.expanduser("~"), "." + CONST.resource_name)
    LOGGER.info("Resource name: {}".format(CONST.resource_name))
    LOGGER.info("Resource path: {}".format(rspath))
    
    # check for exist resource path.
    if not os.path.exists(rspath):
        os.makedirs(rspath)
        LOGGER.warning("[{}] is not exist.".format(rspath))
        sys.exit()
    elif not os.path.isdir(rspath):
        LOGGER.warning("ERROR! {} is not directory!".format(rspath))
        sys.exit()
    elif os.path.isdir(rspath):
        LOGGER.debug("[{}] path is exist OK.".format(rspath))

    
def checkqueuefile():
    LOGGER.info("xxxxxxx");

##
 # html을 실제 파싱하고 object로 변환 한다.
 ##
def listhtml2obj(htmlstring):
    #htmllinearr = htmlstring.splitlines(True)
    #linelen = len(htmllinearr)
    #LOGGER.debug("html line length: {}".format(linelen))
    #for line in htmllinearr:
    soup = BeautifulSoup(htmlstring, "lxml")
    soup_listsubjects = soup('a', {'class':'list_subject',})
    LOGGER.debug("list_subject element: {}".format(str(soup_listsubjects)))
    listidx = 0
    torrcontentlist = []
    for ahref in soup_listsubjects:
        listidx = listidx + 1 
        hrefval = ahref['href']
        # skip: rel="nofollow"
        #LOGGER.debug("tag.attrs: {}".format(ahref.attrs))
        if 'rel' in ahref.attrs:
            relval = ahref['rel']
            #LOGGER.debug("relval: {}".format(relval))
            if relval[0] == "nofollow": continue
        LOGGER.debug("content url path[{:0>2d}]: {}: {}".format(listidx, hrefval, ahref.string))
        torrcontent = {}
        torrcontent['title'] = ahref.string
        torrcontent['url'] = "https://m.torrentkim5.net/" + hrefval
        torrcontentlist.append(torrcontent)
    return torrcontentlist
        

##
 # 목록 html들을 받아오고 parsing 한 후 object로 반환 하게 한다.
 # TODO: host, path, list-pagenum 을 환경 설정으로 처리 한다.
 ##
def getKtvDramaList():
    torrcontentlist = []
    conn = http.client.HTTPSConnection("m.torrentkim5.net")
    #TODO: range는 설정하고, 계산하여 처리 하도록 해야함.
    for pagenum in range(1, 2):

        '''if pagenum == 1:
            ransleep = random.random()*100
            LOGGER.debug("sleep: {}".format(ransleep))
            time.sleep(ransleep)'''

        urlpath = "/bc.php?bo_table=torrent_tv&page=" + str(pagenum)
        LOGGER.debug("content list path: {}".format(urlpath))
        conn.request("GET", urlpath)
        r1 = conn.getresponse()
        LOGGER.debug("Status: {}, Reason: {}".format(r1.status, r1.reason))
        if r1.status == 200:
            data1 = r1.read()
            torrcontentlist = torrcontentlist +listhtml2obj(data1)
            # 바깥 for loop 를 설정에 의해 제어하도록 하면서, 이곳의 값도 그 값을 가지고 처리 하도록 변경 해야 한다.
            if pagenum == 3: break
            ransleep = random.random()*10
            LOGGER.debug("sleep: {}".format(ransleep))
            time.sleep(ransleep)

    conn.close()
    return torrcontentlist

def saveJsonArticle(listobj, type):
    formatedJsonStr = json.dumps(listobj, indent=4, sort_keys=False, ensure_ascii=False)
    LOGGER.debug("Formatted json: {}".format(formatedJsonStr))
    feedlib_path = os.path.join(rspath, CONST.feedlib_path_name, CONST.dramafeedlib_name)
    f = open(feedlib_path, 'w')
    f.write(formatedJsonStr)
    f.close()

def main():
    checkrspath()
    checkqueuefile()
    recentDramaList = getKtvDramaList()
    LOGGER.debug("Three page's list: {}".format(str(recentDramaList)))
    saveJsonArticle(recentDramaList, "drama")

if __name__ == "__main__":
    main()


"""
## torrent 파일을 다운로드 받으려 하는 경우는 다음과 같이 referer를 지정 해줘야 한다. 꼭 상세 페이지를 줘야 하는지는 모르겠지만, 그게 가장 좋아 보인다.
## curl --referer "https://m.torrentkim5.net/./bc.php?bo_table=torrent_tv&wr_id=119764&page=2" "https://m.torrentkim5.net/./bbs/download.php?bo_table=torrent_tv&wr_id=119764&no=0&page=1"
## cookie는 필요 없는 것으로 확인 되었지만, 만약 해야 한다면, 다음과 같이 상세 페이지에서 cookie를 받아 저장하고 이를 사용하도록 해야 할 수도 있다.
## curl --cookie-jar cjar3.cookie --output /dev/null "https://m.torrentkim5.net/./bc.php?bo_table=torrent_tv&wr_id=119764&page=2"
## curl --cookie cjar3.cookie --referer "https://m.torrentkim5.net/./bc.php?bo_table=torrent_tv&wr_id=119764&page=2" "https://m.torrentkim5.net/./bbs/download.php?bo_table=torrent_tv&wr_id=119764&no=0&page=1"
"""


