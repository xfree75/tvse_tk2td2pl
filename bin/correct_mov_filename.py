#!/usr/bin/env python3

import glob
import ntpath
import os

def getCorrectName(fname):
    retDic = {}
    
    bfname = ntpath.basename(fname)
    # print(bfname)
    bpath = os.path.dirname(os.path.abspath(fname))
    # print(bpath)
    
    #TODO: retDic에 경로, 원본파일이름, 올바른파일이름을 저장 한다.

    return retDic
    

def getm4vList(path_str):
    returnList = []
    for fname in glob.iglob(path_str + '/**/*.m4v', recursive=True):
        returnList.append(fname)
    
    return returnList


def getAllm4vList():
    plex_recent_path = "/home/jin/plex-recent/"
    plex_path = "/home/jin/plex/"

    plexRecentList = getm4vList(plex_recent_path)
    plexList = getm4vList(plex_path)

    allList = plexRecentList + plexList
    allList.sort()
    # print("\n".join(allList))

    corrDicList = []
    for fname in allList:
        corrDicList.append(getCorrectName(fname))


def main():
    getAllm4vList()

if __name__ == "__main__":
    main()


