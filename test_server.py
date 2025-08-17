# Create a test file called test_server.py to isolate the issue
# This will help us determine if the problem is with the model, websocket, or other components

from fastapi import FastAPI, WebSocket
from fastapi.middleware.cors import CORSMiddleware
import json
import asyncio

app = FastAPI()

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
async def root():
    return {"message": "Test server running"}

@app.websocket("/ws/{user_id}")
async def websocket_endpoint(websocket: WebSocket, user_id: str):
    await websocket.accept()
    print(f"[INFO] WebSocket connected for user: {user_id}")
    
    try:
        while True:
            # Receive message
            data = await websocket.receive_json()
            message = data.get("message", "")
            persona = data.get("persona", "kai")
            
            print(f"[DEBUG] Received: {message}")
            
            # Send typing indicator
            typing_response = {
                "type": "typing",
                "content": f"{persona.capitalize()} is typing...",
                "persona": persona
            }
            await websocket.send_text(json.dumps(typing_response))
            
            # Simulate processing delay
            await asyncio.sleep(2)
            
            # Send simple response
            response = {
                "type": "message",
                "content": f"Echo from {persona}: {message}",
                "emotions": {},
                "persona": persona
            }
            await websocket.send_text(json.dumps(response))
            print(f"[DEBUG] Sent response")
            
    except Exception as e:
        print(f"[ERROR] WebSocket error: {e}")
        await websocket.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)