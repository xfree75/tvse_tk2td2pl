#!/usr/bin/env python3

import sys
import getopt
import logging
import os
import yaml
import codecs
import time
import http.client
import requests
import random
import base64
import json
import glob
import ntpath
import subprocess

from urllib.parse import urlparse
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

def help():
   print("print help usage: {} -bfp5".format(os.path.basename(__file__)))
   print("    -b, --burst_process: ignore time sleep for feed update & add torrent.")
   print("    -f, --force_update: force feed refresh.")
   print("    -p 5, --pages=5: read pages for feed refreash.")
   return

def readArgument(argv):
    global burst_process
    global force_update
    global pages
    burst_process = False
    force_update = False
    pages = 4 
    try:
        opts, etc_args = getopt.getopt(argv[1:], "hbfp:", ["help", "burst_process", "force_update", "pages="])
    except getopt.GetoptError as err:
        print("Argument Error: {}".format(err))
        sys.exit(1)
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            help()
            sys.exit()
        elif opt in ("-b", "--burst_process"):
            burst_process = True
        elif opt in ("-f", "--force_update"):
            force_update = True
        elif opt in ("-p", "--pages"):
            pages = arg 

    print("Argument option - burst_procss: {}, force_update: {}, pages: {}".format(burst_process, force_update, pages)) 

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

    global proxy_host
    global proxy_port
    global proxy_auth_username
    global proxy_auth_password
    proxy_host = config["proxy_host"]
    proxy_port = str(config["proxy_port"])
    proxy_auth_username = config["proxy_auth_username"]
    proxy_auth_password = config["proxy_auth_password"]

    global base_dn
    base_dn = config["base_dn_zota"]

def checkRecentUpdate():
    if force_update == True:
        return True
    current = time.time()
    logger.debug("Current time: {}".format(current))
    last_modified_date = 0
    mtime = 0
    for file in os.listdir(os.path.join(rspath, CONST.feedlib_path_name)):
        if file.endswith(".json") and file.startswith("zota_"):
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

def boartlisthtml2obj(htmlstring):
    soup = BeautifulSoup(htmlstring, "lxml")
    soup_board_list = soup('div', {'class':'py-2 flex flex-col xl:flex-row'})
    #logger.debug("html-1: {}".format(soup_board_list[0].prettify(formatter="html")))
    soup_trlist = soup_board_list[0].find_all('a', {'class':'item-link'})
    #logger.debug("html-2: {}".format(soup_trlist[1].prettify(formatter="html")))
    #sys.exit()

    # 반환할 object array.
    torrcontentlist = []
    # 파싱할때 element 속의 elements 골라 지울 수 있도록.
    #__text_strip_str="{[**wiz**]}"

    listidx = 0
    for soup_tr in soup_trlist:
        listidx = listidx + 1
        #logger.debug("tr html: {}".format(soup_tr.prettify(formatter="html")))

        try:
            ##num = soup_tr.find('div', {'class':'wr-num'}).text.strip()
            ##logger.debug("num: {}".format(num))
            
            #title_href = soup_tr.find('a', {'class':'item-subject'})
            title = soup_tr.text.strip()
            url = soup_tr['href']
            #logger.debug("title-href: {}".format(title_href))
            #logger.debug("title: {}".format(title))
            #logger.debug("href: {}".format(url))
            
            #date = soup_tr.find('div', {'class':'wr-date'}).text.strip()
            #logger.debug("date: {}".format(date))
            
            # object 생성.
            torrcontent = {}
            torrcontent['num']       = ""
            torrcontent['title']     = title
            torrcontent['url']       = "https://" + base_dn + url
            torrcontent['date']      = ""
            #torrcontent['size']      = soup_td_size.string.strip()
            torrcontent['publisher'] = "zota"
            torrcontentlist.append(torrcontent)

        except:
            logger.error("Error: ".format(sys.exc_info()[0]))
            continue
    
    return torrcontentlist

def getKtvList(tvGenreName):
    # wiz에서는 browser agnet 헤더를 확인 하므로... 차후에는 환경 설정으로 바꾸도록 하자.
    # agent_string = "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36"
    agent_string = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/78.0.3904.70 Safari/537.36"
    s = requests.Session()
    s.headers.update({'User-Agent': agent_string})

    # genreName으로 baseUrl을 담자.
    boardBaseUrl = "https://" + base_dn + ":443/t/" + tvGenreName
    # page를 path로 지정 하므로, 2page부터 사용할 pagePath를 담을 문자열.
    boardPagePath = ""
    # 목록을 파싱하여 생성한 object 목록들을 추가할 array.
    boardContentlist = []
    pageCountForFeed = int(pages)
    for pagenum in range(1, pageCountForFeed + 1):

        if pagenum == 1:
            ransleep = (random.random()*8) + 5
            logger.info("sleep for first page: {}".format(ransleep))
            if burst_process == False:
                time.sleep(ransleep)
        
        boardPagePath = "?page=" + str(pagenum)
        
        # 2020.01.19(토) http proxy(smart dns proxy) 추가.
        proxy_uri = "http://" + proxy_auth_username + ":" + proxy_auth_password + "@" + proxy_host + ":" + proxy_port
        url = urlparse(proxy_uri)
        conn = http.client.HTTPSConnection(url.hostname, url.port)
        headers = {}
        if url.username and url.password:
            auth = '%s:%s' % (url.username, url.password)
            #encauth = str(base64.b64encode(auth.encode())).replace("b'", "").replace("'", "")
            headers['Proxy-Authorization'] = 'Basic ' + str(base64.b64encode(auth.encode())).replace("b'", "").replace("'", "")
        
        pr = urlparse(boardBaseUrl + boardPagePath)
        logger.debug("Current page URL: {}".format(pr.geturl()))
        conn.set_tunnel(pr.hostname, pr.port, headers)
        conn.request("GET", pr.path + "?" + pr.query)
        r = conn.getresponse()
        logger.debug("Status: {}, Reason: {}".format(r.status, r.reason))
        
        if r.status == 200:
            data = r.read()
            #logger.info("Data : {}".format(data))
            #logger.info("Data : {}".format(data.decode()))
            boardContentlist = boardContentlist + boartlisthtml2obj(data.decode())
            # 바깥 for loop 를 설정에 의해 제어하도록 하면서, 이곳의 값도 그 값을 가지고 처리 하도록 변경 해야 한다.
            if pagenum == pageCountForFeed: break
            ransleep = (random.random()*8) + 2
            logger.info("sleep for next page: {}".format(ransleep))
            if burst_process == False:
                time.sleep(ransleep)
            
    return boardContentlist

def saveJsonArticle(listobj, type):
    formatedJsonStr = json.dumps(listobj, indent=4, sort_keys=False, ensure_ascii=False)
    logger.debug("Formatted json: {}".format(formatedJsonStr))
    feedlib_path = os.path.join(rspath, CONST.feedlib_path_name, type)
    f = open(feedlib_path, 'w')
    f.write(formatedJsonStr)
    f.close()

def updatefeed():
    if not checkRecentUpdate():
        return

    saveJsonArticle(getKtvList("2/13.html"), "zota_" + CONST.dramafeedlib_name)
    saveJsonArticle(getKtvList("4/16.html"), "zota_" + CONST.entertainmentfeedlib_name)
    saveJsonArticle(getKtvList("4/17.html"), "zota_" + CONST.documentaryfeedlib_name)

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

def downloadFromMagnet(tpe, title_keywords):
    #logger.debug("(downloadToIncomming)tep:{}".format(tpe))
    ed = tpe["ed"]
    pr = urlparse(tpe["url"])
    logger.info("epsode detail page: {}".format(tpe["url"]))
    logger.debug("parser result:{}".format(pr))

    '''conn = http.client.HTTPSConnection(pr.netloc)
    conn.request("GET", pr.path)
    r1 = conn.getresponse()
    logger.debug("Status: {}, Reason: {}".format(r1.status, r1.reason))'''
    
    proxy_uri = "http://" + proxy_auth_username + ":" + proxy_auth_password + "@" + proxy_host + ":" + proxy_port
    proxy_url = urlparse(proxy_uri)
    conn = http.client.HTTPSConnection(proxy_url.hostname, proxy_url.port)
    headers = {}
    if proxy_url.username and proxy_url.password:
        auth = '%s:%s' % (proxy_url.username, proxy_url.password)
        #encauth = str(base64.b64encode(auth.encode())).replace("b'", "").replace("'", "")
        headers['Proxy-Authorization'] = 'Basic ' + str(base64.b64encode(auth.encode())).replace("b'", "").replace("'", "")
    
    #pr = urlparse(pr.path)
    conn.set_tunnel(pr.hostname, pr.port, headers)
    conn.request("GET", pr.path + "?" + pr.query)
    r1 = conn.getresponse()
    logger.debug("Status: {}, Reason: {}".format(r1.status, r1.reason))
    
    if r1.status == 200:
        data2 = r1.read()
        logger.debug("content html: {}".format(data2.decode()))
        soup = BeautifulSoup(data2, "lxml")
        soup_bo_v_img_list = soup.find_all("a")
        #logger.debug("A elements: {}".format(soup_bo_v_img_list))

        for soup_bo_v_img in soup_bo_v_img_list:

            try:
                magnet_string = soup_bo_v_img['href']
                #logger.debug("input value: {} / {}".format(soup_bo_v_img, magnet_string))
                logger.debug("ahtml: {} ".format(soup_bo_v_img))
                logger.debug("url: {} ".format(magnet_string))
                if magnet_string.startswith('magnet:?'):
                    logger.info("Start adding magnet: {}({}) s{} e{} : {}".format(ed["series_name"], ed["release_year"], ed["season_number"], tpe["epid"], tpe["title"]))

                    cmdstr = "transmission-remote --auth=" + ctru + ":" + ctrp + " -a \"" + magnet_string + "\""
                    result = subprocess.check_output(cmdstr, shell=True)
                    logger.info("Complete adding magnet. result: {}".format(result))

                    ## queue 정보를 갱신 한다. 시리즈 이름. 다운로드 추가 된 에피소드 정보.
                    updateQueue(tpe, title_keywords)

            except KeyError as kerr:
                logger.debug("KeyError cause by none value. html: {}".format(soup_bo_v_img))
                continue

    conn.close()

def discoveryAndDownload(ed, leid, feedlibs):
    feed = ed["feed"]
    title_keywords = feed["necessary_title_keywords"]
    epsode_id_type = feed["epsode_id_type"]

    #logger.debug("feedlibs: {}".format(feedlibs))
    match1feeds = list()
    for nfs in reversed(feedlibs):
        matched = True
        for tk in title_keywords:
            #logger.debug("tk: {}, nfs.title: {}".format(tk, nfs["title"]))
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
            downloadFromMagnet(te, title_keywords)

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

def findNewEpsoides():
    # feedlib/*.json 파일들을 읽어 들인다.
    feedlibs = []
    for feedfile in glob.glob(os.path.join(rspath, CONST.feedlib_path_name) + '/zota_*.json'):
        ff = open(feedfile, 'r')
        feedlibs = feedlibs + json.loads(ff.read())
        ff.close()

    logger.debug("feedlibs length: {}".format(len(feedlibs)))

    # seriesdef/*.def.yaml 파일들을 읽어 들인다.
    for name in glob.glob(os.path.join(rspath, CONST.seriesdef_path_name) + '/*.def.yaml'):
        logger.debug("Feed list file: {}".format(name))
        discoveryEpsoidesFromAllFeed(name, feedlibs)

def main(argv):
    readArgument(argv)
    try:
        checkrspath()
        startLogging()
        loadConfig()
        updatefeed()
        findNewEpsoides()
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
    sys.exit()

if __name__ == "__main__":
    main(sys.argv)
