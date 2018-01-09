#!/bin/bash

usage() { echo  "Usage: $0 [-f <yaml-config-file>] [-l <git-link> -s <script-name>] [-d]
                    -f      path to the configuration file, default 'images.yaml'
                    -l      git link from where to download and create the tar file
                    -s      script name to be executed while creating the image. Manadatory when '-l' is passed
                    -d      execute in dry run and in debug mode
                " 1>&2; exit 1; }

while getopts ":f:l:s:d" o; do
    case "${o}" in
        f)
            CONFIG_FILE=${OPTARG}
            [ -e $CONFIG_FILE ] || echo "File $CONFIG_FILE not found" 1>&2; exit 2
            ;;
        l)
            LINK=${OPTARG}
	    git ls-remote "${LINK}" &>-
            if [ "$?" -ne 0 ]; then
              echo "Unable to read from ${LINK}" 1>&2
              exit 3;
            fi
            ;;
        s)
            SCRIPT=${OPTARG}
	    ;;
        d)
            DRY=true
            ;;
        *)
            usage
            ;;
    esac
done
shift $((OPTIND-1))

if [ -z "${CONFIG_FILE}" ] ;then
    CONFIG_FILE=image.yaml
    if [ ! -e $CONFIG_FILE ] ; then
     echo "File $CONFIG_FILE not found, run the install.sh first or provide a config file" 1>&2; usage
    fi
fi

if [ -z "${LINK}" ] ;then
    # TODO update with right repo
    # LINK=https://github.com/RuthDevlaeminck/OAI_VNF.git
    # SCRIPT=oai_image_create.sh
    sudo wget https://github.com/corenetdynamics/image-generator/raw/master/files.tar -O /etc/image-generator/files.tar
elif [ ! -z ${LINK} ] && [ -z ${SCRIPT} ]; then
    echo "Link is provided but no script to execute, please provide also script name" 1>&2; usage
else
    git clone ${LINK} _scripts

    pushd _scripts
    tar -cvf ../files.tar *
    popd

    sudo mv files.tar /etc/image-generator/files.tar
    sed -i "s/oai_image_create.sh/$SCRIPT/g" ${CONFIG_FILE}

    rm -rf _scripts
fi


if [ "${DRY}" = true  ] ; then 
	sudo image-generator -f image.yaml --debug -dry
else
	sudo image-generator -f image.yaml # --debug -dry
fi
