# Laser Engraver Helper

A comprehensive Windows application that combines real-time wood identification with laser engraving settings recommendations. Uses computer vision to identify wood types and provides optimal speed, power, and pass settings for your diode laser.

## 🎯 Features

### Wood Identification
- **Real-time wood recognition** using LAB color space analysis
- **Multi-patch sampling** for accurate confidence scoring
- **Supports 20+ wood types**: Pine, Basswood, Oak, Maple, Walnut, Cherry, Mahogany, Ebony, and more
- **Grain direction detection** with visual overlay
- **Color-coded grain arrow**: Green for optimal alignment, Red for diagonal

### Laser Settings
- **Three operation modes**:
  - **Surface**: Single-pass engraving (default)
  - **Deep**: Multi-pass depth engraving
  - **Cut**: Through-cutting parameters
- **Realistic speed/power settings** based on real-world data
- **Support for 5W to 80W diode lasers**
- **Automatic pass calculation** based on material thickness

### Professional Features
- **Standalone Windows application** with installer
- **USB webcam integration** with OpenCV
- **Camera controls**: Brightness, contrast, exposure, auto-exposure
- **Snapshot capability** for documentation
- **Resizable window** with overlay toggle

## 🚀 Quick Start

### Option 1: Install from Release (Recommended)
1. Download `Engraver Helper-Setup.exe` from the [Releases](https://github.com/cooksta120021/laser_engraver_helper/releases) page
2. Run the installer
3. Launch from Desktop or Start Menu

### Option 2: Build from Source
```powershell
# Clone and install dependencies
git clone https://github.com/cooksta120021/laser_engraver_helper.git
cd laser_engraver_helper
pip install -r requirements.txt

# Run the application
python main.py
```

## 📊 How It Works

### Wood Identification Process
1. **Multi-patch sampling**: Analyzes 9 regions across the camera frame
2. **LAB color space**: Robust to lighting variations
3. **Vote counting**: More accurate than single-mean analysis
4. **Confidence scoring**: Based on patch agreement and color distance

### Settings Calculation
- **Surface mode**: Optimized for marking/engraving (1 pass)
- **Deep mode**: Calculates passes based on depth per pass (0.3-1.2mm depending on wood)
- **Cut mode**: Uses separate cutting database with slower speeds and 100% power

### Grain Detection
- **CLAHE enhancement**: Works in poor lighting conditions
- **Hough line transform**: Detects dominant grain direction
- **Visual feedback**: Arrow shows grain angle with color coding

## 🛠️ Supported Materials

### Softwoods
- Basswood, Pine, Poplar, Cedar, Bamboo, Cork

### Medium Hardwoods  
- Oak, Maple, Birch, Cherry, Alder, Mahogany

### Dense Hardwoods
- Walnut, Padauk, Purpleheart, Wenge, Ebony

### Engineered Materials
- Plywood, MDF/HDF

### Non-Wood
- Leather

## ⚙️ Technical Details

### Wood Database
- **LAB color signatures** for each wood type
- **Realistic laser settings** per wattage (5W-80W)
- **Depth per pass values** for engraving and cutting
- **Interpolation** for non-standard wattages

### Camera Integration
- **OpenCV with MediaFoundation backend** (Windows)
- **Multiple camera support** with index selection
- **Real-time processing** at 30 FPS
- **Resolution options**: 640x480, 1280x720, 1920x1080

## 📦 Building from Source

### Dependencies
```bash
pip install -r requirements.txt
```

### Build Executable
```bash
# Create icon
python create_icon.py

# Build standalone executable
python build_exe.py

# Create Windows installer
python build_installer.py
```

### Build Tools Used
- **PyInstaller**: Bundles Python and dependencies
- **NSIS**: Creates professional Windows installer
- **Pillow**: Icon generation

## 🎮 Usage Guide

### Basic Operation
1. **Select camera** from dropdown (default: Camera 0)
2. **Choose laser wattage** (5W-80W)
3. **Set material thickness** (for Deep/Cut modes)
4. **Select operation mode** (Surface/Deep/Cut)
5. **Point camera at wood** - identification happens automatically

### Camera Controls
- **Brightness/Contrast/Exposure sliders**: Fine-tune image quality
- **Auto-exposure button**: One-click optimization
- **Overlay toggle**: Show/hide visual overlays
- **Snapshot button**: Save current frame

### Reading the Display
```
Basswood  (67% confidence)
Speed: 3600 mm/min  |  Power: 60%  |  Passes: 1
Grain direction: 15
```

## 🔧 Configuration

Edit `config.py` for advanced settings:

```python
# Camera settings
REAL_CAMERA_INDEX = 0
REAL_CAMERA_WIDTH = 1280
REAL_CAMERA_HEIGHT = 720

# Recognition settings
CONFIDENCE_THRESHOLD = 0.3
MIN_PATCHES_FOR_IDENTIFICATION = 6
```

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| Camera shows black screen | Try different camera index (1, 2, etc.) |
| Wood identification inaccurate | Adjust lighting, ensure wood fills center of frame |
| Settings seem wrong | Check wattage selection, verify mode (Surface/Deep/Cut) |
| App won't start | Install Visual C++ Redistributable if missing |

## 📈 Performance Notes

- **CPU usage**: ~15-25% on modern processors
- **Memory usage**: ~200MB including camera buffers
- **Startup time**: ~3-5 seconds
- **Identification speed**: Real-time at 30 FPS

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly
5. Submit a pull request

### Areas for Contribution
- **Additional wood types** with LAB signatures
- **Improved recognition algorithms**
- **More laser settings data**
- **UI/UX improvements**
- **Bug fixes and optimizations**

## 📄 License

MIT License - see [LICENSE.txt](LICENSE.txt) for details.

## 🙏 Acknowledgments

- **OpenCV** for computer vision
- **Tkinter** for GUI framework
- **PyInstaller** for executable packaging
- **NSIS** for Windows installer
- **Community laser engravers** for settings data

---

**Made with ❤️ for the laser engraving community**
