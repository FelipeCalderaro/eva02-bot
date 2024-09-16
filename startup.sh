#!/bin/bash

cd /app

touch discord.log
python3 main.py &
tail -f discord.log
