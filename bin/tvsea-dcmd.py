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
    def history_path_name():
        return "history"
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
    global logger
    logger = logging.getLogger(os.path.basename(__file__))
    fomatter = logging.Formatter('[%(levelname)s|%(filename)s:%(lineno)s] %(asctime)s > %(message)s')
    fileHandler = logging.FileHandler(logfile)
    fileHandler.setFormatter(fomatter)
    logger.addHandler(fileHandler)
    logger.setLevel(logging.DEBUG)
    print("Complete initialize logging. logfile: {}".format(logfile))
    logger.info("Start script.")

def acquireLock():
    lockfile = os.path.join(rspath, "lock")
    if os.path.isfile(lockfile):
        logger.info("Process is already running.")
        sys.exit()
    else:
        current = datetime.now()
        lfo = open(lockfile, 'w')
        lfo.write(str(current))
        lfo.close()
    
def unLock():
    lockfile = os.path.join(rspath, "lock")
    if os.path.isfile(lockfile):
        logger.debug("Prev remove lockfile: {}".format(lockfile))
        try:
            os.remove(lockfile)
        except OSError as err:
            logger.error("OS error: {0}".format(err))
        except ValueError:
            logger.error("Could not convert data to an integer.")
        except:
            logger.error("Unexpected error:", sys.exc_info()[0])
        logger.debug("Complete remove lockfile: {}".format(lockfile))
    else:
        logger.warn("remove lockfile - lock file is not exist: {}".format(lockfile))
    
    
def matchDownloadFile(f, key_words, epid, epsode_id_type, resolution, release_group):
    fu = f.upper()
    #logger.debug("Try matching: {}. words: {}, epid: {}, resolution: {}, release group: {}".format(f, key_words, epid, resolution, release_group))
    
    for kw in key_words:
        if fu.find(str(kw).upper()) < 0:
            #logger.debug("Fail keyword matching: {} {}".format(str(kw).upper(), fu.find(str(kw).upper())))
            return False
            
    if epsode_id_type == "date":
        dateMatch = False
        if fu.find(epid) > 0:
            dateMatch = True
        # 날짜 형식을 바꿔 가면셔 모두 테스트 해본다.
        # "%y%m%d", "%y.%m.%d", "%y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y-%m-%d"
        dateformats = ["%y%m%d", "%y.%m.%d", "%y-%m-%d", "%Y%m%d", "%Y.%m.%d", "%Y-%m-%d"]
        ep_dt = datetime.strptime(epid, "%Y-%m-%d")
        for df in dateformats:
            if not dateMatch:
                if fu.find(ep_dt.strftime(df)) > -1:
                    dateMatch = True
                    
        if not dateMatch:
            logger.debug("Fail epid matching: {}".format(ep_dt))
            return False
    else:
        epids = str(epid)
        if int(epid) < 10:
            epids = "0" + str(epid)
        if fu.find("E" + str(epids)) < 0:
            logger.debug("Fail epid matching: {}".format("E" + str(epid)))
            return False
    
    if fu.find(resolution.upper()) < 0:
        logger.debug("Fail resolution matching: {}".format(resolution.upper()))
        return False
    if fu.find(release_group.upper()) < 0:
        logger.debug("Fail epid matching: {}".format(release_group.upper()))
        return False
    
    #logger.debug("found match: {}. words: {}, epid: {}, resolution: {}, release group: {}".format(f, key_words, epid, resolution, release_group))
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
    logger.debug("transmission download file list: {}".format(tm_d_files))
    
    qf = open(queue_name, 'r')
    queue = json.loads(qf.read())
    qf.close()
    logger.debug("queue: {}".format(json.dumps(queue, indent=4, sort_keys=False, ensure_ascii=False)))
    
    ep_dic = queue["ep_dic"]
    key_words = queue["title_keywords"]
    series_name = queue["series_name"]
    release_year = queue["release_year"]
    epsode_id_type = queue["epsode_id_type"]
    
    queue_update_flag = False
    for epid in ep_dic.keys():
        download_content = ep_dic[epid]
        logger.debug("queud epid: {}, download complete: {}".format(download_content["epid"], download_content["download_complete"]))
        if not download_content["download_complete"]:
            resolution = download_content["resolution"]
            release_group = download_content["release_group"]
            for f in tm_d_files:
                # .size로 이름이 끝나는 파일은 제외.
                if not f.endswith(".size"):
                    if matchDownloadFile(os.path.basename(f), key_words, epid, epsode_id_type, resolution, release_group):
                        logger.info("match download file for {}/{}/e{}: {}".format(series_name, release_year, epid, os.path.basename(f)))
                        if checkWriteComplete(f):
                            logger.info("Download complete. Updating queue download stat.")
                            download_content["download_complete"] = True
                            download_content["tvshow_file"] = os.path.basename(f)
                            queue_update_flag = True
    
    if queue_update_flag: 
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
        logger.debug("Queue file: {}".format(queue_name))
        queueUpdate(queue_name)
    
def removeOldEpsoide(path, count):
    # count 가 0 이라면 무시된다.
    if count == 0:
        return None
    # 파일 목록을 불러 온다.
    # 역순으로 정렬한다.
    # 개수 이후의 index를 가지는 파일은 삭제 한다.
    logger.debug("remove old. path: {}, count: {}".format(path, count))
    media_list = glob.glob(path + "/*.m4v")
    logger.debug("remove old. path: {}, limit cnt: {}, current cnt:{}".format(path, count, len(media_list)))
    media_list.sort()
    media_list.reverse()
    mfile_count = 1
    for media in media_list:
        if mfile_count > count:
            os.remove(media)
            logger.info("removed old file:{}".format(media))
        mfile_count = mfile_count + 1
    
def distByMv(q, d, t):
    logger.info("dist - Just move {}".format(t))
    ##TODO: 환경설정 값으로 바꾸어야 한다.
    tm_d_path = "/storage/local/mforce2-local/transmission-daemon/downloads"
    source = os.path.join(tm_d_path, d["tvshow_file"])
    target = os.path.join(q["plexlib_season_root"], t)
    
    # 소스파일이 존재 하지 않는다면, error logging 후 return.
    if not os.path.isfile(source):
        logger.error("Source file is not exist: {}".format(source))
        return False
        
    os.rename(source, target)
    logger.info("Complete move to plex lib: {}".format(target))
    
    # download 경로의 .size 파일 제거.
    if os.path.isfile(source + ".size"):
        os.remove(source + ".size")
        
    # 보관 개수 보다 많은 항목은 자동 삭제.
    removeOldEpsoide(q["plexlib_season_root"], q["store_count"])
    
    return True
    
def distByRepac(q, d, t):
    logger.info("dist - Just repackaging {}".format(t))
    ##TODO: 환경설정 값으로 바꾸어야 한다.
    tm_d_path = "/storage/local/mforce2-local/transmission-daemon/downloads"
    source = os.path.join(tm_d_path, d["tvshow_file"])
    
    # 소스파일이 존재 하지 않는다면, error logging 후 return.
    if not os.path.isfile(source):
        logger.error("Source file is not exist: {}".format(source))
        return False
    
    cstr = "/home/jin/bin/ktvshowhdenc --no-interact --rm-source --over-write"
    cstr = cstr + " --out-path \"" + q["plexlib_season_root"] + "/\""
    cstr = cstr + " --out-name \"" + t + "\""
    cstr = cstr + " --ff-vcp true "
    cstr = cstr + " --ff-acp true "
    cstr = cstr + " \"" + source + "\""
    logger.info("Command: {}".format(cstr))
    ##TODO: 실행 출력을 어딘가 저장 하도록 한다.
    os.system(cstr)
    logger.info("Complete repackaging to plex lib: {}".format(os.path.join(q["plexlib_season_root"], t)))
    
    # download 경로의 .size 파일 제거.
    if os.path.isfile(source + ".size"):
        os.remove(source + ".size")
        
    # 보관 개수 보다 많은 항목은 자동 삭제.
    removeOldEpsoide(q["plexlib_season_root"], q["store_count"])
    
    return True
    
def distByTrans(q, d, t):
    logger.info("dist - with transcoding {}, v:{}, a:{}.".format(t, d["force_video_encoding"], d["force_audio_encoding"]))
    # 환경설정 값으로 바꾸어야 한다.
    tm_d_path = "/storage/local/mforce2-local/transmission-daemon/downloads"
    source = os.path.join(tm_d_path, d["tvshow_file"])
    target = os.path.join(q["plexlib_season_root"], t)
    
    # 소스파일이 존재 하지 않는다면, error logging 후 return.
    if not os.path.isfile(source):
        logger.error("Source file is not exist: {}".format(source))
        return False
    
    cstr = "/home/jin/bin/ktvshowhdenc --no-interact --rm-source --over-write"
    cstr = cstr + " --out-path \"" + q["plexlib_season_root"] + "/\""
    cstr = cstr + " --out-name \"" + t + "\""
    if not d["force_video_encoding"]:
        cstr = cstr + " --ff-vcp true "
    if not d["force_audio_encoding"]:
        cstr = cstr + " --ff-acp true "
    cstr = cstr + " \"" + source + "\""
    logger.info("Command: {}".format(cstr))
    ##TODO: 실행 출력을 어딘가 저장 하도록 한다.
    os.system(cstr)
    logger.info("Complete transcoding to plex lib: {}".format(os.path.join(q["plexlib_season_root"], t)))
    
    # download 경로의 .size 파일 제거.
    if os.path.isfile(source + ".size"):
        os.remove(source + ".size")
        
    # 보관 개수 보다 많은 항목은 자동 삭제.
    removeOldEpsoide(q["plexlib_season_root"], q["store_count"])
    
    return True
    
def dist(queue_name):
    qf = open(queue_name, 'r')
    queue = json.loads(qf.read())
    qf.close()
    
    ep_dic = queue["ep_dic"]
    series_name = queue["series_name"]
    season_number = queue["season_number"]
    release_year = queue["release_year"]
    epsode_id_type = queue["epsode_id_type"]
    plexlib_season_root = queue["plexlib_season_root"]
    epid_list = []
    for epid in ep_dic.keys():
        dist_result = False
        download_content = ep_dic[epid]
        if download_content["download_complete"]:
            # 저장할 경로가 생성되지 않았다면, 경로를 생성
            if not os.path.isdir(plexlib_season_root):
                logger.info("Make new season root path: {}".format(plexlib_season_root))
                try:
                    os.makedirs(plexlib_season_root)
                except OSError as exc:  # Python >2.5
                    logger.error("Fail to mkdirs : {}".foramt(exc))
                    raise
                except NameError as ne:
                    traceback.print_exc()
                    logger.error("NameError. Fail to mkdirs : {}".foramt(ne))
                    raise
                except AttributeError as ae:
                    traceback.print_exc()
                    logger.error("Attribute Error. Fail to mkdirs : {}".foramt(ae))
                    raise
                    
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
                    dist_result = distByMv(queue, download_content, lib_target_name)
                        
                else:
                    if ext == ".mkv":
                        dist_result = distByRepac(queue, download_content, lib_target_name)
                            
                    else:
                        dist_result = distByTrans(queue, download_content, lib_target_name)
                            
            else:
                dist_result = distByTrans(queue, download_content, lib_target_name)
                    
            # 처리 이력을 저장.
            current_string = datetime.now().strftime("%Y%m%d_%H%M%S.%f")
            contentStr = json.dumps(download_content, indent=4, sort_keys=False, ensure_ascii=False)
            rqfName = os.path.join(rspath, CONST.history_path_name, "fail", current_string + '.result.json')
            if dist_result:
                rqfName = os.path.join(rspath, CONST.history_path_name, "success", current_string + '.result.json')
            rf = open(rqfName, 'w')
            rf.write(contentStr)
            rf.close()
            
            epid_list.append(epid)
        
    # 처리 완료된 것들을 queue에서 항목 제거
    for epid in epid_list:
        del ep_dic[epid]
    
    # 처리 완료된 항목이 제거된 queue를 다시 저장.
    if len(epid_list) > 0:
        queueStr = json.dumps(queue, indent=4, sort_keys=False, ensure_ascii=False)
        qf = open(queue_name, 'w')
        qf.write(queueStr)
        qf.close()
    
    # 보관 개수 보다 많은 항목은 자동 삭제.
    removeOldEpsoide(queue["plexlib_season_root"], queue["store_count"])
    
def dist2plexlib():
    ## queue/*.queue.json 파일들을 읽어 들인다.
    for queue_name in glob.glob(os.path.join(rspath, CONST.queue_path_name) + '/*.queue.json'):
        logger.debug("Queue file: {}".format(queue_name))
        dist(queue_name)
    
    logger.info("All task complete.")
    
def main():
    checkrspath()
    startLogging()
    # lock 여부 확인 및 locking 
    acquireLock()
    try:
        downloadQueuesUpdate()
        dist2plexlib()
    except OSError as err:
        logger.error("OS error: {0}".format(err))
    except ValueError:
        logger.error("Could not convert data to an integer.")
    except:
        logger.error("Unexpected error: {}".format(sys.exc_info()[0]))
        
    # unlocking
    unLock()
    logger.info("Unlock compete.")
    logger.info("===============================================")
    logger.info("-----------------------------------------------")

if __name__ == "__main__":
    main()
