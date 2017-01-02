#!/usr/bin/env python3


import os
import sys
import logging
import time
import random
import json
import time
import glob
import codecs
import yaml
import copy
import http.client
import ntpath
from os.path import basename
from bs4 import BeautifulSoup
from datetime import datetime

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
    def seriesdef_path_name():
        return "seriesdef"
    @constant
    def dramafeedlib_name():
        return "drama.json"
    @constant
    def kidsfeedlib_name():
        return "kids.json"
    @constant
    def entertainmentfeedlib_name():
        return "entertainment.json"
    @constant
    def documentaryfeedlib_name():
        return "documentary.json"

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
def getKtvList(bo_table_value):
    torrcontentlist = []
    conn = http.client.HTTPSConnection("m.torrentkim5.net")
    #TODO: range는 설정하고, 계산하여 처리 하도록 해야함.
    for pagenum in range(1, 4):

        if pagenum == 1:
            ransleep = random.random()*100
            LOGGER.debug("sleep: {}".format(ransleep))
            time.sleep(ransleep)

        urlpath = "/bc.php?bo_table="+bo_table_value+"&page=" + str(pagenum)
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
    feedlib_path = os.path.join(rspath, CONST.feedlib_path_name, type)
    f = open(feedlib_path, 'w')
    f.write(formatedJsonStr)
    f.close()

def checkRecentUpdate():
    current = time.time()
    LOGGER.debug("Current time: {}".format(current))
    last_modified_date = 0
    mtime = 0
    for file in os.listdir(os.path.join(rspath, CONST.feedlib_path_name)):
        if file.endswith(".json"):
            libfile = os.path.join(rspath, CONST.feedlib_path_name, file)
            try:
                mtime = os.path.getmtime(libfile)
            except OSError:
                mtime = 0
                
            difftime = (current - mtime) / 180
            LOGGER.debug("Current feed update time: {}. Diff(min): {}.".format(mtime, difftime))
            
            if difftime < 180:
                LOGGER.info("Already updated just before {0:.2f}(min). Skip update feedlib. ".format(difftime))
                return False
    return True
    
def updatefeed():
    if not checkRecentUpdate():
        return
    
    bo_table_drama = "torrent_tv"
    bo_table_kids = "torrent_child"
    bo_table_entertainment = "torrent_variety"
    bo_table_documentary= "torrent_docu"
    
    saveJsonArticle(getKtvList(bo_table_drama)        , CONST.dramafeedlib_name)
    saveJsonArticle(getKtvList(bo_table_kids)         , CONST.kidsfeedlib_name)
    saveJsonArticle(getKtvList(bo_table_entertainment), CONST.entertainmentfeedlib_name)
    saveJsonArticle(getKtvList(bo_table_documentary)  , CONST.documentaryfeedlib_name)

def getLastEpsoideNumberAtPlex(season_root, seriesname, seasonnumber):
    ##TODO: 마지막 번호를 구해서 반환. 파일조차 없다면. None을 반환.
    videoList = glob.glob(os.path.join(season_root, seriesname + "*"))
    LOGGER.debug("{}'s video file count: {}".format(seriesname, str(len(videoList))))

    if len(videoList) == 0:
        return None

    epnumlist = []
    for aep in videoList:
        aep1 = ntpath.basename(aep).split('.')[0]
        aep2 = aep1.replace(seriesname, "", 1)
        aep3 = aep2.split('-')[1].strip()
        aep4 = aep3.replace("s" + str(seasonnumber) + "e", "", 1)
        #LOGGER.debug("    - name: [{}]".format(aep4))
        epnumlist.append(aep4)

    return max(epnumlist) 
    
def getLastEpsoideDateAtPlex(season_root, seriesname):
    ##TODO: 마지막 날짜를 구해서 반환. 파일조차 없다면. None을 반환.
    videoList = glob.glob(os.path.join(season_root, seriesname + "*"))
    LOGGER.debug("{}'s video file count: {}".format(seriesname, str(len(videoList))))

    if len(videoList) == 0:
        return None

    epdatelist = []
    for aep in videoList:
        aep1 = ntpath.basename(aep).split('.')[0]
        aep2 = aep1.replace(seriesname, "", 1).replace(" - ", "", 1).strip()
        LOGGER.debug("    - name: [{}]".format(aep2))
        epdatelist.append(aep2)

    return max(epdatelist) 
    
def getLastEpsoideId(season_root, series_key, epsode_id_type, seriesname, seasonnumber):
    # 에피소드 다운로드 정보 json 파일이 있는지 확인 한다.
    epdfile = os.path.join(rspath, CONST.seriesdef_path_name, str(series_key) + "_epd.json")
    if os.path.isfile(epdfile):
        # 파일이 있다면, 읽어서 마지막 에피소드 정보를 반환 한다.
        LOGGER.debug("Found epdfile: {}.".format(epdfile))
    else:
        # 파일이 없다면, season root path를 읽어서 마지막 값을 반환 한다.
        LOGGER.debug("Search: {}".format(season_root))
        if epsode_id_type == "date":
            return getLastEpsoideDateAtPlex(season_root, seriesname)
        elif epsode_id_type == "number":
            return getLastEpsoideNumberAtPlex(season_root, seriesname, seasonnumber)
        else:
            return None

def titleSplit(title):
    s1 = title.upper().split()

    s2 = list()
    for w in s1:
        s2.extend(w.split("."))

    s3 = list()
    for w in s2:
        s3.extend(w.split("-"))

    s4 = list()
    for w in s3:
        s4.extend(w.split("_"))

    LOGGER.debug("s4: {}".format(s4))
    return s4

def checkNewEpByDate(leid, title):
    leiddt = datetime.strptime(leid, "%Y-%m-%d")
    dateformats = ["%y%m%d", "%y.%m.%d", "%y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y-%m-%d"]
    now = datetime.now()
    s4 = titleSplit(title)
    for w in s4:
        for df in dateformats:
            val = None
            try:
                ## 여려 format의 날짜 변환을 시도해 본다. 변환된 날짜가 과거 1개월 이내 이어야 한다.
                dto = datetime.strptime(w, df)
                LOGGER.debug("w to datetime_object: {} -> {} / {}".format(w, dto, df))
                delta = now - dto
                LOGGER.debug("diff date: {} days".format(delta.days))
                if delta.days < 32 and delta.days > -1:
                    if dto > leiddt:
                        dstr = dto.strftime("%Y-%m-%d")
                        LOGGER.debug("return new episode date: [{}]".format(dstr))
                        return dstr
            except ValueError as e:
                #LOGGER.warn("{}".format(e))
                continue 

    return None

def checkNewEpByNumber(leid, title):
    s4 = titleSplit(title)
    for w in s4:
        if w.startswith("E"):
            epnum = w.split("E")[-1]
            try:
                val = int(epnum)
                if int(leid) < val:
                    LOGGER.info("return new episode number: e[{}]".format(val))
                    return val
            except TypeError as e:
                LOGGER.warn("TypeError word[{}, {}]: {}".format(w, epnum, e))
                continue
            except ValueError as e:
                LOGGER.warn("ValueError word[{}, {}]: {}".format(w, epnum, e))
                continue

            LOGGER.debug("E start word: {}".format(w))
    return None

def discoveryAndDownload(ed, leid, feedlibs):
    feed = ed["feed"]
    title_keywords = feed["necessary_title_keywords"]
    epsode_id_type = feed["epsode_id_type"]

    match1feeds = list()
    for nfs in feedlibs:
        matched = True
        for tk in title_keywords:
            if nfs["title"].upper().find(tk.upper()) < 0:
                matched = False
        if matched:
            match1feeds.append(nfs)

    LOGGER.debug("match1feeds size: {}".format(len(match1feeds)))

    match2feeds = list()
    ## 검색된 것이 새로운 에피소드인지 확인 한다.
    for ffs in match1feeds:
        LOGGER.debug("matched: {}".format(ffs["title"]))
        if epsode_id_type == "date":
            epid = checkNewEpByDate(leid, ffs["title"])
            if not epid == None:
                ffs["epid"] = epid
                ffs["ed"] = ed
                match2feeds.append(ffs)
        elif epsode_id_type == "number":
            epid = checkNewEpByNumber(leid, ffs["title"])
            if not epid == None:
                ffs["epid"] = epid
                ffs["ed"] = ed
                match2feeds.append(ffs)

    LOGGER.debug("match2feeds size: {}".format(len(match2feeds)))

    ##TODO: 같은 에피소드끼리 묶어서 우선순위가 높은 것 하나만 선택하는 작업을 한다.
    LOGGER.debug("==========")
    
    
def discoveryEpsoidesFromAllFeed(dy, feedlibs):
    ed = yaml.load(codecs.open(dy, "r", "utf-8"))
    LOGGER.debug("Current series is \"{} ({})\".".format(ed["series_name"], ed["release_year"]))
    
    plexlib_path = ed["plexlib_season_root"]
    feedinfo = ed["feed"]
    serieskey = ed["series_key"]
    seriesname = ed["series_name"]
    seasonnumber = ed["season_number"]
    eptype = feedinfo["epsode_id_type"]
    leid = getLastEpsoideId(plexlib_path, serieskey, eptype, seriesname, seasonnumber)
    LOGGER.info("Last epsoid id: {}".format(leid))
    #keys = ed.feed.necessary_title_keywords
    ##TODO: 받아야 할 모든 항목을 feed-json에서 확인
    ##TODO:  - keyword로 찾은 다음. epsoide 번호 기준 새로운 항목을 확인.
    ##TODO: 새로운 항목은 torrent 파일을 다운로드 받아 추가.
    ##TODO: 다운로드 정보 파일에 정보를 추가.
    discoveryAndDownload(ed, leid, feedlibs)
    
    
def findNewEpsoides():
    ## feedlib/*.json 파일들을 읽어 들인다.
    feedlibs = []
    for feedfile in glob.glob(os.path.join(rspath, CONST.feedlib_path_name) + '/*.json'):
        ff = open(feedfile, 'r')
        feedlibs = feedlibs + json.loads(ff.read())
        ff.close()
    
    LOGGER.debug("feedlibs length: {}".format(len(feedlibs)))
    
    ## seriesdef/*.def.yaml 파일들을 읽어 들인다.
    for name in glob.glob(os.path.join(rspath, CONST.seriesdef_path_name) + '/*.def.yaml'):
        LOGGER.debug("Feed list file: {}".format(name))
        discoveryEpsoidesFromAllFeed(name, feedlibs)
    
def main():
    checkrspath()
    checkqueuefile()
    updatefeed()
    findNewEpsoides()

if __name__ == "__main__":
    main()


"""
## torrent 파일을 다운로드 받으려 하는 경우는 다음과 같이 referer를 지정 해줘야 한다. 꼭 상세 페이지를 줘야 하는지는 모르겠지만, 그게 가장 좋아 보인다.
## curl --referer "https://m.torrentkim5.net/./bc.php?bo_table=torrent_tv&wr_id=119764&page=2" "https://m.torrentkim5.net/./bbs/download.php?bo_table=torrent_tv&wr_id=119764&no=0&page=1"
## cookie는 필요 없는 것으로 확인 되었지만, 만약 해야 한다면, 다음과 같이 상세 페이지에서 cookie를 받아 저장하고 이를 사용하도록 해야 할 수도 있다.
## curl --cookie-jar cjar3.cookie --output /dev/null "https://m.torrentkim5.net/./bc.php?bo_table=torrent_tv&wr_id=119764&page=2"
## curl --cookie cjar3.cookie --referer "https://m.torrentkim5.net/./bc.php?bo_table=torrent_tv&wr_id=119764&page=2" "https://m.torrentkim5.net/./bbs/download.php?bo_table=torrent_tv&wr_id=119764&no=0&page=1"
"""


