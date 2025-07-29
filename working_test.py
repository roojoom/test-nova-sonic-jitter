#!/usr/bin/env python3
"""
Nova Sonic Jitter Test - Records audio responses and analyzes jitter patterns

This script tests AWS Nova Sonic's audio streaming behavior by:
1. Sending a trigger signal followed by test audio
2. Recording all audio response chunks with precise timestamps
3. Analyzing jitter (timing variations) in the audio stream
4. Saving audio files and generating jitter reports
"""

import asyncio
import os
import sys
import time
import wave
import json
from datetime import datetime
from dotenv import load_dotenv
from pydub import AudioSegment
from loguru import logger
import statistics

# Add the pipecat src to Python path
sys.path.insert(0, "/Users/ormeirov/Projects/tests/pipecat/src")

from pipecat.processors.aggregators.openai_llm_context import OpenAILLMContext
from pipecat.services.aws_nova_sonic import AWSNovaSonicLLMService
from pipecat.frames.frames import (
    StartFrame, EndFrame, InputAudioRawFrame, TTSAudioRawFrame,
    TTSStartedFrame, TTSStoppedFrame, LLMTextFrame
)
from pipecat.pipeline.pipeline import Pipeline
from pipecat.pipeline.runner import PipelineRunner
from pipecat.pipeline.task import PipelineTask
from pipecat.processors.logger import FrameLogger

# Load environment variables
load_dotenv()

class AudioRecorder(FrameLogger):
    """Extends FrameLogger to record Nova Sonic audio responses with comprehensive jitter analysis"""

    def __init__(self):
        super().__init__()
        self.chunks = []
        self.timestamps = []
        self.chunk_sizes = []
        self.start_time = None
        self.session_start = time.time()
        self.text_content = ""

    async def process_frame(self, frame, direction):
        # Let the parent logger handle all frames first
        await super().process_frame(frame, direction)
        
        # Debug: Log ALL frame types we receive
        frame_type = type(frame).__name__
        logger.info(f"🔍 FRAME: {frame_type} (direction: {direction.name})")
        
        # Then handle our specific audio recording
        if isinstance(frame, TTSStartedFrame):
            logger.info("🎵 Audio generation started")
            self.start_time = time.time()
            self.chunks = []
            self.timestamps = []
            self.chunk_sizes = []

        elif isinstance(frame, TTSAudioRawFrame):
            if self.start_time:
                current_time = time.time()
                elapsed = current_time - self.start_time
                chunk_size = len(frame.audio)
                
                logger.info(f"🔊 Chunk #{len(self.chunks)+1}: {chunk_size} bytes at {elapsed:.4f}s")
                
                self.chunks.append(frame.audio)
                self.timestamps.append(elapsed)
                self.chunk_sizes.append(chunk_size)

        elif isinstance(frame, TTSStoppedFrame):
            logger.info("🛑 Audio generation stopped")
            await self._analyze_and_save()

        elif isinstance(frame, LLMTextFrame):
            self.text_content += frame.text
            logger.info(f"💬 Text: {frame.text}")

    async def _analyze_and_save(self):
        if not self.chunks:
            logger.warning("⚠️ No audio chunks to analyze")
            return

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        base_filename = f"nova_{timestamp}"
        
        # Save audio file
        audio_filename = f"{base_filename}.wav"
        audio_data = b''.join(self.chunks)
        
        with wave.open(audio_filename, 'wb') as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(24000)
            f.writeframes(audio_data)
        
        # Calculate comprehensive metrics
        total_chunks = len(self.chunks)
        total_bytes = len(audio_data)
        duration = total_bytes / (24000 * 2)  # 24kHz, 16-bit
        
        logger.info(f"💾 Saved {audio_filename} - {duration:.2f}s, {total_chunks} chunks, {total_bytes} bytes")
        
        # Detailed jitter analysis
        if total_chunks > 1:
            intervals = [self.timestamps[i] - self.timestamps[i-1] for i in range(1, len(self.timestamps))]
            
            # Basic statistics
            avg_interval = statistics.mean(intervals)
            median_interval = statistics.median(intervals)
            min_interval = min(intervals)
            max_interval = max(intervals)
            jitter_range = max_interval - min_interval
            
            # Variability metrics
            std_dev = statistics.stdev(intervals) if len(intervals) > 1 else 0
            variance = statistics.variance(intervals) if len(intervals) > 1 else 0
            
            # Percentiles
            intervals_sorted = sorted(intervals)
            p95 = intervals_sorted[int(0.95 * len(intervals_sorted))]
            p99 = intervals_sorted[int(0.99 * len(intervals_sorted))]
            
            # Chunk size analysis
            avg_chunk_size = statistics.mean(self.chunk_sizes)
            min_chunk_size = min(self.chunk_sizes)
            max_chunk_size = max(self.chunk_sizes)
            
            # Create comprehensive report
            jitter_report = {
                "test_info": {
                    "timestamp": timestamp,
                    "audio_file": audio_filename,
                    "text_content": self.text_content.strip(),
                    "total_duration_seconds": duration,
                    "total_chunks": total_chunks,
                    "total_bytes": total_bytes
                },
                "timing_analysis": {
                    "intervals_ms": [round(i * 1000, 2) for i in intervals],
                    "avg_interval_ms": round(avg_interval * 1000, 2),
                    "median_interval_ms": round(median_interval * 1000, 2),
                    "min_interval_ms": round(min_interval * 1000, 2),
                    "max_interval_ms": round(max_interval * 1000, 2),
                    "jitter_range_ms": round(jitter_range * 1000, 2),
                    "std_deviation_ms": round(std_dev * 1000, 2),
                    "variance_ms2": round(variance * 1000000, 2),
                    "p95_percentile_ms": round(p95 * 1000, 2),
                    "p99_percentile_ms": round(p99 * 1000, 2)
                },
                "chunk_analysis": {
                    "chunk_sizes_bytes": self.chunk_sizes,
                    "avg_chunk_size_bytes": round(avg_chunk_size, 2),
                    "min_chunk_size_bytes": min_chunk_size,
                    "max_chunk_size_bytes": max_chunk_size,
                    "chunk_size_variation_bytes": max_chunk_size - min_chunk_size
                },
                "quality_assessment": {
                    "high_jitter_warning": jitter_range > 0.1,
                    "irregular_chunks_warning": (max_chunk_size - min_chunk_size) > avg_chunk_size * 0.5,
                    "consistency_score": max(0, 100 - (std_dev * 1000))  # Lower std_dev = higher score
                }
            }
            
            # Save detailed report
            report_filename = f"{base_filename}_jitter_report.json"
            with open(report_filename, 'w') as f:
                json.dump(jitter_report, f, indent=2)
            
            # Log summary
            logger.info(f"📊 === JITTER ANALYSIS SUMMARY ===")
            logger.info(f"📈 Chunks: {total_chunks}, Duration: {duration:.2f}s")
            logger.info(f"⏱️  Avg Interval: {avg_interval*1000:.2f}ms, Std Dev: {std_dev*1000:.2f}ms")
            logger.info(f"📏 Jitter Range: {jitter_range*1000:.2f}ms (min: {min_interval*1000:.2f}ms, max: {max_interval*1000:.2f}ms)")
            logger.info(f"📦 Avg Chunk Size: {avg_chunk_size:.0f} bytes")
            logger.info(f"🎯 Consistency Score: {jitter_report['quality_assessment']['consistency_score']:.1f}/100")
            
            if jitter_range > 0.1:
                logger.warning(f"🚨 HIGH JITTER DETECTED: {jitter_range*1000:.2f}ms range")
            if jitter_report['quality_assessment']['irregular_chunks_warning']:
                logger.warning(f"🚨 IRREGULAR CHUNK SIZES: {max_chunk_size - min_chunk_size} bytes variation")
                
            logger.info(f"📄 Detailed report saved: {report_filename}")
        
        else:
            logger.warning("⚠️ Not enough chunks for jitter analysis")

async def main():
    logger.info("🚀 Working Nova Sonic Test")
    
    # Get AWS credentials
    access_key = os.getenv("AWS_ACCESS_KEY_ID")
    secret_key = os.getenv("AWS_SECRET_ACCESS_KEY")
    region = os.getenv("AWS_REGION", "eu-north-1")
    
    if not access_key or not secret_key:
        logger.error("❌ Missing AWS credentials")
        return
    
    # Load test audio
    try:
        audio = AudioSegment.from_mp3("hello-46355.mp3")
        audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
        audio_data = audio.raw_data
        logger.info(f"🎤 Loaded {len(audio_data)} bytes")
    except Exception as e:
        logger.error(f"❌ Audio error: {e}")
        return
    
    # Create Nova Sonic service
    system_msg = f"You are helpful. {AWSNovaSonicLLMService.AWAIT_TRIGGER_ASSISTANT_RESPONSE_INSTRUCTION}"
    
    llm = AWSNovaSonicLLMService(
        access_key_id=access_key,
        secret_access_key=secret_key,
        region=region,
        voice_id="tiffany",
        system_instruction=system_msg
    )
    
    # Create context
    context = OpenAILLMContext(
        messages=[
            {"role": "system", "content": system_msg},
            {"role": "user", "content": "Hello!"},
        ]
    )
    
    context_agg = llm.create_context_aggregator(context)
    recorder = AudioRecorder()
    
    # Simple pipeline
    pipeline = Pipeline([
        context_agg.user(),
        llm,
        recorder,
        context_agg.assistant(),
    ])
    
    task = PipelineTask(pipeline)
    runner = PipelineRunner()
    
    # Run
    logger.info("▶️ Starting...")
    runner_task = asyncio.create_task(runner.run(task))
    
    try:
        await asyncio.sleep(1)
        
        # Send StartFrame first
        await task.queue_frames([StartFrame()])
        await asyncio.sleep(1)
        
        # Send context
        await task.queue_frames([context_agg.user().get_context_frame()])
        await asyncio.sleep(3)
        
        # Trigger
        logger.info("🎯 Triggering...")
        await llm.trigger_assistant_response()
        await asyncio.sleep(3)
        
        # Send audio
        logger.info("🎤 Sending audio...")
        for i in range(0, len(audio_data), 1600):
            chunk = audio_data[i:i+1600]
            frame = InputAudioRawFrame(audio=chunk, sample_rate=16000, num_channels=1)
            await task.queue_frames([frame])
            await asyncio.sleep(0.1)
        
        # Wait for response
        logger.info("⏳ Waiting for response...")
        await asyncio.sleep(10)
        
        # Send EndFrame to trigger clean shutdown
        logger.info("🏁 Sending EndFrame...")
        await task.queue_frames([EndFrame()])
        
        # Give some time for clean shutdown
        await asyncio.sleep(2)
        
    except Exception as e:
        logger.error(f"❌ Error during test: {e}")
    finally:
        try:
            # Cancel the runner task gracefully
            if not runner_task.done():
                runner_task.cancel()
                try:
                    await asyncio.wait_for(runner_task, timeout=5)
                except asyncio.TimeoutError:
                    logger.warning("⚠️ Runner task didn't finish within timeout")
                except asyncio.CancelledError:
                    logger.info("✅ Runner task cancelled successfully")
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
    
    logger.info("✅ Done")

if __name__ == "__main__":
    asyncio.run(main())
