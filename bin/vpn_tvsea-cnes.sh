#!/usr/bin/env bash

set -x

sudo systemctl stop plexpy.service

sudo ipsec up vpn-nw \
    && sleep 10 \
    && tvsea-cnes_max.py \
    && tvsea-cnes_view.py \
    && sleep 80 \
    
sudo ipsec down vpn-vpn-nw
sleep 8
sudo systemctl restart plexmediaserver.service
sleep 8
sudo systemctl restart dnsmasq.service
sleep 8
sudo systemctl start plexpy.service



