#!/bin/bash
#set -x

#이미 실행 되었는지 확인
ps -ef | grep " nmon -f" | grep -v "grep" | wc -l

_DAY_SEC=86400
_INTERVAL=60

cstamp1=$(date +"%s")
echo $cstamp1

# get current timezone's day start stamp.
# 현재 지역, 오늘 00:00분의 timestamp
cstamp2=$(date --date="$TIME" +"%s")
echo $cstamp2

# 오늘밤 현재 지역의 23:59:59초의 timestamp
cstamp3=`expr $cstamp2 + $_DAY_SEC - 1`
echo $cstamp3

# 오늘 남은 초.
extstamp=`expr $cstamp3 - $cstamp1`
echo $extstamp

checkcnt=`expr $extstamp / ${_INTERVAL}`

cmdstr="nmon -f -s ${_INTERVAL} -c ${checkcnt}"
echo $cmdstr

