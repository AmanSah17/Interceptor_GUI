# Interceptor GUI (GCS Dashboard)

A robust, professional Ground Control Station (GCS) Dashboard built with Python and PyQt6. The Interceptor GUI is designed to display live telemetry, high-definition video streams, dynamic map overlays, and target tracking analytics in a unified, military-style Heads Up Display (HUD).

## Features
- **Live Video Streaming:** Decodes and renders live OpenCV video feeds with real-time bounding box tracking.
- **Dynamic Minimap Overlay:** An embedded map widget positioned statically over the video feed, pulling live XYZ tile coordinates based on incoming GPS telemetry.
- **Real-Time Telemetry HUD:** Displays Altitude, Speed, Heading, Vertical Speed, and Battery levels with dynamic graphical indicators.
- **Target Tracking Table:** Dynamically populates a table of identified targets with confidence percentages and localized coordinates.
- **Stream Health Watchdog:** Actively monitors video stream latency and connection status. Automatically attempts to reconnect and displays a "SIGNAL LOST" overlay if the stream drops, preventing UI freezing.
- **Backend Architecture:** Powered by a FastAPI backend that handles local database logging and simulated/live telemetry generation.

## Prerequisites
- Windows OS (Tested on Windows 11)
- **Python 3.10+**
- (Optional but Recommended) A virtual environment. The default setup assumes `D:\CUDA_ENV`.

## Installation

1. **Clone the Repository:**
   ```bash
   git clone https://github.com/AmanSah17/Interceptor_GUI.git
   cd Interceptor_GUI
   ```

2. **Activate your Virtual Environment:**
   If using the default `CUDA_ENV` setup:
   ```powershell
   D:\CUDA_ENV\Scripts\activate
   ```
   *Otherwise, create and activate a new virtual environment.*

3. **Install Dependencies:**
   Ensure you have the required packages installed. *(A `requirements.txt` is recommended, but primary dependencies are below)*
   ```bash
   pip install PyQt6 opencv-python numpy fastapi uvicorn requests
   ```

## Running the Application

To launch the dashboard, ensure your virtual environment is active, then run the primary entry point script:

```powershell
# Activate the environment
D:\CUDA_ENV\Scripts\activate

# Run the GUI
python run_app.py
```

### Video Source configuration
By default, the `VideoWorker` connects to an external streaming URL. To change the stream source (e.g. to a local webcam or a different IP camera):
1. Open `app/workers.py`
2. Locate the `VideoWorker` class.
3. Modify the `stream_url` variable to match your stream endpoint.
```python
stream_url = "https://fretted-tarnish-anchor.ngrok-free.dev/stream" # Change this URL
```

## Project Structure
```
Interceptor_GUI/
│
├── run_app.py                # Main application entry point
├── README.md                 # This documentation
├── .gitignore                # Git ignore configurations
│
├── app/                      # Frontend PyQt6 Interface
│   ├── main_window.py        # Core dashboard layout and component assembly
│   ├── video_panel.py        # Renders OpenCV frames, overlays, and stream status
│   ├── minimap_widget.py     # Live GPS map overlay
│   ├── compass_widget.py     # Custom drawn compass indicator
│   ├── theme.py              # Application colors and styles
│   └── workers.py            # QThread workers for Telemetry and Video fetching
│
└── backend/                  # Backend Services
    ├── server.py             # FastAPI server for data routing
    ├── database.py           # SQLite handlers for logging flight sessions
    ├── telemetry_sim.py      # Telemetry generator
    └── video_generator.py    # Legacy local video generator
```

## Contributing
When contributing to this repository, please ensure that all UI modifications maintain the high-contrast dark theme (defined in `app/theme.py`) and use grid-based layouts to preserve the professional dashboard aesthetics.
