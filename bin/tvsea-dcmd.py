#!/usr/bin/env python3


import os
import sys
import logging
import json
import glob
from datetime import datetime


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
    print("Complete initialize logging. logfile: {}".format(logfile))
    logging.info("Start script.")

def acquireLock():
    lockfile = os.path.join(rspath, "lock")
    if os.path.isfile(lockfile):
        logging.info("Process is already running.")
        sys.exit()
    else:
        current = datetime.now()
        lfo = open(lockfile, 'w')
        lfo.write(str(current))
        lfo.close()
    
def unLock():
    lockfile = os.path.join(rspath, "lock")
    if os.path.isfile(lockfile):
        os.remove(lockfile)
    
def matchDownloadFile(f, key_words, epid, epsode_id_type, resolution, release_group):
    fu = f.upper()
    #logging.debug("Try matching: {}. words: {}, epid: {}, resolution: {}, release group: {}".format(f, key_words, epid, resolution, release_group))
    
    for kw in key_words:
        if fu.find(kw.upper()) < 0:
            #logging.debug("Fail keyword matching: {} {}".format(kw.upper(), fu.find(kw.upper())))
            return False
            
    if epsode_id_type == "date":
        dateMatch = False
        if fu.find(epid) > 0:
            dateMatch = True
        #TODO 날짜 형식을 바꿔 가면셔 모두 테스트 해본다.
        #"%y%m%d", "%y.%m.%d", "%y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y-%m-%d"
        dateformats = ["%y%m%d", "%y.%m.%d", "%y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y-%m-%d"]
        ep_dt = datetime.strptime(epid, "%Y-%m-%d")
        for df in dateformats:
            if not dateMatch:
                if fu.find(ep_dt.strftime(df)) > 0:
                    dateMatch = True
                    
        if not dateMatch:
            logging.debug("Fail epid matching: {}".format(ep_dt))
            return False
    else:
        if fu.find("E" + str(epid)) < 0:
            logging.debug("Fail epid matching: {}".format("E" + str(epid)))
            return False
    
    if fu.find(resolution.upper()) < 0:
        logging.debug("Fail resolution matching: {}".format(resolution.upper()))
        return False
    if fu.find(release_group.upper()) < 0:
        logging.debug("Fail epid matching: {}".format(release_group.upper()))
        return False
    
    #logging.debug("found match: {}. words: {}, epid: {}, resolution: {}, release group: {}".format(f, key_words, epid, resolution, release_group))
    return True
    
def checkWriteComplete(f):
    # 현재 그 파일의 크기를 확인.
    statinfo = os.stat(f)
    curr_size = statinfo.st_size
    sizef = f + ".size"
    if os.path.isfile(sizef):
        f = open(sizef, 'r')
        prev_size = f.readline()
        if prev_size == str(curr_size):
            return True
    else:
        f = open(sizef, 'w')
        f.write(str(curr_size))
        f.close()
    
    return False
    
def queueUpdate(queue_name):
    ##TODO: 환경설정 값으로 바꾸어야 한다.
    tm_d_path = "/storage/local/mforce2-local/transmission-daemon/downloads"
    tm_d_files = glob.glob(os.path.join(tm_d_path, "*"))
    logging.debug("transmission download file list: {}".format(tm_d_files))
    
    qf = open(queue_name, 'r')
    queue = json.loads(qf.read())
    qf.close()
    logging.debug("queue: {}".format(json.dumps(queue, indent=4, sort_keys=False, ensure_ascii=False)))
    
    ep_dic = queue["ep_dic"]
    key_words = queue["title_keywords"]
    series_name = queue["series_name"]
    release_year = queue["release_year"]
    epsode_id_type = queue["epsode_id_type"]
    for epid in ep_dic.keys():
        download_content = ep_dic[epid]
        logging.debug("queud epid: {}, download complete: {}".format(download_content["epid"], download_content["download_complete"]))
        if not download_content["download_complete"]:
            resolution = download_content["resolution"]
            release_group = download_content["release_group"]
            for f in tm_d_files:
                # .size로 이름이 끝나는 파일은 제외.
                if not f.endswith(".size"):
                    if matchDownloadFile(os.path.basename(f), key_words, epid, epsode_id_type, resolution, release_group):
                        logging.info("match download file for {}/{}/e{}: {}".format(series_name, release_year, epid, os.path.basename(f)))
                        if checkWriteComplete(f):
                            logging.info("Download complete. Updating queue download stat.")
                            download_content["download_complete"] = True
                            download_content["tvshow_file"] = os.path.basename(f)
    
    qf = open(queue_name, 'w')
    queue = qf.write(json.dumps(queue, indent=4, sort_keys=False, ensure_ascii=False))
    qf.close()

    
def downloadQueuesUpdate():
    '''
    queue를 읽어 다운로드에 추가된 파일을 확인.
    다운로드 경로에서 해당 하는 파일을 검색.
    검색된 파일의 .size 파일이 존재 하는지 확인.
    만약 .size 파일이 존재한다면,
        이 파일에 기록된 크기와 파일의 크기를 확인하여 같다면, queue에 상태 반영
        아니면, 파일 크기를 확인하여 저장
    '''
    ## queue/*.queue.json 파일들을 읽어 들인다.
    for queue_name in glob.glob(os.path.join(rspath, CONST.queue_path_name) + '/*.queue.json'):
        logging.debug("Queue file: {}".format(queue_name))
        queueUpdate(queue_name)
    
def distByMv(q, d, t):
    logging.info("dist - Just move {}".format(t))
    ##TODO: 환경설정 값으로 바꾸어야 한다.
    tm_d_path = "/storage/local/mforce2-local/transmission-daemon/downloads"
    source = os.path.join(tm_d_path, d["tvshow_file"])
    target = os.path.join(q["plexlib_season_root"], t)
    if os.path.isfile(source):
        os.rename(source, target)
    else:
        logging.warn("Source file is not exist: {}".format(source))
    ## download 경로의 .size 파일 제거.
    if os.path.isfile(source + ".size"):
        os.remove(source + ".size")
    ##TODO: 보관 개수 보다 많은 항목은 자동 삭제.
    
def distByRepac(q, d, t):
    logging.info("dist - Just repackaging {}".format(t))
    ##TODO: 환경설정 값으로 바꾸어야 한다.
    tm_d_path = "/storage/local/mforce2-local/transmission-daemon/downloads"
    source = os.path.join(tm_d_path, d["tvshow_file"])
    cstr = "ktvshowhdenc --no-interact --rm-source --over-write"
    cstr = cstr + " --out-path \"" + q["plexlib_season_root"] + "/\""
    cstr = cstr + " --out-name \"" + t + "\""
    cstr = cstr + " --ff-vcp true "
    cstr = cstr + " --ff-acp true "
    cstr = cstr + " \"" + source + "\""
    logging.info("Command: {}".format(cstr))
    os.system(cstr)
    
    ##TODO: download 경로의 .size 파일 제거.
    if os.path.isfile(source + ".size"):
        os.remove(source + ".size")
    ##TODO: 보관 개수 보다 많은 항목은 자동 삭제.
    
def distByTrans(q, d, t):
    logging.info("dist - with transcoding {}, v:{}, a:{}.".format(t, d["force_video_encoding"], d["force_audio_encoding"]))
    # 환경설정 값으로 바꾸어야 한다.
    tm_d_path = "/storage/local/mforce2-local/transmission-daemon/downloads"
    source = os.path.join(tm_d_path, d["tvshow_file"])
    target = os.path.join(q["plexlib_season_root"], t)
    cstr = "ktvshowhdenc --no-interact --rm-source --over-write"
    cstr = cstr + " --out-path \"" + q["plexlib_season_root"] + "/\""
    cstr = cstr + " --out-name \"" + t + "\""
    if not d["force_video_encoding"]:
        cstr = cstr + " --ff-vcp true "
    if not d["force_audio_encoding"]:
        cstr = cstr + " --ff-acp true "
    cstr = cstr + " \"" + source + "\""
    logging.info("Command: {}".format(cstr))
    os.system(cstr)
    
    # download 경로의 .size 파일 제거.
    if os.path.isfile(source + ".size"):
        os.remove(source + ".size")
    ##TODO: 보관 개수 보다 많은 항목은 자동 삭제.
    
def dist(queue_name):
    qf = open(queue_name, 'r')
    queue = json.loads(qf.read())
    qf.close()
    
    ep_dic = queue["ep_dic"]
    series_name = queue["series_name"]
    season_number = queue["season_number"]
    release_year = queue["release_year"]
    epsode_id_type = queue["epsode_id_type"]
    for epid in ep_dic.keys():
        download_content = ep_dic[epid]
        if download_content["download_complete"]:
            # 라이브러리에 저장될 파일 이름.
            lib_target_name = ""
            if epsode_id_type == "date":
                lib_target_name = series_name + " - " + epid + ".m4v"
            else:
                lib_target_name = series_name + " - s" + season_number + "e" + epid + ".m4v"
            
            vcp = not download_content["force_video_encoding"]
            acp = not download_content["force_audio_encoding"]
            if vcp and acp:
                download_content["tvshow_file"]
                name, ext = os.path.splitext(download_content["tvshow_file"])
                if ext == ".mp4" or ext == ".m4v":
                    distByMv(queue, download_content, lib_target_name)
                    #TODO: 처리 완료 후 queue에서 항목 제거
                    #TODO: 제거 했던 내용을 완료 이력에 저장
                else:
                    if ext == ".mkv":
                        distByRepac(queue, download_content, lib_target_name)
                        #TODO: 처리 완료 후 queue에서 항목 제거
                        #TODO: 제거 했던 내용을 완료 이력에 저장
                    else:
                        distByTrans(queue, download_content, lib_target_name)
                        #TODO: 처리 완료 후 queue에서 항목 제거
                        #TODO: 제거 했던 내용을 완료 이력에 저장
            else:
                distByTrans(queue, download_content, lib_target_name)
                #TODO: 처리 완료 후 queue에서 항목 제거
                #TODO: 제거 했던 내용을 완료 이력에 저장
    
    #TODO: 처리 완료된 항목이 제거된 queue를 다시 저장.
    
def dist2plexlib():
    ## queue/*.queue.json 파일들을 읽어 들인다.
    for queue_name in glob.glob(os.path.join(rspath, CONST.queue_path_name) + '/*.queue.json'):
        logging.debug("Queue file: {}".format(queue_name))
        dist(queue_name)
    
def main():
    checkrspath()
    startLogging()
    # lock 여부 확인 및 locking 
    acquireLock()
    downloadQueuesUpdate()
    dist2plexlib()
    # unlocking
    unLock()

if __name__ == "__main__":
    main()
