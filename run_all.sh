#!/bin/bash
cd /workspace/shared/noc-copilot

echo "==> Stopping old app processes (vLLM on :8000 untouched)..."
pkill -9 -f "router_api"  2>/dev/null
pkill -9 -f "itsm_api"    2>/dev/null
pkill -9 -f "itsm_board"  2>/dev/null
pkill -9 -f "app.py"      2>/dev/null
fuser -k -9 8001/tcp 8002/tcp 8080/tcp 7860/tcp 2>/dev/null
sleep 4

echo "==> Starting background services..."
uvicorn mocks.router_api:app --host 0.0.0.0 --port 8001 > /tmp/router.log 2>&1 &
uvicorn mocks.itsm_api:app   --host 0.0.0.0 --port 8002 > /tmp/itsm.log   2>&1 &
python itsm_board.py > /tmp/board.log 2>&1 &
sleep 4

echo "==> Health checks:"
curl -s http://localhost:8001/docs  >/dev/null && echo "   router :8001  OK" || echo "   router :8001  FAIL"
curl -s http://localhost:8002/health && echo "   <- itsm :8002 OK" || echo "   itsm :8002 FAIL"
curl -s http://localhost:8080/       >/dev/null && echo "   board  :8080  OK" || echo "   board  :8080  FAIL"

echo ""
echo "==> ITSM board: https://notebooks.amd.com/jupyter-hack-team-3049-260614162200-ee4e0c4e/proxy/8080/"
echo ""
echo "==> Starting dashboard..."
python app.py
