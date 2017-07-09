#!/bin/bash
set -x

NMON_HOME=/home/jin/nmon

#이미 실행 되었는지 확인
pscnt=`ps -ef | grep " nmon -f" | grep -v "grep" | wc -l`

if [[ ${pscnt} -gt 0 ]]; then
    exit -1
fi


_DAY_SEC=86400
_INTERVAL=60

cstamp1=$(date +"%s")
echo $cstamp1

# get current timezone's day start stamp.
# 현재 지역, 오늘 00:00분의 timestamp
cstamp2=$(date --date="$TIME" +"%s")
echo $cstamp2

# 오늘밤 현재 지역의 23:59:59초의 timestamp
cstamp3=`expr $cstamp2 + $_DAY_SEC - 8`
echo $cstamp3

# 오늘 남은 초.
extstamp=`expr $cstamp3 - $cstamp1`
echo $extstamp

checkcnt=`expr $extstamp / ${_INTERVAL}`

cmdstr="nmon -f -s ${_INTERVAL} -c ${checkcnt}"S

cd $NMON_HOME
$cmdstr
echo $cmdstr
cd -

# 오래된 mmon 파일 삭제.
find /home/jin/nmon -name "*.nmon" -type f -ctime +30 -exec rm -rf {} ';'

exit 0

