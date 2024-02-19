#!/bin/sh
docker stop eva02; docker rm eva02; docker rmi eva02; docker build --tag=eva02 .; docker compose up -d 