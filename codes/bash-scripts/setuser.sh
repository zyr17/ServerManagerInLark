#!/bin/bash

user=USER
id=ID

if [[ -n `cat /etc/passwd | grep ^$user` ]]; then
    echo user exists.
    exit 1
elif [[ -n `cat /etc/passwd | grep :$id:$id:` ]]; then
    echo id exists.
    exit 1
else
    echo user and id not exist. create it. 
    # create new user
    useradd -s /bin/bash -d /home/$user -m $user
fi

if [[ ! -e /home/$user/data ]]; then
    ln -s /data/$user /home/$user/data
fi

if [[ ! -e /home/$user/nas ]]; then
    ln -s /nas/user/$user /home/$user/nas
fi

nowid=`cat /etc/passwd | grep ^$user | awk -F : '{print $3}'`
if [[ $nowid -ne $id ]]; then
    echo user id not right! $nowid
    usermod -u $id $user
    groupmod -g $id $user
fi

folders=(/nas/user /data)
for folder in ${folders[*]}; do
    folder=$folder/$user
    if [[ ! -e $folder ]]; then
        echo $folder not exist, create
        # create folder and change owner
        mkdir $folder
    else
        echo $folder exists
    fi
    chown $user:$user $folder
done
if [[ ! -e /nas/user/$user/data ]]; then
    ln -s /data/$user /nas/user/$user/data
fi
