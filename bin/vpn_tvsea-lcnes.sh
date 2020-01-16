#!/usr/bin/env bash

set -x

sudo systemctl stop plexpy.service

sudo ipsec up vpn-hk \
    && sleep 10 \
    && tvsea-lcnes.py \
    && sleep 80 \
    
sudo ipsec down vpn-hk
sleep 8
sudo systemctl restart plexmediaserver.service
sleep 8
sudo systemctl restart dnsmasq.service
sleep 8
sudo systemctl start plexpy.service



