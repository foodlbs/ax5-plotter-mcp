# Contributing to AX5 Plotter Photo Booth

Thank you for your interest in contributing to this project!

## Project Overview

This is a showcase project demonstrating the integration of:
- Computer vision and image processing
- AI-powered image transformation
- Hardware control (pen plotter)
- Queue management systems
- Interactive UI development

## How to Contribute

### Reporting Issues

If you find a bug or have a suggestion:
1. Check if the issue already exists
2. Create a detailed issue description including:
   - Steps to reproduce (for bugs)
   - Expected vs actual behavior
   - Your environment (OS, Python version, etc.)
   - Relevant logs or error messages

### Suggesting Features

Feature suggestions are welcome! Please describe:
- The use case
- Expected behavior
- Why this would be valuable

### Code Contributions

While this is primarily a portfolio/showcase project, improvements are welcome:

1. **Fork the repository**
2. **Create a feature branch**: `git checkout -b feature/your-feature-name`
3. **Make your changes**
4. **Test thoroughly**: Run `python test_photo_booth.py`
5. **Commit with clear messages**: `git commit -m "Add: feature description"`
6. **Push to your fork**: `git push origin feature/your-feature-name`
7. **Submit a Pull Request**

## Development Setup

```bash
# Clone the repository
git clone https://github.com/yourusername/ax5-plotter-mcp.git
cd ax5-plotter-mcp

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy example config
cp config/settings.example.yaml config/settings.yaml

# Run tests
python test_photo_booth.py

# Run the application
python photo_booth_app.py
```

## Code Style

- Follow PEP 8 guidelines
- Use meaningful variable and function names
- Add docstrings to functions and classes
- Comment complex logic
- Keep functions focused and modular

## Testing

Before submitting:
- Run the test suite: `python test_photo_booth.py`
- Test with both AI and Canny processing
- Verify the UI works correctly
- Test queue management features

## Areas for Improvement

Some ideas if you want to contribute:

### New Features
- Additional artistic styles
- More AI provider options
- Batch processing mode
- Image editing/cropping tools
- Print preview enhancements
- Email delivery integration
- Web interface version

### Improvements
- Performance optimizations
- Better error handling
- Enhanced logging
- More comprehensive tests
- Documentation improvements
- UI/UX enhancements

### Hardware
- Support for other plotters
- Additional pen profiles
- Multi-plotter support

## Questions?

Feel free to open an issue for questions or discussions!

## License

By contributing, you agree that your contributions will be licensed under the MIT License.
