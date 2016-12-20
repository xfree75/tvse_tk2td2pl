#!/bin/bash
#set -x


tmpbase=/tmp
ff_tune=film
ff_preset=medium
ff_crf=20
ff_threads=0
ff_vwscale=1280
vwscale_set=false


##
 # my read link function.
 ##
function mreadlink(){
    dirname=`perl -e 'use Cwd "abs_path";print abs_path(shift)' "$1"`
    echo ${dirname}
}

##
 #
 ##
function printhelp(){
	echo "사용법: ${0} [--options] file"
	echo "여기서 options는 다음과 같습니다."
	echo "    --help                이 도움말을 표시 합니다."
	echo "    --no-interact         작업을 진행할지 물어 보지 않습니다."
	echo "    --rm-source           작업이 완료 되면 원본 비디오 파일을 제거 합니다."
	echo "    --over-write          생성할 파일이 이미 존재하여도 덮어 씁니다."
	echo "    --tmp-path <path>     변환 작업을 위한 임시 경로 입니다."
	echo "                          기본 경로는 ${tmpbase} 입니다."
	echo "                          작업 경로는 원본 파일 크기 + 변환될 파일 크기 만큼 필요 합니다."
	echo "                          작업이 완료되면 작업 파일은 삭제 됩니다. (오류 발생시 남게 됨)."
	echo "    --out-path <path>     인코딩 된 파일을 저장할 경로입니다."
	echo "    --out-name <name>     인코딩 된 파일을 저장할 이름입니다."
	echo "    --ff-tune <value>     ffmpeg 실행 시 tune option으로 전달 됩니다."
	echo "                          기본 값은 ${ff_tune} 입니다. 자세한 옵션은 ffmpeg 도움말을 참고하십시오."
	echo "    --ff-preset <value>   ffmpeg 실행 시 preset option으로 전달 됩니다."
	echo "                          기본 값은 ${ff_preset} 입니다. 자세한 옵션은 ffmpeg 도움말을 참고하십시오."
	echo "    --ff-crf <number>     ffmpeg 실행 시 crf option으로 전달 됩니다."
	echo "                          기본 값은 ${ff_crf} 입니다. 자세한 옵션은 ffmpeg 도움말을 참고하십시오."
	echo "    --ff-threads <number> ffmpeg 실행 시 threads option으로 전달 됩니다."
	echo "                          기본 값은 ${ff_threads} 입니다. 자세한 옵션은 ffmpeg 도움말을 참고하십시오."
	echo "    --ff-vwscale <number> ffmpeg 실행 시 vf scale option의 넓이 값(-vf scale=1280:1)으로 전달 됩니다."
	echo "                          기본 값은 ${ff_vwscale} 입며 원본 영상의 넓이가 더 작은 경우 자동으로 조정 됩니다."
	echo "                          이 옵션을 사용하지 않을 경우 mediainfo가 설치 되어 있어야 합니다."
	echo "                          macOS에서는 'brew install mediainfo' 명령어로 설치 할 수 있습니다."
	echo "                          Debian 계열 배포판에서는 'sudo apt install mediainfo' 명령어로 설치 할 수 있습니다."
	echo "   "
	exit 0
}

##
 # time format?
 ##
function show_time(){
    num=$1
    min=0
    hour=0
    day=0
    if((num>59));then
        ((sec=num%60))
        ((num=num/60))
        if((num>59));then
            ((min=num%60))
            ((num=num/60))
            if((num>23));then
                ((hour=num%24))
                ((day=num/24))
            else
                ((hour=num))
            fi
        else
            ((min=num))
        fi
    else
        ((sec=num))
    fi
    echo "$day"d "$hour"h "$min"m "$sec"s
}


# check arguments
ovf=false
co=
no_interact=false
rm_source=false
over_write=false
arg_outpath=
arg_outname=

if [[ "$#" == 0 ]]; then
	printhelp
fi

for targ in "$@"
do
	if  [[ ${targ} == --* ]];
	then
		#echo "Option: ${targ}"
		if [ "${targ}" == "--help" ]; then
			rm_source=true
			ovf=false
			co=
			printhelp
		fi
		if [ "${targ}" == "--no-interact" ]; then
			no_interact=true
			ovf=false
			co=
		fi
		if [ "${targ}" == "--rm-source" ]; then
			rm_source=true
			ovf=false
			co=
		fi
		if [ "${targ}" == "--over-write" ]; then
			over_write=true
			ovf=false
			co=
		fi
		if [ "${targ}" == "--tmp-path" ]; then
			ovf=true
			co="--tmp-path"
		fi
		if [ "${targ}" == "--out-path" ]; then
			ovf=true
			co="--out-path"
		fi
		if [ "${targ}" == "--out-name" ]; then
			ovf=true
			co="--out-name"
		fi
		if [ "${targ}" == "--ff-tune" ]; then
			ovf=true
			co="--ff-tune"
		fi
		if [ "${targ}" == "--ff-preset" ]; then
			ovf=true
			co="--ff-preset"
		fi
		if [ "${targ}" == "--ff-crf" ]; then
			ovf=true
			co="--ff-crf"
		fi
		if [ "${targ}" == "--ff-threads" ]; then
			ovf=true
			co="--ff-threads"
		fi
		if [ "${targ}" == "--ff-vwscale" ]; then
			ovf=true
			co="--ff-vwscale"
			vwscale_set=true
		fi

	else
		#echo "Value: ${targ}"
		if [ "${ovf}" = true ]; then
			if [ "${co}" == "--tmp-path" ]; then
				tmpbase=${targ}
				ovf=false
				co=
			fi
			if [ "${co}" == "--out-path" ]; then
				arg_outpath=${targ}
				ovf=false
				co=
			fi
			if [ "${co}" == "--out-name" ]; then
				arg_outname=${targ}
				ovf=false
				co=
			fi
			if [ "${co}" == "--ff-tune" ]; then
				ff_tune=${targ}
				ovf=false
				co=
			fi
			if [ "${co}" == "--ff-preset" ]; then
				ff_preset=${targ}
				ovf=false
				co=
			fi
			if [ "${co}" == "--ff-crf" ]; then
				ff_crf=${targ}
				ovf=false
				co=
			fi
			if [ "${co}" == "--ff-threads" ]; then
				ff_threads=${targ}
				ovf=false
				co=
			fi
			if [ "${co}" == "--ff-vwscale" ]; then
				ff_vwscale=${targ}
				ovf=false
				co=
			fi
		else
			argsource=${targ}
		fi
	fi

done

# 생성된지 3일 이상 된 작업경로를 제거 한다.
find ${tmpbase} -type d -name "ffmpegtmp*" -ctime +3 -exec rm -rf {} ';'

# 작업 경로.
tmp_time=`date "+%Y%m%d_%H%M.%s"`
ffmpeg_tmp=${tmpbase}/ffmpegtmp.${tmp_time}.${RANDOM}



filename=`basename "${argsource}"`
#filename2=`echo ${filename} | sed -e "s/ /\\\\\ /g" | sed -e "s/(/\\\\\(/g" | sed -e "s/)/\\\\\)/g"`
#abspath=`readlink -f "$1"`
abspath=$(mreadlink "${argsource}")
sourcepath=`dirname "${abspath}"`

if [ -f "${abspath}" ]
then
	echo "Source video file [${abspath}] found."
else
	echo "Source vodeo file [${abspath}] not found."
	exit -1
fi

if [ ! -d "${ffmpeg_tmp}" ]
then
	mkdir -p ${ffmpeg_tmp}
fi

ext=`echo ${filename##*.}`
name=`echo ${filename%.*}`

# 출력 경로 및 이름 인지가 있다면 지정 한다.
targetpath=${sourcepath}
targetname=${name}.m4v
if [ ! -z "${arg_outpath}" ]; then
	targetpath=$(mreadlink "${arg_outpath}")
fi
if [ ! -z "${arg_outname}" ]; then
	targetname=${arg_outname}
fi


if [ "${over_write}" == false ]; then
	if [ -f "${targetpath}/${targetname}" ]; then
		echo -e "Target video file [${targetpath}/${targetname}] already exist.\n     You can use this option: [--over-write]."
		exit -1
	fi
fi
echo "Target video file: [${targetpath}/${targetname}]."

# get source video bit_rate
#vbit_rate_str=`mediainfo --Output=XML "${abspath}" | xmllint --xpath "/Mediainfo/File/track[@type='Video']/Bit_rate/text()" -`
#echo "video Bit_rate value string: ${vbit_rate_str}"
#vbit_rate_value=`echo ${vbit_rate_str} | sed -e "s/Kbps//g" | sed -e "s/\ //g"`
#echo "video bit rate value(k): ${vbit_rate_value}"

# get source video scale(width)
if [ "${vwscale_set}" == false ]; then
	# mediainfo 가 설치 되어 있는지 확인.
	absmediainfo=$(which mediainfo)
	absmediainfo=$(mreadlink "${absmediainfo}")
	if [ "${absmediainfo}" == "" ]; then
		echo "Can't found mediainfo. Please insatall mediainfo. See help(--help)."
		exit -1
	else
		if [ ! -x "${absmediainfo}" ]; then
			echo "Fatal ERROR: Can't execute mediainfo."
			exit -1
		fi
	fi
	vwscale_str=`mediainfo --Output=XML "${abspath}" | xmllint --xpath "/Mediainfo/File/track[@type='Video']/Width/text()" -`
	vwscale_value=`echo ${vwscale_str} | sed -e "s/pixels//g" | sed -e "s/\ //g"`
	echo "vwscale_value: ${vwscale_value}"
	if [[ ${vwscale_value} -lt ${ff_vwscale} ]]; then
		ff_vwscale=${vwscale_value}
	fi

fi

command0="cp \
	    \"${abspath}\" \
	    \"${ffmpeg_tmp}/\""


command1="ffmpeg \
	   -y \
	   -i \"${ffmpeg_tmp}/${filename}\" \
	   -acodec ac3 -ar 48000 -ab 384 -ac 6 \
	   -vcodec libx264 \
	   -preset ${ff_preset} \
	   -level 3.0 \
	   -crf ${ff_crf} \
	   -tune ${ff_tune} \
	   -r 23.976 \
	   -vf scale=${ff_vwscale}:-1 \
	   -threads ${ff_threads} \
	   -strict -2 \
	   \"${ffmpeg_tmp}/___tmp.m4v\""


command2="cp \
	    \"${ffmpeg_tmp}/___tmp.m4v\" \
	    \"${targetpath}/${targetname}\" \
	    && rm -rf \
	    \"${ffmpeg_tmp}/___tmp.m4v\" \
	    && rm -rf \
	    \"${ffmpeg_tmp}"


# remove copyed original file
command3="rm -f \
	    \"${ffmpeg_tmp}/${filename}\""

echo -e "================================================================================"
echo -e "Command-0: ${command0}" | tr '\t' '\n' 
echo -e "================================================================================"
echo -e "Command-1: ${command1}" | tr '\t' '\n'
echo -e "================================================================================"
echo -e "Command-2: ${command2}" | tr '\t' '\n' 
echo -e "================================================================================"
echo -e "Command-3: ${command3}" | tr '\t' '\n' 
echo -e "================================================================================"
if [ "${rm_source}" == true ]; then
	command4="rm -f \"${abspath}\""
	echo -e "Command-4: ${command4}" | tr '\t' '\n' 
	echo -e "================================================================================"
fi

if [ "${no_interact}" == false ]; then
	read -n 1 -p "Continue? [y/n]: "
	if [[ ! ${REPLY} == [yY] ]]; then
		echo -e "\n"
		exit 0
	fi
fi


# 실행 시작 시간 기록
start_stamp=`date "+%s"`

if [ "${rm_source}" == true ]; then
	eval ${command0} && eval ${command1} && eval ${command2} && eval ${command3} && eval ${command4}
else
	eval ${command0} && eval ${command1} && eval ${command2} && eval ${command3}
fi

# 실행 종료 시간 기록 및 출력
finish_stamp=`date "+%s"`
r=`expr ${finish_stamp} - ${start_stamp}`
echo "Completed! ${r} seconds ($(show_time ${r}))"

exit 0

