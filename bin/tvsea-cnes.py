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
import requests
import ntpath
from urllib.parse import urlparse
from os.path import basename
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil.relativedelta import relativedelta

#logging.basicConfig(level=logging.DEBUG)
#LOGGER = logging.getLogger(os.path.basename(__file__))
#LOGGER = None

##TODO: 미디어 라이브러리 폴더가 없는 경우. 경고 로깅 후 경로를 생성 하도록 처리.
##TODO: 미디어 라이브러리에 영상이 없고, queue도 없을 때(leid number가 None)이 반환되지 않도록? 아니면 None에 대해 방어 코딩 등등..
##TODO: 로깅을 파일에 하도록 처리

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
    def queue_path_name():
        return "queue"
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
    @constant
    def midfeedlib_name():
        return "mid.json"

CONST = _Const()

def checkrspath():
    global rspath
    rspath = os.path.join(os.path.expanduser("~"), "." + CONST.resource_name)
    print("Resource name: {}".format(CONST.resource_name))
    print("Resource path: {}".format(rspath))
    
    # check for exist resource path.
    if not os.path.exists(rspath):
        os.makedirs(rspath)
        print("[{}] is not exist.".format(rspath))
        sys.exit()
    elif not os.path.isdir(rspath):
        print("ERROR! {} is not directory!".format(rspath))
        sys.exit()
    elif os.path.isdir(rspath):
        print("[{}] path is exist OK.".format(rspath))

def startLogging():
    rspath = os.path.join(os.path.expanduser("~"), "." + CONST.resource_name)
    logfile = os.path.join(rspath, "log", os.path.basename(__file__) + ".log")
    logging.basicConfig(filename=logfile,level=logging.DEBUG)
    #logging.basicConfig(level=logging.WARNING)
    #logging.basicConfig(level=logging.DEBUG)
    #LOGGER = logging.getLogger(os.path.basename(__file__))
    global LOGGER
    LOGGER = logging
    print("Complete initialize logging. logfile: {}".format(logfile))


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
    pageCountForFeed = 3
    for pagenum in range(1, pageCountForFeed + 1):

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
            if pagenum == pageCountForFeed: break
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
                
            difftime = (current - mtime) / 60
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
    bo_table_mid= "torrent_mid"
    
    saveJsonArticle(getKtvList(bo_table_drama)        , CONST.dramafeedlib_name)
    saveJsonArticle(getKtvList(bo_table_kids)         , CONST.kidsfeedlib_name)
    saveJsonArticle(getKtvList(bo_table_entertainment), CONST.entertainmentfeedlib_name)
    saveJsonArticle(getKtvList(bo_table_documentary)  , CONST.documentaryfeedlib_name)
    saveJsonArticle(getKtvList(bo_table_mid)          , CONST.midfeedlib_name)

def getLastEpsoideNumberAtPlex(season_root, seriesname, seasonnumber):
    # 마지막 번호를 구해서 반환. 파일조차 없다면. None을 반환.
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
    # 마지막 날짜를 구해서 반환. 파일조차 없다면. 적당한 과거의 날짜를 반환.
    videoList = glob.glob(os.path.join(season_root, seriesname + "*"))
    LOGGER.debug("{}'s video file count: {}".format(seriesname, str(len(videoList))))

    if len(videoList) == 0:
        ## 좀 과거의 값을 반환 하도록 한다.
        ayearago = datetime.now() - relativedelta(years=1)
        return ayearago.strftime("%Y-%m-%d")

    epdatelist = []
    for aep in videoList:
        aep1 = ntpath.basename(aep).split('.')[0]
        aep2 = aep1.replace(seriesname, "", 1).replace(" - ", "", 1).strip()
        LOGGER.debug("    - name: [{}]".format(aep2))
        epdatelist.append(aep2)

    return max(epdatelist) 
    
def getLastEpsoideId(season_root, series_key, epsode_id_type, seriesname, seasonnumber):
    # queue에 다운로드 이력을 먼저 확인 하도록 한다.
    queueFileName = seriesname + ".s" + seasonnumber + ".queue.json"
    queueFile = os.path.join(rspath, CONST.queue_path_name, queueFileName)
    if os.path.isfile(queueFile):
        # 파일이 있다면, 읽어서 마지막 에피소드 정보를 반환 한다.
        LOGGER.debug("Found season queue file: {}.".format(queueFile))
        qf = open(queueFile, 'r')
        queue = json.loads(qf.read())
        qf.close()
        LOGGER.debug("The last epid of queue file is {} ({})".format(queue["last_epid"], queueFileName))
        return queue["last_epid"]
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

    #LOGGER.debug("s4: {}".format(s4))
    return s4

def checkNewEpByDate(leid, title):
    if not leid:
        leid = "2016-01-01"
    
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
                        #LOGGER.debug("return new episode date: [{}]".format(dstr))
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
                    LOGGER.debug("return new episode number: e[{}]".format(val))
                    return val
            except TypeError as e:
                LOGGER.warn("TypeError word[{}, {}]: {}".format(w, epnum, e))
                continue
            except ValueError as e:
                LOGGER.warn("ValueError word[{}, {}]: {}".format(w, epnum, e))
                continue

            LOGGER.debug("E start word: {}".format(w))
    return None

def getTopPriorityEp(el, k):
    LOGGER.debug("Lenght: {}. epid: {}".format(len(el), k))
    
    ## 개수가 하나라면, 그 하나를 다운로드 받도록. 아니라면, 가장 적절한 것(?)을 찾도록.
    
    pl = el[0]["ed"]["feed"]["priority"]
    
    if len(el) == 0:
        return None
    
    ## 하나 일때 다운로드 받게 하려면, 아래 코드로 처리 가능하지만, 릴그룹/인코딩여부를 반환하기 애매 하므로 일단 보류 한다.
    '''if len(el) == 1:
        LOGGER.info("(getTopPriorityEp)Just one content: {}".format(el[0]["title"]))
        return el[0]'''
    
    for p in pl:
        #LOGGER.debug("priority: {}".format(p))
        LOGGER.debug("resolution: {}, release_group: {}, force_audio_encoding:{}, force_video_encoding{}".format(p["resolution"], p["release_group"], p["force_audio_encoding"], p["force_video_encoding"]))
    
        for e in el:
            #LOGGER.debug("title: {}".format(e["title"]))
            if e["title"].upper().find(p["resolution"].upper()) > -1:
                if e["title"].upper().find(p["release_group"].upper()) > -1:
                    e["resolution"] = p["resolution"]
                    e["release_group"] = p["release_group"]
                    e["force_audio_encoding"] = p["force_audio_encoding"]
                    e["force_video_encoding"] = p["force_video_encoding"]
                    LOGGER.info("(getTopPriorityEp)Matched top priority: {}".format(e["title"]))
                    return e
    
    LOGGER.info("(getTopPriorityEp)No match found: {}".format(el))
    return None
    
def attachDownload(httpsHost, urlPath, my_referer, localPath, name):
    ##referer 설정을 위해 httplib.HTTPConnection를 사용 해야 한다.
    LOGGER.debug("httpsHost: {}, urlPath: {}, name: {}, my_referer: {}, localPath: {}".format(httpsHost, urlPath, name, my_referer, localPath))
    
    s = requests.Session()
    s.headers.update({'referer': my_referer})
    r = s.get("https://" + httpsHost + "/" + urlPath)
    LOGGER.debug("Download status: {}".format(r.status_code))
    if r.status_code == 200:
        data = r.content
        
        f = open(os.path.join(localPath, name), 'wb')
        f.write(bytearray(data))
        f.close()
    
def updateQueue(tpe, title_keywords):
    #LOGGER.debug("tpe for Update queue: {}".format(tpe))
    seriesName = tpe["ed"]["series_name"]
    seriesKey = tpe["ed"]["series_key"]
    seasonNumber = tpe["ed"]["season_number"]
    releaseYear = tpe["ed"]["release_year"]
    plexlibRoot = tpe["ed"]["plexlib_season_root"]
    storeCount = tpe["ed"]["store_count"]
    epidType = tpe["ed"]["feed"]["epsode_id_type"]
    queueFileName = seriesName + ".s" + seasonNumber + ".queue.json"
    queueFile = os.path.join(rspath, CONST.queue_path_name, queueFileName)
    queue = {}
    
    ## 일단 현재 epsodie 정보를 생성 한다.
    cep = {}
    cep["epid"] = tpe["epid"]
    cep["url"] = tpe["url"]
    cep["title"] = tpe["title"]
    cep["resolution"] = tpe["resolution"]
    cep["release_group"] = tpe["release_group"]
    cep["force_audio_encoding"] = tpe["force_audio_encoding"]
    cep["force_video_encoding"] = tpe["force_video_encoding"]
    cep["download_complete"] = False

    ## 파일이 있다면 읽기. 없다면, 생성.
    if os.path.isfile(queueFile):
        qf = open(queueFile, 'r')
        queue = json.loads(qf.read())
        qf.close()
        
        # 일단 추가된 에피소드 정보를 추가.
        # 이미 존재 하는 경우에도 덮어쓰기가 안되므로, 확인한 후 없는 경우에만 쓰거나, 있는 경우 제거 하고 쓰도록 한다.
        ep_dic = queue["ep_dic"]
        if str(tpe["epid"]) in ep_dic:
            LOGGER.warn("epid {} at {} is already is exist.".format(str(tpe["epid"]), seriesName))
            del ep_dic[str(tpe["epid"])]
            
        ep_dic[tpe["epid"]] = cep
        
        # last_epid를 비교하여 갱신하고, cep를 추가 하도록 한다.
        if epidType == "date":
            # 날짜 비교.
            df = "%Y-%m-%d"
            qdto = datetime.strptime(queue["last_epid"], df)
            cdto = datetime.strptime(cep["epid"], df)
            if qdto < cdto:
                queue["last_epid"] = cdto.strftime(df)
                
        elif epidType == "number":
            # 숫자 비교.
            if queue["last_epid"] < cep["epid"]:
                queue["last_epid"] = cep["epid"]
            
        else:
            # 요건 에러임.
            LOGGER.error("Unknown epsodie id tpye: {}".format(epidType))
        
    else:
        queue["series_name"] = seriesName
        queue["series_key"] = seriesKey
        queue["season_number"] = seasonNumber
        queue["last_epid"] = tpe["epid"]
        queue["release_year"] = releaseYear
        queue["plexlib_season_root"] = plexlibRoot
        queue["store_count"] = storeCount
        queue["title_keywords"] = title_keywords
        queue["epsode_id_type"] = epidType
        ep_dic = {}
        queue["ep_dic"] = ep_dic
        ep_dic[tpe["epid"]] = cep
        
    queueStr = json.dumps(queue, indent=4, sort_keys=False, ensure_ascii=False)
    #LOGGER.debug("Update queue: {}".format(queueStr))
    qf = open(queueFile, 'w')
    qf.write(queueStr)
    qf.close()
    
def downloadToIncomming(tpe, title_keywords):
    #LOGGER.debug("(downloadToIncomming)tep:{}".format(tpe))
    pr = urlparse(tpe["url"])
    LOGGER.info("epsode detail page: {}".format(tpe["url"]))
    #LOGGER.debug("parser result:{}".format(pr))
    
    conn = http.client.HTTPSConnection(pr.netloc)
    conn.request("GET", pr.path + "?" + pr.query)
    r1 = conn.getresponse()
    LOGGER.debug("Status: {}, Reason: {}".format(r1.status, r1.reason))
    if r1.status == 200:
        data2 = r1.read()
        #LOGGER.debug("content html: {}".format(data2))
        soup = BeautifulSoup(data2, "lxml")
        soup_mview = soup.find(id="m_view")
        soup_mview_as = soup_mview.findAll("a")
        
        for a in soup_mview_as:
            cu = str(a["href"])
            if cu.find("javascript") > -1:
                if cu.find("file_download") > -1:
                    cu = cu.replace("javascript:file_download(", "")
                    cu = cu.replace(");", "")
                    cu = cu.replace("'", "")
                    cul = cu.split(",")
                    cp = cul[0].strip()
                    cn = cul[1].strip()
                    LOGGER.info("download path: {}".format(cp))
                    LOGGER.info("download file name: {}".format(cn))
                    
                    ## 확장자 명에 따라 파일을 업로드 한다.
                    ## 혹시 자막파일이면 나중에 찾아서 쓸 수 있도록 다운로드 경로에 미리 저장해 두자.
                    watchDirPath = "/storage/local/mforce2-local/transmission-daemon/watch-dir"
                    downloadDirPath = "/storage/local/mforce2-local/transmission-daemon/downloads"
                    if cn.endswith('.torrent'):
                        targetPath = watchDirPath
                    else:
                        targetPath = downloadDirPath
                    
                    # 실제 다운로드 시작
                    attachDownload(pr.netloc, cp, tpe["url"], targetPath, cn)
                    ransleep = random.random()*10
                    LOGGER.debug("sleep: {}".format(ransleep))
                    time.sleep(ransleep)
                    
        ## queue 정보를 갱신 한다. 시리즈 이름. 다운로드 추가 된 에피소드 정보.
        updateQueue(tpe, title_keywords)
    
    conn.close()

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

    ## 우선순위가 높은 것 하나만 선택하는 작업을 위해 같은 에피소드끼리 묶는다.
    match3feedDic = {}
    for f2f in match2feeds:
        epid = f2f["epid"]
        if not epid in match3feedDic:
            neplist = []
            neplist.append(f2f)
            match3feedDic[epid] = neplist
            LOGGER.debug("match3feedDic - new: [{}] {}".format(epid, len(match3feedDic[epid])))
        else:
            neplist = match3feedDic.get(epid)
            neplist.append(f2f)
            LOGGER.debug("match3feedDic - add: [{}] {}".format(epid, len(match3feedDic[epid])))
    
    #LOGGER.debug("{}".format(json.dumps(match3feedDic, indent=4, sort_keys=False, ensure_ascii=False)))
    
    ## 각 에페소드별로 하나의 게시물만 골라내는 함수를 호출한다.
    for k in match3feedDic.keys():
        te = getTopPriorityEp(match3feedDic.get(k), k)
        #LOGGER.debug("Top priority epsode: {}".format(json.dumps(te, indent=4, sort_keys=False, ensure_ascii=False)))
        if te:
            downloadToIncomming(te, title_keywords)
        
    LOGGER.debug("===============================================================================")
    
    
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
    ## 받아야 할 모든 항목을 feed-json에서 확인
    ##  - keyword로 찾은 다음. epsoide 번호 기준 새로운 항목을 확인.
    ## 새로운 항목은 torrent 파일을 다운로드 받아 추가.
    ## 다운로드 정보 파일에 정보를 추가.
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
    startLogging()
    updatefeed()
    findNewEpsoides()

if __name__ == "__main__":
    main()




