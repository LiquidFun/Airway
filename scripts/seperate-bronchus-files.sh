#!/bin/bash

copyImages () {

    #getting path to Bronchus-images
    image_path=`grep -m 1 "$1" $data_file | cut -d ":" -f 3 | sed 's#\\#/#g' | tr -d [:blank:] | tr -d [:cntrl:] | head -n 1`
    image_path="/$image_path"

    #getting patients id from image path
    pat_id=`echo $image_path | cut -d '/' -f 3`

    #create dirs
    src="$path_source$pat_dir$image_path/*"
    dest="$path_dest$pat_id/$2"

    if [ ! -d $dest ]
    then
        mkdir -p $dest
    fi

    #copying
    echo "copying $1 related files from Patient $pat_id"
    cp -r $src $dest
}


path_source='/share/SBI-Projekt/raw_data/'
path_dest='/share/SBI-Projekt/working_dir/'

export IFS=$'\n'

declare -a patterns=(   "Bronchus"
                        "Right upper lobe"
                        "Right middle lobe"
                        "Right lower lobe"
                        "Left upper lobe"
                        "Left lower lobe"                      
                        )

for pat_dir in `ls -1 $path_source`
do
    data_file="$path_source$pat_dir/Data.txt"

    all_images_existing="yes"

    if [ -e $data_file ]
    then

        for pattern in "${patterns[@]}"
        do
            
            grep "$pattern" $data_file > /dev/null
            if [ $? -ne 0 ]
            then
                all_images_existing="no"
                echo "WARNING path $pat_dir has no $pattern related images"
            fi

        done
       
        if [ $all_images_existing = "yes" ]
        then
            copyImages "Bronchus"           "Bronchus"
            copyImages "Right upper lobe"   "RightUpperLobe"
            copyImages "Right middle lobe"  "RightMiddleLobe"
            copyImages "Right lower lobe"   "RightLowerLobe"
            copyImages "Left upper lobe"    "LeftUpperLobe"
            copyImages "Left lower lobe"    "LeftLowerLobe"
        fi

    fi
done

