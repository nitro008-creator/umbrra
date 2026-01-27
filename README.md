# umbrra
Umbrra v1.2: A professional ADB-based post-exploitation framework for Android security auditing. Features automated data exfiltration, stealth mirroring, and forensic trace removal.



Umbrra is a command-line interface (CLI) framework designed for advanced Android administration and security auditing via ADB (Android Debug Bridge).

## Core Capabilities
- **Automated Exfiltration**: Extract SMS, contacts, and account metadata.
- **Stealth Monitoring**: Low-latency screen mirroring using H.264.
- **Forensic Cleanup**: Automated wiping of shell history, logcat buffers, and temporary files.
- **Environment Interaction**: Remote microphone recording and GPS location tracking.

## Prerequisites
- Python 3.8+
- ADB binaries (located in `./ADB/`)
- Scrcpy binaries (located in `./ADB/` for mirroring)

## Installation
```bash
git clone [https://github.com/username/umbrra.git](https://github.com/username/umbrra.git)
cd umbrra
pip install rich
```

Interactive CLI Mode
To launch the interactive command-line interface, run the script without arguments or with only the target IP:

```bash
python umbrra.py 192.168.1.2
```
Quick Commands (Non-Interactive)

Execute specific modules directly and exit immediately. Example of device auditing followed by automated cleanup:

```bash
python umbrra.py 192.168.1.2 --info --anon
```

