#!/bin/bash

# Run both mock APIs in the background
uvicorn mocks.router_api:app --host 0.0.0.0 --port 8000 --reload &
ROUTER_PID=$!

uvicorn mocks.itsm_api:app --host 0.0.0.0 --port 8001 --reload &
ITSMS_PID=$!

echo "Mock APIs started:"
echo "Router API: http://localhost:8000"
echo "ITSM API: http://localhost:8001"

# Wait for processes to complete
wait $ROUTER_PID $ITSMS_PID