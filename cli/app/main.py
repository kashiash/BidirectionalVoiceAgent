import json
import pyaudio
import websockets
import base64
import asyncio
import base64
import pyaudio
from rx.subject import Subject
from rx import operators as ops
from rx.scheduler.eventloop import AsyncIOScheduler
from typing import Dict
import os

# Audio configuration
# make sure that it matches the agent configuration
INPUT_SAMPLE_RATE = 16000
OUTPUT_SAMPLE_RATE = 16000
CHANNELS = 1
FORMAT = pyaudio.paInt16
CHUNK_SIZE = 512  # Number of frames per buffer
# region that the agent core runtime is deployed in
REGION = os.getenv("AWS_DEFAULT_REGION", "ap-northeast-1")

# Debug mode flag
DEBUG = False

def debug_print(*values: object):
    """Print only if debug mode is enabled"""
    if DEBUG:
        print(values)

def print_gray(message: str):
    print(f"\033[90m{message}\033[0m")


class AudioChatManager:

    def __init__(self, ws_endpoint: str, agnet_arn: str | None):
        """Initialize the stream manager."""
        self.input_subject = Subject()
        self.output_subject = Subject()
        self.audio_subject = Subject()

        self.websocket = None
        self.ws_endpoint = ws_endpoint
        self.agent_arn = agnet_arn

        self.response_task = None
        self.is_active = False
        self.barge_in = False
        self.scheduler = None

        # Audio playback components
        self.audio_output_queue = asyncio.Queue()


    async def initialize_chat(self):
        if self.agent_arn is not None:
            from bedrock_agentcore.runtime import AgentCoreRuntimeClient
            client = AgentCoreRuntimeClient(region=REGION)
            ws_url, headers = client.generate_ws_connection(
                runtime_arn=self.agent_arn,
                session_id=None
            )
            self.websocket = await websockets.connect(ws_url, additional_headers=headers)
            print_gray(f"connected to {ws_url}")
        else:
            self.websocket = await websockets.connect(self.ws_endpoint)
            print_gray(f"connected to {self.ws_endpoint}")

        self.scheduler = AsyncIOScheduler(asyncio.get_event_loop())

        try:
            self.is_active = True

            # Start listening for responses
            self.response_task = asyncio.create_task(self._process_responses())

            # Set up subscription for input events
            self.input_subject.pipe(
                ops.subscribe_on(self.scheduler)
            ).subscribe(
                on_next=lambda event: asyncio.create_task(self.send_raw_event(event)),
                on_error=lambda e: print(f"Input stream error: {e}")
            )

            # Set up subscription for audio chunks
            self.audio_subject.pipe(
                ops.subscribe_on(self.scheduler)
            ).subscribe(
                on_next=lambda audio_data: asyncio.create_task(self._handle_audio_input(audio_data)),
                on_error=lambda e: print(f"Audio stream error: {e}")
            )

            print_gray("Stream initialized successfully")
            return self
        except Exception as e:
            self.is_active = False
            print(f"Failed to initialize stream: {str(e)}")
            import traceback
            traceback.print_exc()
            raise

    async def send_raw_event(self, event_json):
        """Send a raw event JSON to the Bedrock stream."""
        if not self.websocket or not self.is_active:
            print("Stream not initialized or closed")
            return

        try:
            await self.websocket.send(json.dumps(event_json), text=True)
        except Exception as e:
            print(f"Error sending event: {str(e)}")
            self.input_subject.on_error(e)


    async def _handle_audio_input(self, data):
        """Process audio input before sending it to the stream."""
        audio_bytes = data.get("audio_bytes")

        if not audio_bytes:
            print("No audio bytes received")
            return

        try:
            # Base64 encode the audio data
            audio_base64 = base64.b64encode(audio_bytes).decode("utf-8")
            # BidiAudioInputEvent:
            # https://strandsagents.com/latest/documentation/docs/user-guide/concepts/experimental/bidirectional-streaming/events/#bidiaudioinputevent
            audio_event = {
                "type": "bidi_audio_input",
                "audio": audio_base64,
                "format": FORMAT,
                "sample_rate": INPUT_SAMPLE_RATE,
                "channels": CHANNELS,
            }
            # Send the event directly
            await self.send_raw_event(audio_event)
        except Exception as e:
            print(f"Error processing audio: {e}")


    def add_audio_chunk(self, audio_bytes):
        """Add an audio chunk to the stream."""
        self.audio_subject.on_next({
            "audio_bytes": audio_bytes,
        })

    async def _process_responses(self):
        """Process incoming responses from Bedrock."""
        try:
            while self.is_active:
                try:
                    output = await self.websocket.recv()
                    event: Dict = json.loads(output)
                    event_type = event.get("type")
                    debug_print("event received: ", event.get("type"))

                    if event_type == "bidi_audio_stream":
                        base64_audio = event["audio"]
                        audio_bytes = base64.b64decode(base64_audio)
                        await self.audio_output_queue.put(audio_bytes)

                    elif event_type == "bidi_transcript_stream":
                        role = event["role"]
                        text = event["text"]
                        is_final = event["is_final"]

                        if is_final:
                            print(f"{role}: {text}")
                        else:
                            print_gray(f"{role} (preview): {text}")

                    elif event_type == "tool_use_stream":
                        tool_use: Dict = event["current_tool_use"]
                        print(f"Using tool: {tool_use["name"]}. Input: {str(tool_use["input"])}")

                    elif event_type == "bidi_interruption":
                        print_gray(f"Interrupted by {event["reason"]}")
                        self.barge_in = True

                    elif event_type == "bidi_connection_restart":
                        # Connection restarts automatically
                        print_gray("Reconnecting...")
                        await asyncio.sleep(0.05)

                    elif event_type == "bidi_error":
                        raise Exception(f"{event["message"]}")

                    self.output_subject.on_next(event)
                except StopAsyncIteration:
                    # Stream has ended
                    break
                except Exception as e:
                    print(f"Error receiving response: {e}")
                    self.output_subject.on_error(e)
                    break
        except Exception as e:
            print(f"Response processing error: {e}")
            self.output_subject.on_error(e)
        finally:
            if self.is_active:
                self.output_subject.on_completed()


    async def close(self):
        """Close the stream properly."""
        if not self.is_active:
            return

        # Complete the subjects
        self.input_subject.on_completed()
        self.audio_subject.on_completed()

        if self.response_task and not self.response_task.done():
            self.response_task.cancel()

        # BidiTextInputEvent
        # https://strandsagents.com/latest/documentation/docs/user-guide/concepts/experimental/bidirectional-streaming/events/#biditextinputevent
        end_event = {
            "type": "bidi_text_input",
            "text": "Ending conversation",
            "role": "user",
        }
        await self.send_raw_event(end_event)


        if self.websocket:
            await self.websocket.close()


class AudioStreamer:
    """Handles continuous microphone input and audio output using separate streams."""

    def __init__(self, chat_manager: AudioChatManager):
        self.chat_manager = chat_manager
        self.is_streaming = False
        self.loop = asyncio.get_event_loop()

        # Initialize PyAudio
        print_gray("AudioStreamer Initializing PyAudio...")
        self._audio = pyaudio.PyAudio()
        print_gray("AudioStreamer PyAudio initialized")

        # Initialize separate streams for input and output
        # Input stream with callback for microphone
        print_gray("Opening input audio stream...")
        self.input_stream = self._audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=INPUT_SAMPLE_RATE,
            input=True,
            frames_per_buffer=CHUNK_SIZE,
            stream_callback=self.input_callback
        )
        print_gray("input audio stream opened")

        # Output stream for direct writing (no callback)
        print_gray("Opening output audio stream...")
        self.output_stream = self._audio.open(
            format=FORMAT,
            channels=CHANNELS,
            rate=OUTPUT_SAMPLE_RATE,
            output=True,
            frames_per_buffer=CHUNK_SIZE
        )

        print_gray("output audio stream opened")

    def input_callback(self, in_data, frame_count, time_info, status):
        """Callback function that schedules audio processing in the asyncio event loop"""
        if self.is_streaming and in_data:
            # Schedule the task in the event loop
            asyncio.run_coroutine_threadsafe(
                self.process_input_audio(in_data),
                self.loop
            )
        return (None, pyaudio.paContinue)

    async def process_input_audio(self, audio_data):
        """Process a single audio chunk directly"""
        try:
            # Send audio to Bedrock immediately
            self.chat_manager.add_audio_chunk(audio_data)
        except Exception as e:
            if self.is_streaming:
                print(f"Error processing input audio: {e}")

    async def play_output_audio(self):
        """Play audio responses from Nova Sonic"""
        while self.is_streaming:
            try:
                # Check for barge-in flag
                if self.chat_manager.barge_in:
                    # Clear the audio queue
                    while not self.chat_manager.audio_output_queue.empty():
                        try:
                            self.chat_manager.audio_output_queue.get_nowait()
                        except asyncio.QueueEmpty:
                            break
                    self.chat_manager.barge_in = False
                    # Small sleep after clearing
                    await asyncio.sleep(0.05)
                    continue

                # Get audio data from the stream manager"s queue
                audio_data = await asyncio.wait_for(
                    self.chat_manager.audio_output_queue.get(),
                    timeout=0.1
                )

                if audio_data and self.is_streaming:
                    # Write directly to the output stream in smaller chunks
                    chunk_size = CHUNK_SIZE  # Use the same chunk size as the stream

                    # Write the audio data in chunks to avoid blocking too long
                    for i in range(0, len(audio_data), chunk_size):
                        if not self.is_streaming:
                            break

                        end = min(i + chunk_size, len(audio_data))
                        chunk = audio_data[i:end]

                        # Create a new function that captures the chunk by value
                        def write_chunk(data):
                            return self.output_stream.write(data)

                        # Pass the chunk to the function
                        await asyncio.get_event_loop().run_in_executor(None, write_chunk, chunk)

                        # Brief yield to allow other tasks to run
                        await asyncio.sleep(0.001)

            except asyncio.TimeoutError:
                # No data available within timeout, just continue
                continue
            except Exception as e:
                if self.is_streaming:
                    print(f"Error playing output audio: {str(e)}")
                    import traceback
                    traceback.print_exc()
                await asyncio.sleep(0.05)

    async def start_streaming(self):
        """Start streaming audio."""
        if self.is_streaming:
            return

        print("Stream starts! You can now speak into your microphone to start chatting with the agent!")
        print("To stop chatting and end streaming, press Enter!")
        print("----------------")

        self.is_streaming = True

        # Start the input stream if not already started
        if not self.input_stream.is_active():
            self.input_stream.start_stream()

        # Start processing tasks
        #self.input_task = asyncio.create_task(self._audiorocess_input_audio())
        self.output_task = asyncio.create_task(self.play_output_audio())

        # Wait for user to press Enter to stop
        await asyncio.get_event_loop().run_in_executor(None, input)

        # Once input() returns, stop streaming
        await self.stop_streaming()

    async def stop_streaming(self):
        """Stop streaming audio."""
        if not self.is_streaming:
            return

        self.is_streaming = False

        # Cancel the tasks
        tasks: list[asyncio.Task] = []

        if hasattr(self, "output_task") and not self.output_task.done():
            tasks.append(self.output_task)

        for task in tasks:
            task.cancel()

        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        # Stop and close the streams
        if self.input_stream:
            if self.input_stream.is_active():
                self.input_stream.stop_stream()
            self.input_stream.close()

        if self.output_stream:
            if self.output_stream.is_active():
                self.output_stream.stop_stream()
            self.output_stream.close()

        if self._audio:
            self._audio.terminate()

        await self.chat_manager.close()


async def main(debug=False, endpoint: str="ws://localhost:8080/ws", agent_arn: str | None = None):
    """Main function to run the application."""
    global DEBUG
    DEBUG = debug

    # Create stream manager
    chat_manager = AudioChatManager(ws_endpoint=endpoint, agnet_arn=agent_arn)

    # Create audio streamer
    audio_streamer = AudioStreamer(chat_manager)

    # Initialize the stream
    await chat_manager.initialize_chat()

    try:
        # This will run until the user presses Enter
        await audio_streamer.start_streaming()

    except KeyboardInterrupt:
        print("Interrupted by user")
    finally:
        # Clean up
        await audio_streamer.stop_streaming()


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Itsuki's Bi-directional Voice Chat!")
    parser.add_argument("--debug", action="store_true", help="Enable debug mode")
    parser.add_argument("--endpoint", type=str, default="ws://localhost:8080/ws", help="Websocket endpoint")
    parser.add_argument("--agent_arn", type=str, help="agent core runtime arn. Ex: arn:aws:bedrock-agentcore:ap-...-1:...:runtime/...")
    args = parser.parse_args()

    # Set your AWS credentials here or use environment variables
    # os.environ["AWS_ACCESS_KEY_ID"] = "AWS_ACCESS_KEY_ID"
    # os.environ["AWS_SECRET_ACCESS_KEY"] = "AWS_SECRET_ACCESS_KEY"
    # os.environ["AWS_DEFAULT_REGION"] = "us-east-1"


    try:
        asyncio.run(main(debug=args.debug, endpoint=args.endpoint, agent_arn=args.agent_arn))
    except asyncio.exceptions.CancelledError:
        pass
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"Application error: {e}")
        import traceback
        traceback.print_exc()
