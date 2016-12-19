#!/bin/bash
#set -x

#ffmpeg_tmp=~/ffmpeg/tmp
ffmpeg_tmp=/tmp/ffmpeg
max_bit_rate=2048

# check arguments
for targ in "$@"
do
	if  [[ ${targ} == --* ]];
	then
		echo "Option: ${targ}"
	else
		echo "Value: ${targ}"
	fi

done

#exit 0

filename=`basename "$1"`
#filename2=`echo ${filename} | sed -e "s/ /\\\\\ /g" | sed -e "s/(/\\\\\(/g" | sed -e "s/)/\\\\\)/g"`
abspath=`readlink -f "$1"`
#abspath2=`echo ${abspath} | sed -e "s/ /\\\\\ /g" | sed -e "s/(/\\\\\(/g" | sed -e "s/)/\\\\\)/g"`
sourcepath=`dirname "${abspath}"`
#sourcepath2=`echo ${sourcepath} | sed -e "s/ /\\\\\ /g" | sed -e "s/(/\\\\\(/g" | sed -e "s/)/\\\\\)/g"`


if [ -f "${abspath}" ]
then
	echo "${abspath} found."
else
	echo "${abspath} not found."
	exit -1
fi

if [ ! -d "${ffmpeg_tmp}" ]
then
	mkdir -p ${ffmpeg_tmp}
fi

ext=`echo ${filename##*.}`
name=`echo ${filename%.*}`
#name2=`echo ${name} | sed -e "s/ /\\\\\ /g" | sed -e "s/(/\\\\\(/g" | sed -e "s/)/\\\\\)/g"`

# get source video bit_rate
vbit_rate_str=`mediainfo --Output=XML "${abspath}" | xmllint --xpath "/Mediainfo/File/track[@type='Video']/Bit_rate/text()" -`
#echo "video Bit_rate value string: ${vbit_rate_str}"
vbit_rate_value=`echo ${vbit_rate_str} | sed -e "s/Kbps//g" | sed -e "s/\ //g"`
#echo "video bit rate value(k): ${vbit_rate_value}"

if [ ${vbit_rate_value} -gt ${max_bit_rate} ]
then
	vbit_rate_value=${max_bit_rate}
fi

ffmpeg_tmp_dev_num=`stat -c "%d" "${ffmpeg_tmp}"`
source_path_dev_num=`stat -c "%d" "${sourcepath}"`

command0="cp \"${abspath}\" \"${ffmpeg_tmp}\""

#command1="ffmpeg -y -i \"${ffmpeg_tmp}/${filename}\" -acodec aac -ab 192k -ar 48000 -ac 2 -b:a 300k -vcodec libx264 -preset fast -level 30 -b:v ${vbit_rate_value}k -r 29.97 -s 1280:720 -threads 0 -strict -2 \"${ffmpeg_tmp}/${name}.m4v\""
#command1="ffmpeg -y -i \"${ffmpeg_tmp}/${filename}\" -acodec aac -ab 192k -ar 48000 -ac 2 -b:a 300k -vcodec libx264 -preset veryfast -level 30 -crf 27 -r 23.976 -s 1280:720 -threads 0 -strict -2 \"${ffmpeg_tmp}/${name}.m4v\""
command1="ffmpeg -y -i \"${ffmpeg_tmp}/${filename}\" -acodec aac -ab 192k -ar 48000 -ac 2 -b:a 300k -vcodec libx264 -preset veryfast -level 3.0 -crf 23 -r 23.976 -s 1280:720 -threads 0 -strict -2 \"${ffmpeg_tmp}/${name}.m4v\""

if [ ${ffmpeg_tmp_dev_num} -eq ${source_path_dev_num} ]
then 
	command2="mv \"${ffmpeg_tmp}/${name}.m4v\" \"${sourcepath}\""
	echo "It is going to move to sourcepath by exec mv commnad."
else
	command2="cp \"${ffmpeg_tmp}/${name}.m4v\" \"${sourcepath}\" && rm -rf \"${ffmpeg_tmp}/${name}.m4v\""
	echo "It is going to move to sourcepath by exec cp && rm commnad."
fi

# remove copyed original file
command3="rm -f \"${ffmpeg_tmp}/${filename}\""

echo -e "================================================================================"
echo -e "command0: ${command0}\n"
echo -e "================================================================================"
echo -e "command1: ${command1}\n"
echo -e "================================================================================"
echo -e "command2: ${command2}\n"
echo -e "================================================================================"
echo -e "command3: ${command3}\n"
echo -e "================================================================================"

eval ${command0} && eval ${command1} && eval ${command2} && eval ${command3}

exit 0

