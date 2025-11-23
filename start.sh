#!/bin/bash
source venv/bin/activate
uvicorn main:app --host 0.0.0.0 --port 8000 --reload > logs/server.log 2>&1 &
echo $! > server.pid
