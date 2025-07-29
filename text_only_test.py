#!/usr/bin/env python3
"""
Simple Text-Only Nova Sonic Test

This script tests if AWS Nova Sonic can generate any response at all by:
1. Sending only text input (no audio)
2. Recording any frames received back
3. Checking if Nova Sonic generates text or audio responses
"""

import asyncio
import os
import sys
import time
from dotenv import load_dotenv
from loguru import logger

# Add the pipecat src to Python path
sys.path.insert(0, "/Users/ormeirov/Projects/tests/pipecat/src")

from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.aws_nova_sonic import AWSNovaSonicLLMService
from pipecat.frames.frames import (
    StartFrame, EndFrame, LLMTextFrame, TTSAudioRawFrame,
    TTSStartedFrame, TTSStoppedFrame, TextFrame
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.logger import FrameLogger

# Load environment variables
load_dotenv()

class ResponseTracker(FrameLogger):
    """Tracks all frames received from Nova Sonic"""

    def __init__(self):
        super().__init__()
        self.responses = []
        self.text_responses = []
        self.audio_responses = []
        self.start_time = time.time()

    async def process_frame(self, frame, direction):
        # Let the parent logger handle all frames first
        await super().process_frame(frame, direction)
        
        # Track all frames with timestamps
        frame_type = type(frame).__name__
        elapsed = time.time() - self.start_time
        
        logger.info(f"🔍 FRAME: {frame_type} (direction: {direction.name}) at {elapsed:.2f}s")
        
        self.responses.append({
            'type': frame_type,
            'time': elapsed,
            'direction': direction.name
        })
        
        # Track specific response types
        if isinstance(frame, LLMTextFrame):
            text = getattr(frame, 'text', '')
            logger.info(f"💬 TEXT RESPONSE: {text}")
            self.text_responses.append(text)
            
        elif isinstance(frame, TTSStartedFrame):
            logger.info("🎵 AUDIO GENERATION STARTED")
            
        elif isinstance(frame, TTSAudioRawFrame):
            chunk_size = len(frame.audio)
            logger.info(f"🔊 AUDIO CHUNK: {chunk_size} bytes")
            self.audio_responses.append(chunk_size)
            
        elif isinstance(frame, TTSStoppedFrame):
            logger.info("🛑 AUDIO GENERATION STOPPED")
            
        # Handle input frames (these are normal, not responses)
        elif frame_type == "InputAudioRawFrame":
            chunk_size = len(getattr(frame, 'audio', b''))
            logger.info(f"🎤 INPUT AUDIO: {chunk_size} bytes (this is our input, not Nova Sonic's response)")
            
        elif frame_type == "TextFrame":
            text = getattr(frame, 'text', '')
            logger.info(f"📝 INPUT TEXT: {text} (this is our input, not Nova Sonic's response)")
            
        # Handle control frames
        elif frame_type in ["StartFrame", "EndFrame", "OpenAILLMContextFrame"]:
            logger.info(f"⚙️ CONTROL FRAME: {frame_type}")
            
        else:
            logger.warning(f"🔍 UNHANDLED FRAME TYPE: {frame_type}")

    def get_summary(self):
        return {
            'total_frames': len(self.responses),
            'text_responses': self.text_responses,
            'audio_chunk_count': len(self.audio_responses),
            'total_audio_bytes': sum(self.audio_responses),
            'frame_types': list(set(r['type'] for r in self.responses))
        }

async def main():
    logger.info("🚀 Simple Text-Only Nova Sonic Test")
    
    # Get AWS credentials
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = "eu-north-1"
    
    if not access_key or not secret_key:
        logger.error("❌ Missing AWS credentials")
        return
    
    logger.info(f"🌍 Using region: {region}")
    
    # Create Nova Sonic service WITHOUT trigger instruction to test
    system_msg = "Tell me about the weather."
    
    logger.info(f"📝 System message: {system_msg[:100]}...")
    
    llm = AWSNovaSonicLLMService(
        access_key_id=access_key,
        secret_access_key=secret_key,
        region=region,
        voice_id="tiffany",
        system_instruction=system_msg
    )
    
    # Create context with a simple question
    context = OpenAILLMContext(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "What's the weather like today?"},
        ]
    )
    
    context_agg = llm.create_context_aggregator(context)
    tracker = ResponseTracker()
    
    # Simple pipeline
    pipeline = Pipeline([
        context_agg.user(),
        llm,
        tracker,
        context_agg.assistant(),
    ])
    
    task = PipelineTask(pipeline)
    runner = PipelineRunner()
    
    logger.info("▶️ Starting pipeline...")
    runner_task = asyncio.create_task(runner.run(task))
    
    try:
        # Give the system time to initialize
        await asyncio.sleep(1)
        
        # Send StartFrame
        logger.info("📤 Sending StartFrame...")
        await task.queue_frames([StartFrame()])
        await asyncio.sleep(1)
        
        # Queue context frame
        logger.info("📤 Queueing context frame...")
        await task.queue_frames([context_agg.user().get_context_frame()])
        await asyncio.sleep(2)
        
        # Trigger assistant response
        logger.info("🎯 Triggering assistant response...")
        await llm.trigger_assistant_response()
        
        # CRITICAL: Wait for Nova Sonic to fully process the trigger
        logger.info("⏳ Waiting 9+ seconds for Nova Sonic to PROCESS trigger (NO input frames)...")
        await asyncio.sleep(10)  # Wait 10 seconds to be safe
        
        # NOW send input after Nova Sonic has processed
        logger.info("📤 NOW sending text frame AFTER Nova Sonic processing...")
        text_frame = TextFrame("What is 2 plus 2?")
        await task.queue_frames([text_frame])
        
        # CRITICAL: Give Nova Sonic time to process the input and generate response
        logger.info("⏳ Waiting 15+ seconds for Nova Sonic to PROCESS input and generate response...")
        await asyncio.sleep(15)  # Give Nova Sonic plenty of time to process input and respond
        
        # Send EndFrame
        logger.info("🏁 Sending EndFrame...")
        await task.queue_frames([EndFrame()])
        await asyncio.sleep(2)
        
    except Exception as e:
        logger.error(f"❌ Error during test: {e}")
        import traceback
        logger.error(f"❌ Traceback: {traceback.format_exc()}")
    finally:
        try:
            if not runner_task.done():
                runner_task.cancel()
                try:
                    await asyncio.wait_for(runner_task, timeout=5)
                except (asyncio.TimeoutError, asyncio.CancelledError):
                    logger.info("✅ Runner task cancelled")
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
    
    # Print summary
    summary = tracker.get_summary()
    logger.info("📊 === TEST SUMMARY ===")
    logger.info(f"📈 Total frames received: {summary['total_frames']}")
    logger.info(f"💬 Text responses: {len(summary['text_responses'])}")
    logger.info(f"🔊 Audio chunks: {summary['audio_chunk_count']}")
    logger.info(f"📦 Total audio bytes: {summary['total_audio_bytes']}")
    logger.info(f"🔍 Frame types seen: {', '.join(summary['frame_types'])}")
    
    if summary['text_responses']:
        logger.info("✅ TEXT RESPONSES RECEIVED:")
        for i, text in enumerate(summary['text_responses'], 1):
            logger.info(f"   {i}. {text}")
    else:
        logger.warning("⚠️ No text responses received")
        
    if summary['total_audio_bytes'] > 0:
        logger.info(f"✅ AUDIO RECEIVED: {summary['total_audio_bytes']} bytes in {summary['audio_chunk_count']} chunks")
    else:
        logger.warning("⚠️ No audio responses received")
    
    logger.info("✅ Test completed")

if __name__ == "__main__":
    asyncio.run(main())
