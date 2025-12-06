# server.py
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
import os
from strands.experimental.bidi import BidiAgent
from strands.experimental.bidi.models import BidiNovaSonicModel
from strands.experimental.bidi.tools import stop_conversation
# events references
# from strands.experimental.bidi.types.events import BidiAudioInputEvent, BidiTextInputEvent

model_id = os.getenv("MODEL_ID", "amazon.nova-2-sonic-v1:0")
region = os.getenv("REGION_NAME", "ap-northeast-1")

INPUT_SAMPLE_RATE = int(os.getenv("INPUT_SAMPLE_RATE", "16000"))
OUTPUT_SAMPLE_RATE = int(os.getenv("OUTPUT_SAMPLE_RATE", "16000"))
CHANNELS = int(os.getenv("CHANNELS", "1"))
FORMAT = "pcm"

sonic_model = BidiNovaSonicModel(
    model_id=model_id,
    provider_config={
        # https://strandsagents.com/latest/documentation/docs/api-reference/experimental/bidi/types/#strands.experimental.bidi.types.model.AudioConfig
        "audio": {
            "voice": "tiffany",
            "input_rate": INPUT_SAMPLE_RATE,
            "output_rate": OUTPUT_SAMPLE_RATE,
            "channels": CHANNELS,
            "format": FORMAT
        },
        # https://docs.aws.amazon.com/nova/latest/userguide/input-events.html
        "inference": {}
    },
    client_config={
        "region": region
    },
)


app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.websocket("/ws")
async def voice_chat(websocket: WebSocket) -> None:
    voice_agent = BidiAgent(model=sonic_model, tools=[stop_conversation])

    try:
        await websocket.accept()
        await voice_agent.run(inputs=[websocket.receive_json], outputs=[websocket.send_json])

    except Exception as e:
        if isinstance(e, WebSocketDisconnect):
            print("client disconnected")
        else:
            print(f"Error: {e}")
    except:
        pass
    finally:
        try:
            await websocket.close(code=1011, reason=f"Error: {e}")
            await voice_agent.stop()
        except:
            pass



@app.get("/ping")
async def ping():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8080)
