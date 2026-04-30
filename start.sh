#!/bin/bash
cd /home/juan/mi_web
pkill -f "app.py" 2>/dev/null
sleep 1
nohup /home/juan/mi_web/venv/bin/python app.py > /tmp/mi_web.log 2>&1 &
disown
sleep 2
ss -tlnp | grep 5001 && echo "✓ App corriendo en puerto 5001" || echo "✗ Error al iniciar"
