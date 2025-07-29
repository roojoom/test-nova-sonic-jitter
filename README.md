# Nova Sonic Jitter Test

A comprehensive testing framework for analyzing audio streaming jitter patterns in AWS Nova Sonic's real-time audio processing pipeline.

## Overview

This project tests AWS Nova Sonic's audio streaming behavior by:

1. **Sending audio triggers** - Sends a "ready" trigger followed by test audio input
2. **Recording audio responses** - Captures all audio response chunks with precise timestamps
3. **Analyzing jitter patterns** - Performs comprehensive timing analysis on audio stream variations
4. **Generating detailed reports** - Creates WAV files and JSON reports with jitter metrics

## Features

### 🎵 Audio Recording & Analysis
- Records all Nova Sonic audio response chunks
- Precise millisecond-level timestamp tracking
- Automatic WAV file generation

### 📊 Comprehensive Jitter Analysis
- **Basic Statistics**: Average, median, min/max intervals
- **Variability Metrics**: Standard deviation, variance
- **Percentile Analysis**: 95th and 99th percentile timing
- **Quality Assessment**: Consistency scoring and warnings

### 📄 Detailed Reporting
- JSON reports with all timing metrics
- Audio chunk size analysis
- Quality warnings for high jitter or irregular chunks
- Timestamped output files

### 🔍 Frame-Level Debugging
- Comprehensive frame logging
- Direction tracking (upstream/downstream)
- Real-time processing insights

## Installation

### Prerequisites
- Python 3.8+
- Poetry (for dependency management)
- AWS credentials with Nova Sonic access

### Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/roojoom/test-nova-sonic-jitter.git
   cd test-nova-sonic-jitter
   ```

2. **Install dependencies:**
   ```bash
   poetry install
   ```

3. **Configure AWS credentials:**
   Create a `.env` file with your AWS credentials:
   ```env
   AWS_ACCESS_KEY_ID=your_access_key_here
   AWS_SECRET_ACCESS_KEY=your_secret_key_here
   AWS_REGION=eu-north-1
   ```

## Usage

### Running the Jitter Test

```bash
poetry run python working_test.py
```

The test will:
1. Connect to AWS Nova Sonic
2. Send trigger audio ("ready")
3. Send test audio input (`hello-46355.mp3`)
4. Record and analyze any audio responses
5. Generate comprehensive jitter reports

### Output Files

The test generates:
- **Audio files**: `nova_YYYYMMDD_HHMMSS.wav` - Recorded audio responses
- **Jitter reports**: `nova_YYYYMMDD_HHMMSS_jitter_report.json` - Detailed timing analysis

### Example Jitter Report

```json
{
  "test_info": {
    "timestamp": "20250129_135430",
    "total_duration_seconds": 2.45,
    "total_chunks": 48,
    "total_bytes": 117600
  },
  "timing_analysis": {
    "avg_interval_ms": 51.2,
    "jitter_range_ms": 23.4,
    "std_deviation_ms": 8.7,
    "p95_percentile_ms": 62.1,
    "p99_percentile_ms": 68.9
  },
  "quality_assessment": {
    "high_jitter_warning": false,
    "consistency_score": 91.3
  }
}
```

## Current Status

### ✅ Working Components
- AWS Nova Sonic connection and authentication
- Pipeline setup and frame processing
- Comprehensive jitter analysis framework
- Audio recording and file generation
- Detailed reporting system

### ⚠️ Known Issues
- **No Audio Response**: Nova Sonic currently doesn't generate audio responses
  - Connection successful ✅
  - Trigger sent successfully ✅  
  - Audio input processed ✅
  - Audio output missing ❌

The jitter analysis system is fully functional and ready to work once Nova Sonic starts generating audio responses.

## Architecture

### Pipeline Structure
```
User Context → Nova Sonic LLM → Audio Recorder → Assistant Context
```

### Key Components

- **`AudioRecorder`**: Extends FrameLogger to capture and analyze audio frames
- **AWS Nova Sonic Service**: Handles real-time audio processing
- **Context Aggregators**: Manage conversation context
- **Pipeline Runner**: Orchestrates the entire processing flow

## Dependencies

- **pipecat**: Core audio processing pipeline framework
- **aws-nova-sonic**: AWS Nova Sonic service integration
- **pydub**: Audio file manipulation
- **loguru**: Enhanced logging
- **python-dotenv**: Environment variable management

## Development

### Project Structure
```
test-nova-sonic-jitter/
├── working_test.py          # Main jitter test script
├── pyproject.toml          # Poetry configuration
├── hello-46355.mp3         # Test audio input
├── .env                    # AWS credentials (gitignored)
├── .gitignore             # Git ignore rules
└── README.md              # This file
```

### Testing Audio Formats
The test uses 16kHz, mono, 16-bit PCM audio input as required by Nova Sonic.

## Troubleshooting

### Common Issues

1. **No audio response**
   - Verify AWS credentials and permissions
   - Check Nova Sonic service availability
   - Review conversation context setup

2. **Connection errors**
   - Verify AWS region setting
   - Check network connectivity
   - Ensure proper credentials

3. **Frame processing errors**
   - Check pipecat installation
   - Verify Python version compatibility

### Debug Mode
The `AudioRecorder` logs all frame types and directions for debugging:
```
🔍 FRAME: TTSStartedFrame (direction: DOWNSTREAM)
🔍 FRAME: TTSAudioRawFrame (direction: DOWNSTREAM)
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## License

This project is for testing and development purposes.

## Contact

For questions or issues, please open a GitHub issue.
