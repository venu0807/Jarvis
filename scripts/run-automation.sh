#!/bin/bash
AUTOMATION=$1
cd /home/venu/Proposals/Jarvis
docker compose up -d "$AUTOMATION"