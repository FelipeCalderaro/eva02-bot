#!/bin/bash

cd /eva
python3 main.py &
tail -f discord.log
