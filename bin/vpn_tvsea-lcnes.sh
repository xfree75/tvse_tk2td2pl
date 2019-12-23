#!/usr/bin/env bash

set -x

sudo systemctl stop plexpy.service

sudo ipsec up vpn-tor2 \
    && sleep 10 \
    && tvsea-lcnes.py \
    && sleep 80 \
    
sudo ipsec down vpn-tor2
sleep 20
sudo systemctl restart plexmediaserver.service
sleep 20
sudo systemctl start plexpy.service

