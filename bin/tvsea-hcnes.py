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
import re
import yaml
import copy
import http.client
import requests
import ntpath
import subprocess
from urllib.parse import urlparse
from os.path import basename
from bs4 import BeautifulSoup
from datetime import datetime
from dateutil.relativedelta import relativedelta


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
    #logging.basicConfig(filename=logfile,level=logging.DEBUG)
    #logging.basicConfig(level=logging.WARNING)
    #logging.basicConfig(level=logging.DEBUG)
    #LOGGER = logging.getLogger(os.path.basename(__file__))
    global logger
    logger = logging.getLogger(os.path.basename(__file__))
    fomatter = logging.Formatter('[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')
    fileHandler = logging.FileHandler(logfile)
    fileHandler.setFormatter(fomatter)
    # consoleHandler = logging.StreamHandler()
    # consoleHandler.setFormatter(fomatter)

    logger.addHandler(fileHandler)
    # logger.addHandler(consoleHandler)
    logger.setLevel(logging.DEBUG)
    print("Complete initialize logging. logfile: {}".format(logfile))


def loadConfig():
    configYaml = os.path.join(rspath) + '/config.yaml'
    config = yaml.load(codecs.open(configYaml, "r", "utf-8"))
    print("Complete loading config from yaml file. configfile: {}".format(configYaml))

    global ctru
    global ctrp
    ctru = config["transmission_remote_username"]
    ctrp = config["transmission_remove_password"]


def hajalisthtml2obj(htmlstring):
    soup = BeautifulSoup(htmlstring, "lxml")
    soup_board_list = soup('table', {'class':'table table-hover'})
    #logger.debug("html1: {}".format(soup_board_list[0].prettify(formatter="html")))
    soup_trlist = soup_board_list[0].find_all('tr')
    #logger.debug("html2: {}".format(soup_trlist[1].prettify(formatter="html")))

    # 반환할 object array.
    torrcontentlist = []
    # 파싱할때 element 속의 elements 골라 지울 수 있도록.
    __text_strip_str="{[**haja**]}"

    listidx = 0
    for soup_tr in soup_trlist:
        listidx = listidx + 1
        #logger.debug("tr html: {}".format(soup_tr.prettify(formatter="html")))
        soup_tdlist = soup_tr.find_all('td', recursive=False)
        ##soup_tr.find_all("td", attrs={"class": "td_num"}, recursive=False)
        #logger.debug("td html: {}".format(soup_tdlist))
        #logger.debug("soup_tdlist length: {}".format(len(soup_tdlist)))

        if len(soup_tdlist) != 4:
            # 중간줄(선) skip
            continue

        soup_td1 = soup_tdlist[0]
        soup_td2 = soup_tdlist[1]
        soup_td3 = soup_tdlist[2]
        soup_td4 = soup_tdlist[3]
        #logger.debug("soup_td1: {}".format(soup_td1))
        #logger.debug("soup_td2: {}".format(soup_td2))
        #logger.debug("soup_td3: {}".format(soup_td3))
        #logger.debug("soup_td4: {}".format(soup_td4))

        ahref = soup_td2.div.find_all('a', recursive=False)[0]
        title = ahref.get_text(__text_strip_str, strip=True).split(__text_strip_str)[0]
        
        #logger.debug("num  : {}".format(soup_td1.string.strip()))
        #logger.debug("title: {}".format(title))
        #logger.debug("url  : {}".format(soup_td2.div.a['href']))
        
        # object 생성.
        torrcontent = {}
        torrcontent['num']       = soup_td1.string.strip()
        torrcontent['title']     = title
        torrcontent['url']       = soup_td2.div.a['href']
        torrcontent['date']      = soup_td3.string.strip()
        torrcontent['size']      = soup_td4.string.strip()
        torrcontent['publisher'] = "haja"
        #logger.debug("torrcontent: {}".format(torrcontent))
        torrcontentlist.append(torrcontent)

    return torrcontentlist

def getHajaKtvList(tvGenreName):
    # wiz에서는 browser agnet 헤더를 확인 하므로... 차후에는 환경 설정으로 바꾸도록 하자.
    agent_string = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36"
    s = requests.Session()
    s.headers.update({'User-Agent': agent_string})

    # genreName으로 baseUrl을 담자.
    hajaBaseUrl = "https://torrenthaja.com/bbs/board.php?bo_table=" + tvGenreName
    # page를 path로 지정 하므로, 2page부터 사용할 pagePath를 담을 문자열.
    hajaPagePath = ""
    # 목록을 파싱하여 생성한 object 목록들을 추가할 array.
    hajaContentlist = []
    pageCountForFeed = 2
    for pagenum in range(1, pageCountForFeed + 1):

        if pagenum == 1:
            ransleep = (random.random()*80) + 5
            logger.info("sleep: {}".format(ransleep))
            time.sleep(ransleep)
        else:
            hajaPagePath = "?&page=" + str(pagenum)
        
        # 생성된 주소로 연결 한다.
        r = s.get(hajaBaseUrl + hajaPagePath)
        logger.info("Download status: {} / {}".format(r.status_code, hajaBaseUrl + hajaPagePath))
        if r.status_code == 200:
            data = r.content
            #logger.info("Data : {}".format(data))
            hajaContentlist = hajaContentlist + hajalisthtml2obj(data.decode())
            # 바깥 for loop 를 설정에 의해 제어하도록 하면서, 이곳의 값도 그 값을 가지고 처리 하도록 변경 해야 한다.
            if pagenum == pageCountForFeed: break
            ransleep = (random.random()*8) + 2
            logger.info("sleep: {}".format(ransleep))
            time.sleep(ransleep)
    return hajaContentlist


def saveJsonArticle(listobj, type):
    formatedJsonStr = json.dumps(listobj, indent=4, sort_keys=False, ensure_ascii=False)
    logger.debug("Formatted json: {}".format(formatedJsonStr))
    feedlib_path = os.path.join(rspath, CONST.feedlib_path_name, type)
    f = open(feedlib_path, 'w')
    f.write(formatedJsonStr)
    f.close()

def checkRecentUpdate():
    current = time.time()
    logger.debug("Current time: {}".format(current))
    last_modified_date = 0
    mtime = 0
    for file in os.listdir(os.path.join(rspath, CONST.feedlib_path_name)):
        if file.endswith(".json") and file.startswith("haja_"):
            libfile = os.path.join(rspath, CONST.feedlib_path_name, file)
            try:
                mtime = os.path.getmtime(libfile)
            except OSError:
                mtime = 0

            difftime = (current - mtime) / 60
            logger.debug("Current feed update time: {}. Diff(min): {}.".format(mtime, difftime))

            if difftime < 40:
                logger.info("Already updated just before {0:.2f}(min). Skip update feedlib. ".format(difftime))
                return False
    return True


def updatehajafeed():
    if not checkRecentUpdate():
        return

    saveJsonArticle(getHajaKtvList("torrent_drama"), "haja_" + CONST.dramafeedlib_name)
    saveJsonArticle(getHajaKtvList("torrent_ent"),   "haja_" + CONST.entertainmentfeedlib_name)
    saveJsonArticle(getHajaKtvList("torrent_docu"),  "haja_" + CONST.documentaryfeedlib_name)


def getLastEpsoideNumberAtPlex(season_root, seriesname, seasonnumber):
    # season root 디렉토리가 없다면 기본 값을 반환.
    if not os.path.isdir(season_root):
        logger.warn("Season root path is not exist: {}".format(season_root))
        return 0

    # 마지막 번호를 구해서 반환. 파일조차 없다면. 0을 반환.
    videoList = glob.glob(os.path.join(season_root, seriesname + "*"))
    logger.info("{}'s video file count: {}".format(seriesname, str(len(videoList))))

    if len(videoList) == 0:
        return 0

    epnumlist = []
    for aep in videoList:
        aep1 = ntpath.basename(aep).split('.')[0]
        aep2 = aep1.replace(seriesname, "", 1)
        aep3 = aep2.split('-')[1].strip()
        aep4 = aep3.replace("s" + str(seasonnumber) + "e", "", 1)
        #logger.debug("    - name: [{}]".format(aep4))
        epnumlist.append(aep4)

    return max(epnumlist)

def getLastEpsoideDateAtPlex(season_root, seriesname):
    # season root 디렉토리가 없다면 기본 값을 반환.
    if not os.path.isdir(season_root):
        logger.warn("Season root path is not exist: {}".format(season_root))
        ## 좀 과거의 값을 반환 하도록 한다.
        ayearago = datetime.now() - relativedelta(years=1)
        return ayearago.strftime("%Y-%m-%d")

    # 마지막 날짜를 구해서 반환. 파일조차 없다면. 적당한 과거의 날짜를 반환.
    videoList = glob.glob(os.path.join(season_root, seriesname + "*"))
    logger.debug("{}'s video file count: {}".format(seriesname, str(len(videoList))))

    if len(videoList) == 0:
        ## 좀 과거의 값을 반환 하도록 한다.
        ayearago = datetime.now() - relativedelta(years=1)
        return ayearago.strftime("%Y-%m-%d")

    epdatelist = []
    for aep in videoList:
        aep1 = ntpath.basename(aep).split('.')[0]
        aep2 = aep1.replace(seriesname, "", 1).replace(" - ", "", 1).strip()
        logger.debug("    - name: [{}]".format(aep2))
        epdatelist.append(aep2)

    return max(epdatelist)

def getLastEpsoideId(season_root, series_key, epsode_id_type, seriesname, seasonnumber):
    # queue에 다운로드 이력을 먼저 확인 하도록 한다.
    queueFileName = seriesname + ".s" + seasonnumber + ".queue.json"
    queueFile = os.path.join(rspath, CONST.queue_path_name, queueFileName)
    if os.path.isfile(queueFile):
        # 파일이 있다면, 읽어서 마지막 에피소드 정보를 반환 한다.
        logger.debug("Found season queue file: {}.".format(queueFile))
        qf = open(queueFile, 'r')
        queue = json.loads(qf.read())
        qf.close()
        logger.debug("The last epid of queue file is {} ({})".format(queue["last_epid"], queueFileName))
        return queue["last_epid"]
    else:
        # 파일이 없다면, season root path를 읽어서 마지막 값을 반환 한다.
        logger.debug("Search: {}".format(season_root))
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

    #logger.debug("s4: {}".format(s4))
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
                logger.debug("w to datetime_object: {} -> {} / {}".format(w, dto, df))
                delta = now - dto
                logger.debug("diff date: {} days".format(delta.days))
                if delta.days < 32 and delta.days > -1:
                    if dto > leiddt:
                        dstr = dto.strftime("%Y-%m-%d")
                        #logger.debug("return new episode date: [{}]".format(dstr))
                        return dstr
            except ValueError as e:
                #logger.warn("{}".format(e))
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
                    logger.debug("return new episode number: e[{}]".format(val))
                    return val
            except TypeError as e:
                logger.warn("TypeError word[{}, {}]: {}".format(w, epnum, e))
                continue
            except ValueError as e:
                logger.warn("ValueError word[{}, {}]: {}".format(w, epnum, e))
                continue

            logger.debug("E start word: {}".format(w))
    return None

def getTopPriorityEp(el, k):
    logger.debug("Lenght: {}. epid: {}".format(len(el), k))

    ## 개수가 하나라면, 그 하나를 다운로드 받도록. 아니라면, 가장 적절한 것(?)을 찾도록.

    pl = el[0]["ed"]["feed"]["priority"]

    if len(el) == 0:
        return None

    ## 하나 일때 다운로드 받게 하려면, 아래 코드로 처리 가능하지만, 릴그룹/인코딩여부를 반환하기 애매 하므로 일단 보류 한다.
    '''if len(el) == 1:
        logger.info("(getTopPriorityEp)Just one content: {}".format(el[0]["title"]))
        return el[0]'''

    for p in pl:
        #logger.debug("priority: {}".format(p))
        logger.debug("resolution: {}, release_group: {}, force_audio_encoding:{}, force_video_encoding{}".format(p["resolution"], p["release_group"], p["force_audio_encoding"], p["force_video_encoding"]))

        for e in el:
            #logger.debug("title: {}".format(e["title"]))
            if e["title"].upper().find(p["resolution"].upper()) > -1:
                if e["title"].upper().find(p["release_group"].upper()) > -1:
                    e["resolution"] = p["resolution"]
                    e["release_group"] = p["release_group"]
                    e["force_audio_encoding"] = p["force_audio_encoding"]
                    e["force_video_encoding"] = p["force_video_encoding"]
                    logger.info("(getTopPriorityEp)Matched top priority: {}".format(e["title"]))
                    return e

    logger.info("(getTopPriorityEp)No match found: {}".format(el))
    return None

def attachDownload(httpsHost, urlPath, my_referer, localPath, name):
    #referer 설정을 위해 httplib.HTTPConnection를 사용 해야 한다.
    logger.info("httpsHost: {}, urlPath: {}, name: {}, my_referer: {}, localPath: {}".format(httpsHost, urlPath, name, my_referer, localPath))

    s = requests.Session()
    s.headers.update({'referer': my_referer})
    r = s.get("https://" + httpsHost + "/" + urlPath)
    logger.info("Download status: {}".format(r.status_code))
    if r.status_code == 200:
        data = r.content

        f = open(os.path.join(localPath, name), 'wb')
        f.write(bytearray(data))
        f.close()

def updateQueue(tpe, title_keywords):
    #logger.debug("tpe for Update queue: {}".format(tpe))
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
    cep["publisher"] = tpe["publisher"]
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
            logger.warn("epid {} at {} is already is exist.".format(str(tpe["epid"]), seriesName))
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
            logger.error("Unknown epsodie id tpye: {}".format(epidType))

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
    #logger.debug("Update queue: {}".format(queueStr))
    qf = open(queueFile, 'w')
    qf.write(queueStr)
    qf.close()

# kim에서 받아 torrentmission-daemon에 추가 한다.
def downloadFromHajaMagnet(tpe, title_keywords):
    #logger.debug("(downloadToIncomming)tep:{}".format(tpe))
    ed = tpe["ed"]
    pr = urlparse(tpe["url"])
    logger.info("epsode detail page: {}".format(tpe["url"]))
    #logger.debug("parser result:{}".format(pr))

    conn = http.client.HTTPSConnection(pr.netloc)
    conn.request("GET", pr.path)
    r1 = conn.getresponse()
    logger.debug("Status: {}, Reason: {}".format(r1.status, r1.reason))
    if r1.status == 200:
        data2 = r1.read()
        #logger.debug("content html: {}".format(data2))
        soup = BeautifulSoup(data2, "lxml")
        
        ## Note: soup('table', {'class':'table table-hover'})
        ## Note: <button type="button" class="btn btn-success btn-xs" onclick="magnet_link('3FDE517AA51BBE67F1C0D5E43858ED4F4BEA385E');">
        ## Note: magnet:?xt=urn:btih:
        
        # magnet hash link를 포함한 버튼.
        mgbutton = soup("button", {'class':'btn btn-success btn-xs'})
        mgbutton_onclick_str = mgbutton[0]['onclick']
        magnet_string = mgbutton_onclick_str.replace('magnet_link(\'', 'magnet:?xt=urn:btih:').replace('\');', '')
        
        logger.debug("magnet button: {}".format(mgbutton[0]))
        logger.debug("magnet button onclick: {}".format(mgbutton_onclick_str))
        logger.debug("magent hash: {}".format(magnet_string))
        
        logger.info("Start adding magnet: {}({}) s{} e{} : {}".format(ed["series_name"], ed["release_year"], ed["season_number"], tpe["epid"], tpe["title"]))

        cmdstr = "transmission-remote --auth=" + ctru + ":" + ctrp + " -a \"" + magnet_string + "\""
        result = subprocess.check_output(cmdstr, shell=True)
        logger.info("Complete adding magnet. result: {}".format(result))

        ## queue 정보를 갱신 한다. 시리즈 이름. 다운로드 추가 된 에피소드 정보.
        updateQueue(tpe, title_keywords)

    conn.close()


def downloadToIncomming(tpe, title_keywords):
    #logger.debug("(downloadToIncomming)tep:{}".format(tpe))
    pr = urlparse(tpe["url"])
    logger.info("epsode detail page: {}".format(tpe["url"]))
    #logger.debug("parser result:{}".format(pr))

    conn = http.client.HTTPSConnection(pr.netloc)
    conn.request("GET", pr.path + "?" + pr.query)
    r1 = conn.getresponse()
    logger.debug("Status: {}, Reason: {}".format(r1.status, r1.reason))
    if r1.status == 200:
        data2 = r1.read()
        #logger.debug("content html: {}".format(data2))
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
                    logger.info("download path: {}".format(cp))
                    logger.info("download file name: {}".format(cn))

                    # 확장자 명에 따라 파일을 업로드 한다.
                    # 혹시 자막파일이면 나중에 찾아서 쓸 수 있도록 다운로드 경로에 미리 저장해 두자.
                    ##TODO: torrent로 끝나지 않는 torrent 파일이 있다. magnet을 이용해야 하나?
                    watchDirPath = "/storage/local/mforce2-local/transmission-daemon/watch-dir"
                    downloadDirPath = "/storage/local/mforce2-local/transmission-daemon/downloads"
                    if cn.endswith('.torrent'):
                        targetPath = watchDirPath
                    else:
                        if cn[-4:-3] == ".":
                            targetPath = downloadDirPath
                        else:
                            targetPath = watchDirPath
                            cn = cn + ".torrent"

                    # 실제 다운로드 시작
                    attachDownload(pr.netloc, cp, tpe["url"], targetPath, cn)
                    ransleep = random.random()*10
                    logger.info("download complete. sleep: {}".format(ransleep))
                    time.sleep(ransleep)

        ## queue 정보를 갱신 한다. 시리즈 이름. 다운로드 추가 된 에피소드 정보.
        updateQueue(tpe, title_keywords)

    conn.close()

def discoveryAndDownload(ed, leid, feedlibs):
    feed = ed["feed"]
    title_keywords = feed["necessary_title_keywords"]
    epsode_id_type = feed["epsode_id_type"]

    match1feeds = list()
    for nfs in reversed(feedlibs):
        matched = True
        for tk in title_keywords:
            if nfs["title"].upper().find(str(tk).upper()) < 0:
                matched = False
        if matched:
            match1feeds.append(nfs)

    logger.debug("match1feeds size: {}".format(len(match1feeds)))

    match2feeds = list()
    # 검색된 것이 새로운 에피소드인지 확인 한다.
    for ffs in match1feeds:
        logger.debug("matched: {}".format(ffs["title"]))
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

    logger.debug("match2feeds size: {}".format(len(match2feeds)))

    # 우선순위가 높은 것 하나만 선택하는 작업을 위해 같은 에피소드끼리 묶는다.
    match3feedDic = {}
    for f2f in match2feeds:
        epid = f2f["epid"]
        if not epid in match3feedDic:
            neplist = []
            neplist.append(f2f)
            match3feedDic[epid] = neplist
            logger.debug("match3feedDic - new: [{}] {}".format(epid, len(match3feedDic[epid])))
        else:
            neplist = match3feedDic.get(epid)
            neplist.append(f2f)
            logger.debug("match3feedDic - add: [{}] {}".format(epid, len(match3feedDic[epid])))

    #logger.debug("{}".format(json.dumps(match3feedDic, indent=4, sort_keys=False, ensure_ascii=False)))

    # 각 에페소드별로 하나의 게시물만 골라내는 함수를 호출한다.
    for k in match3feedDic.keys():
        te = getTopPriorityEp(match3feedDic.get(k), k)
        logger.debug("Top priority epsode: {}".format(json.dumps(te, indent=4, sort_keys=False, ensure_ascii=False)))
        if te:
            #downloadToIncomming(te, title_keywords)
            #downloadFromWizMagnet(te, title_keywords)
            #downloadFromKimMagnet(te, title_keywords)
            downloadFromHajaMagnet(te, title_keywords)

    logger.debug("===============================================================================")


def discoveryEpsoidesFromAllFeed(dy, feedlibs):
    ed = yaml.load(codecs.open(dy, "r", "utf-8"))
    logger.info("Current series is \"{} ({})\".".format(ed["series_name"], ed["release_year"]))

    plexlib_path = ed["plexlib_season_root"]
    feedinfo = ed["feed"]
    serieskey = ed["series_key"]
    seriesname = ed["series_name"]
    seasonnumber = ed["season_number"]
    eptype = feedinfo["epsode_id_type"]
    leid = getLastEpsoideId(plexlib_path, serieskey, eptype, seriesname, seasonnumber)
    logger.info("Last epsoid id: {}".format(leid))
    #keys = ed.feed.necessary_title_keywords
    # 받아야 할 모든 항목을 feed-json에서 확인
    #  - keyword로 찾은 다음. epsoide 번호 기준 새로운 항목을 확인.
    # 새로운 항목은 torrent 파일을 다운로드 받아 추가.
    # 다운로드 정보 파일에 정보를 추가.
    discoveryAndDownload(ed, leid, feedlibs)


def findNewHajaEpsoides():
    # feedlib/*.json 파일들을 읽어 들인다.
    feedlibs = []
    for feedfile in glob.glob(os.path.join(rspath, CONST.feedlib_path_name) + '/haja_*.json'):
        ff = open(feedfile, 'r')
        feedlibs = feedlibs + json.loads(ff.read())
        ff.close()

    logger.debug("feedlibs length: {}".format(len(feedlibs)))

    # seriesdef/*.def.yaml 파일들을 읽어 들인다.
    for name in glob.glob(os.path.join(rspath, CONST.seriesdef_path_name) + '/*.def.yaml'):
        logger.debug("Feed list file: {}".format(name))
        discoveryEpsoidesFromAllFeed(name, feedlibs)


def main():
    try:
        checkrspath()
        startLogging()
        loadConfig()
        updatehajafeed()
        findNewHajaEpsoides()
    except OSError as oerr:
        logger.error("OS error: {0}".format(oerr))
        print("OS error: {0}".format(oerr))
    except NameError as nerr:
        logger.error("Name error: {0}".format(nerr))
        print("Name error: {0}".format(nerr))
    except ValueError as verr:
        logger.error("ValueError: {0}".format(verr))
        print("Value error: {0}".format(verr))
    except KeyError as kerr:
        logger.error("KeyError error: {0}".format(kerr))
        print("KeyError error: {0}".format(kerr))
    except TypeError as terr:
        logger.error("TypeError error: {0}".format(terr))
        print("TypeError error: {0}".format(terr))
    except IndexError as ierr:
        logger.error("IndexError error: {0}".format(ierr))
        print("IndexError error: {0}".format(ierr))
    except AttributeError as aerr:
        logger.error("AttributeError error: {0}".format(aerr))
        print("AttributeError error: {0}".format(aerr))
    except:
        logger.error("Unexpected error: {}".format(sys.exc_info()[0]))

    logger.info("All task complete.")
    logger.info("===============================================")
    logger.info("-----------------------------------------------")

if __name__ == "__main__":
    main()
