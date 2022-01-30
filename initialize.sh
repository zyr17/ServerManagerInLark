#!/bin/sh

# touch environment settings
touch codes/.env
mkdir codes/ENV
touch codes/ENV/available_servers codes/ENV/available_accounts

# set redis folder as 777 to allow redis container to save data
chmod 777 redis

echo initialize over. please read the README and fill environment settings in 
echo env files. "(codes/.env; codes/ENV/*)"
