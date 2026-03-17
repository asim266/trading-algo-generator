# 🤖 AI Code Generator

An intelligent Python code generator powered by Claude Opus AI that takes dual prompts, generates code, and automatically fixes runtime errors through iterative refinement.

## ✨ Features

- **Dual Prompt System**: Uses both static and auto-generated prompts
- **Automatic Error Fixing**: Iteratively resolves runtime errors using AI
- **Real-time Execution**: Tests generated code immediately
- **Beautiful UI**: Clean Bootstrap interface with syntax highlighting
- **Progress Tracking**: Shows execution logs and statistics
- **Code Persistence**: Saves generated code to files
- **Configurable Settings**: All settings managed via config.ini file

## 🚀 How It Works

1. **Input**: User provides a static prompt and instructions for auto-generating a second prompt
2. **Generation**: Claude Opus creates a second prompt based on instructions
3. **Code Creation**: AI generates Python code using both prompts
4. **Execution**: Code is run in a sandboxed environment
5. **Error Resolution**: If errors occur, AI automatically fixes them
6. **Iteration**: Process repeats until code runs successfully (configurable max attempts)
7. **Output**: Final working code is displayed with execution results

## 📋 Prerequisites

- Python 3.7+
- Anthropic API key
- Flask environment

## 🛠️ Installation

1. **Clone/Navigate to the project directory:**
   ```bash
   cd ai_code_generator
   ```

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up configuration:**
   - Copy `config_example.ini` to `config.ini`
   ```bash
   cp config_example.ini config.ini
   ```
   - Edit `config.ini` and add your Anthropic API key:
   ```ini
   [anthropic]
   api_key = your_actual_api_key_here
   ```
   - Get your API key from: https://console.anthropic.com/

4. **Run the application:**
   ```bash
   python setup_and_run.py
   ```
   or
   ```bash
   python app.py
   ```

5. **Open your browser:**
   - Navigate to the URL shown in the console (default: `http://localhost:5000`)

## ⚙️ Configuration

The application uses a `config.ini` file for all settings. Here are the main configuration sections:

### 🤖 Anthropic Settings
```ini
[anthropic]
api_key = your_anthropic_api_key_here
model = claude-3-opus-20240229
max_tokens_prompt = 1000
max_tokens_code = 2000
max_tokens_fix = 2000
```

### 🔧 Code Generation Settings
```ini
[code_generation]
temperature_prompt = 0.7
temperature_code = 0.5
temperature_fix = 0.3
max_fix_attempts = 5
execution_timeout = 30
```

### 🌐 Flask Settings
```ini
[flask]
host = 0.0.0.0
port = 5000
debug = true
secret_key = your-secret-key-change-this-in-production
```

### 📁 File Settings
```ini
[files]
generated_code_file = ai_code_generator/generated_code.py
final_code_file = ai_code_generator/final_code.py
attempt_code_prefix = ai_code_generator/attempt_
attempt_code_suffix = _code.py
```

### 🛡️ Safety Settings
```ini
[safety]
enable_timeout = true
cleanup_temp_files = true
log_execution = true
```

## 💡 Usage Examples

### Example 1: Calculator with Visualization
- **Static Prompt**: "Create a calculator that can perform basic arithmetic operations"
- **Auto Instruction**: "Add data visualization features to show calculation history as a chart"

### Example 2: Data Analysis Tool
- **Static Prompt**: "Create a script to analyze CSV data"
- **Auto Instruction**: "Generate features for statistical analysis and reporting"

### Example 3: Web Scraper
- **Static Prompt**: "Build a web scraper for extracting product information"
- **Auto Instruction**: "Add functionality to save data in multiple formats and handle rate limiting"

## 🏗️ Project Structure

```
ai_code_generator/
├── app.py                    # Main Flask application
├── config_manager.py         # Configuration management
├── requirements.txt          # Python dependencies
├── config_example.ini        # Configuration template
├── config.ini               # Your configuration (create from example)
├── setup_and_run.py         # Setup and run script
├── README.md                # This file
├── templates/
│   └── index.html           # Web interface
├── generated_code.py        # Initial generated code
├── final_code.py            # Final working code
└── attempt_*_code.py        # Code from each fix attempt
```

## 🔧 Advanced Configuration

### Temperature Settings
- **temperature_prompt** (0.0-1.0): Creativity for prompt generation
- **temperature_code** (0.0-1.0): Creativity for code generation
- **temperature_fix** (0.0-1.0): Precision for error fixing

### Execution Settings
- **max_fix_attempts**: Maximum attempts to fix errors (1-10)
- **execution_timeout**: Code execution timeout in seconds

### Security Settings
- **enable_timeout**: Enable execution timeout
- **cleanup_temp_files**: Clean up temporary files after execution
- **log_execution**: Log execution details

## 🚨 Safety Considerations

- Code runs in a temporary environment
- Configurable execution timeout
- Automatic cleanup of temporary files
- Manual review recommended for generated code
- API key should be kept secure in config.ini

## 🐛 Troubleshooting

### Common Issues

1. **Configuration Error**
   ```
   python setup_and_run.py --validate
   ```
   - Ensure `config.ini` exists (copy from `config_example.ini`)
   - Verify API key is set correctly
   - Check all required sections are present

2. **API Key Error**
   - Ensure API key is valid at console.anthropic.com
   - Check for typos in the API key
   - Verify no extra spaces in config.ini

3. **Import Errors**
   ```bash
   pip install -r requirements.txt
   ```
   - Ensure Python version is 3.7+
   - Check virtual environment is activated

4. **Port Already in Use**
   - Change port in config.ini: `port = 5001`
   - Or find and kill process using the port

### Setup Script Commands

```bash
# Show help
python setup_and_run.py --help

# Validate configuration
python setup_and_run.py --validate

# Show current configuration
python setup_and_run.py --config

# Normal startup
python setup_and_run.py
```

## 📊 API Endpoints

- `GET /` - Main web interface
- `POST /generate` - Generate code from prompts
- `GET /health` - Health check endpoint
- `GET /config` - Show current configuration (debug)

## 🔄 Error Resolution Process

1. **Initial Generation**: Create code from dual prompts
2. **Execution Test**: Run code and capture any errors
3. **Error Analysis**: AI analyzes runtime error messages
4. **Code Fixing**: Generate corrected version
5. **Re-testing**: Execute fixed code
6. **Iteration**: Repeat until success or max attempts reached

## 📈 Performance Metrics

The application tracks:
- Number of fix attempts needed
- Processing time
- Code complexity (lines of code)
- Success/failure status
- Execution output

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Test thoroughly with different configurations
5. Submit a pull request

## 📝 License

This project is open source. Feel free to modify and distribute.

## 🙏 Acknowledgments

- **Anthropic** for Claude Opus AI
- **Bootstrap** for UI components
- **Prism.js** for syntax highlighting
- **Flask** for web framework

## 🔗 Useful Links

- [Anthropic API Documentation](https://docs.anthropic.com/)
- [Claude Opus Model Info](https://www.anthropic.com/news/claude-3-family)
- [Flask Documentation](https://flask.palletsprojects.com/)
- [Bootstrap Documentation](https://getbootstrap.com/docs/)

---

**⚠️ Disclaimer**: This tool generates and executes code automatically. Always review generated code before using in production environments. The developers are not responsible for any issues arising from generated code execution. 