import os
import glob
import subprocess
import tempfile
import traceback
import logging
import re
import time
import json
from datetime import date, datetime
from flask import Flask, render_template, request, jsonify
from werkzeug.utils import secure_filename
from openai import OpenAI
import anthropic
from config_manager import get_config

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load configuration
try:
    config = get_config()
    logger.info("Configuration loaded successfully")
except Exception as e:
    logger.error(f"Error loading configuration: {e}")
    exit(1)

app = Flask(__name__)
app.secret_key = config.get_flask_secret_key()
app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024

# --- Provider Registry ---
PROVIDERS = {
    'moonshot': {
        'name': 'Moonshot AI',
        'base_url': 'https://api.moonshot.ai/v1',
        'type': 'openai',
        'models': [
            {'id': 'kimi-k2-thinking', 'name': 'Kimi K2 Thinking', 'context': '262k'},
            {'id': 'kimi-k2-thinking-turbo', 'name': 'Kimi K2 Thinking Turbo', 'context': '262k'},
            {'id': 'kimi-k2.5', 'name': 'Kimi K2.5', 'context': '262k'},
            {'id': 'moonshot-v1-128k', 'name': 'Moonshot V1 128K', 'context': '128k'},
            {'id': 'moonshot-v1-32k', 'name': 'Moonshot V1 32K', 'context': '32k'},
        ]
    },
    'anthropic': {
        'name': 'Anthropic',
        'type': 'anthropic',
        'models': [
            {'id': 'claude-sonnet-4-6-20250725', 'name': 'Claude Sonnet 4.6', 'context': '200k'},
            {'id': 'claude-opus-4-6-20250725', 'name': 'Claude Opus 4.6', 'context': '1M'},
            {'id': 'claude-sonnet-4-20250514', 'name': 'Claude Sonnet 4', 'context': '200k'},
            {'id': 'claude-opus-4-20250514', 'name': 'Claude Opus 4', 'context': '200k'},
            {'id': 'claude-haiku-4-5-20251001', 'name': 'Claude Haiku 4.5', 'context': '200k'},
        ]
    },
    'openai': {
        'name': 'OpenAI',
        'base_url': 'https://api.openai.com/v1',
        'type': 'openai',
        'models': [
            {'id': 'gpt-4o', 'name': 'GPT-4o', 'context': '128k'},
            {'id': 'gpt-4o-mini', 'name': 'GPT-4o Mini', 'context': '128k'},
            {'id': 'gpt-4.1', 'name': 'GPT-4.1', 'context': '1M'},
            {'id': 'gpt-4.1-mini', 'name': 'GPT-4.1 Mini', 'context': '1M'},
            {'id': 'o3-mini', 'name': 'O3 Mini', 'context': '200k'},
        ]
    }
}

# Default server client (Moonshot)
default_client = None
try:
    api_key = config.get_moonshot_api_key()
    if api_key:
        default_client = OpenAI(api_key=api_key, base_url='https://api.moonshot.ai/v1')
        logger.info("Default Moonshot AI client initialized")
except Exception as e:
    logger.error(f"Error initializing default client: {e}")


def call_ai(provider, api_key, model, system_prompt, user_prompt, max_tokens=10000, temperature=1.0):
    """Unified AI call supporting all providers."""
    provider_info = PROVIDERS.get(provider)
    if not provider_info:
        return None, f"Unknown provider: {provider}"

    try:
        if provider_info['type'] == 'openai':
            base_url = provider_info.get('base_url', 'https://api.openai.com/v1')
            client = OpenAI(api_key=api_key, base_url=base_url)

            kwargs = {
                'model': model,
                'max_tokens': max_tokens,
                'messages': [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ]
            }
            # Some models (kimi-k2.5, kimi-k2-thinking) require temperature=1
            if not model.startswith(('o1', 'o3')):
                kwargs['temperature'] = temperature

            response = client.chat.completions.create(**kwargs)
            text = response.choices[0].message.content
            return text if text else None, None

        elif provider_info['type'] == 'anthropic':
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model=model,
                max_tokens=max_tokens,
                system=system_prompt,
                messages=[{"role": "user", "content": user_prompt}]
            )
            text = response.content[0].text if response.content else None
            return text, None

    except Exception as e:
        logger.error(f"AI call failed ({provider}/{model}): {str(e)}")
        return None, str(e)


# --- System Prompts ---
STRATEGY_SYSTEM = """You are an expert quantitative trading strategist and Python developer.
Your job is to generate a DETAILED, PRECISE trading strategy specification that can be directly implemented in code.

Rules for your output:
- Define EXACT entry conditions (e.g., "Buy when 20-period SMA crosses above 50-period SMA AND RSI(14) < 70")
- Define EXACT exit conditions (e.g., "Sell when price drops 2% below entry OR RSI(14) > 80")
- Specify exact indicator parameters (periods, thresholds, multipliers)
- Include stop-loss and take-profit rules with exact percentages
- Define position sizing rules
- Handle both LONG and SHORT positions for futures
- Be quantitative — no vague language like "when trend is strong"
- Every rule must be implementable as a Python if-statement"""

CODE_SYSTEM = """You are a senior Python developer specializing in algorithmic trading and backtesting.

CRITICAL RULES:
1. Output ONLY valid, executable Python code. No explanations, no markdown.
2. The code must run end-to-end without any user modification.
3. Use proper imports at the top of the file.
4. All configurable parameters (fees, position size, periods) must be defined as constants at the top.
5. Include comprehensive error handling (try/except for file loading, data parsing).
6. The code MUST produce output — print trade logs, performance metrics, and summary statistics.
7. If using the backtesting library, the Strategy class must properly implement init() and next() methods.
8. Column mapping: the CSV has columns (time, open_price, close_price, high_price, low_price, coin_volume) — rename them to match whatever library you use (Open, High, Low, Close, Volume).
9. Parse dates robustly — try multiple formats if needed.
10. Save any plots to files (plot.html or plot.png) — NEVER call show() or open a display window.
11. Do NOT use placeholder comments like "# TODO" or "# implement here" — write the FULL implementation.
12. Test edge cases: what if there are no trades? What if data is insufficient for indicators?"""

FIX_SYSTEM = """You are an expert Python debugger. You fix runtime errors in trading/backtesting code.

RULES:
1. Return ONLY the complete fixed Python code — no explanations, no markdown blocks.
2. Fix the specific error while preserving all other functionality.
3. If a library is missing, replace it with an equivalent or implement the functionality manually.
4. If a column name is wrong, check the CSV format and fix the mapping.
5. If an indicator calculation fails, check for sufficient data length.
6. Preserve ALL print statements and output formatting.
7. The fixed code must be the COMPLETE script, not just the changed parts."""


# --- Rate Limiting (only for server default key) ---
RATE_LIMIT_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'rate_limit.json')

def get_daily_usage():
    today = str(date.today())
    try:
        with open(RATE_LIMIT_FILE, 'r') as f:
            data = json.load(f)
        if data.get('date') != today:
            return 0
        return data.get('count', 0)
    except (FileNotFoundError, json.JSONDecodeError):
        return 0

def increment_usage():
    today = str(date.today())
    try:
        with open(RATE_LIMIT_FILE, 'r') as f:
            data = json.load(f)
        if data.get('date') != today:
            data = {'date': today, 'count': 0}
    except (FileNotFoundError, json.JSONDecodeError):
        data = {'date': today, 'count': 0}
    data['count'] += 1
    with open(RATE_LIMIT_FILE, 'w') as f:
        json.dump(data, f)
    return data['count']

def check_rate_limit():
    max_requests = config.get_max_requests_per_day()
    current_usage = get_daily_usage()
    return current_usage < max_requests, max_requests - current_usage, max_requests


# --- Utilities ---
def extract_code(text):
    """Extract Python code from markdown code blocks or raw text."""
    match = re.search(r'```python\s*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    match = re.search(r'```\s*\n(.*?)```', text, re.DOTALL)
    if match:
        return match.group(1).strip()
    return text.strip()

def run_python_code(code):
    """Run Python code using temporary files"""
    temp_filename = None
    try:
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as temp_file:
            temp_file.write(code)
            temp_filename = temp_file.name

        timeout = config.get_execution_timeout() if config.is_timeout_enabled() else None
        result = subprocess.run(
            ['python', temp_filename],
            capture_output=True, text=True, timeout=timeout, cwd=os.getcwd()
        )

        try:
            os.unlink(temp_filename)
        except:
            pass

        if result.returncode != 0:
            return False, result.stderr
        if result.stderr and any(t in result.stderr.lower() for t in ['error:', 'exception:', 'traceback', 'failed']):
            return False, result.stderr
        return True, result.stdout

    except subprocess.TimeoutExpired:
        if temp_filename and os.path.exists(temp_filename):
            try: os.unlink(temp_filename)
            except: pass
        return False, f"Code execution timed out ({config.get_execution_timeout()} seconds)"
    except Exception as e:
        if temp_filename and os.path.exists(temp_filename):
            try: os.unlink(temp_filename)
            except: pass
        return False, f"Error running code: {str(e)}"

def save_code_to_file(code, filename=None):
    good_codes_dir = "good_codes"
    if not os.path.exists(good_codes_dir):
        os.makedirs(good_codes_dir)
    if filename is None:
        filename = f"working_strategy_{int(time.time())}.py"
    try:
        filepath = os.path.join(good_codes_dir, filename)
        with open(filepath, 'w') as f:
            f.write(code)
        return True, filepath
    except Exception as e:
        return False, str(e)


# --- Routes ---

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/providers', methods=['GET'])
def list_providers():
    """Return available providers and their models."""
    result = {}
    for key, info in PROVIDERS.items():
        result[key] = {
            'name': info['name'],
            'models': info['models']
        }
    return jsonify(result)

@app.route('/rate-limit', methods=['GET'])
def rate_limit_status():
    allowed, remaining, total = check_rate_limit()
    return jsonify({
        'allowed': allowed, 'remaining': remaining,
        'total': total, 'used': total - remaining, 'date': str(date.today())
    })

REQUIRED_CSV_HEADERS = {'time', 'open_price', 'close_price', 'high_price', 'low_price', 'coin_volume'}

@app.route('/csv-files', methods=['GET'])
def list_csv_files():
    csv_paths = glob.glob(os.path.join(os.getcwd(), '*.csv'))
    groups = {}
    for filepath in sorted(csv_paths):
        filename = os.path.basename(filepath)
        size_mb = round(os.path.getsize(filepath) / (1024 * 1024), 1)
        if filename.startswith('uploaded_'):
            pair = 'Uploaded'
            timeframe = filename.replace('uploaded_', '').replace('.csv', '')
        else:
            parts = filename.replace('.csv', '').split('_')
            if len(parts) >= 2:
                timeframe = parts[-1]
                pair = '_'.join(parts[:-1]).upper()
            else:
                pair, timeframe = 'Other', ''
        if pair not in groups:
            groups[pair] = []
        groups[pair].append({'filename': filename, 'timeframe': timeframe, 'size_mb': size_mb})

    result = [{'pair': p, 'files': groups[p]} for p in sorted(groups.keys()) if p != 'Uploaded']
    if 'Uploaded' in groups:
        result.append({'pair': 'Uploaded', 'files': groups['Uploaded']})
    return jsonify({'groups': result})

@app.route('/upload-csv', methods=['POST'])
def upload_csv():
    if 'csv_file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    file = request.files['csv_file']
    if not file.filename or not file.filename.lower().endswith('.csv'):
        return jsonify({'error': 'File must be a .csv file'}), 400

    first_line = file.readline().decode('utf-8').strip()
    file.seek(0)
    headers = set(h.strip().lower() for h in first_line.split(','))
    if not REQUIRED_CSV_HEADERS.issubset(headers):
        missing = REQUIRED_CSV_HEADERS - headers
        return jsonify({'error': f'Missing required columns: {", ".join(sorted(missing))}'}), 400

    safe_name = secure_filename(file.filename)
    if not safe_name.startswith('uploaded_'):
        safe_name = f'uploaded_{safe_name}'
    save_path = os.path.join(os.getcwd(), safe_name)
    file.save(save_path)
    size_mb = round(os.path.getsize(save_path) / (1024 * 1024), 1)
    return jsonify({'filename': safe_name, 'size_mb': size_mb})

@app.route('/generate', methods=['POST'])
def generate():
    logger.info("New code generation request received")

    try:
        data = request.get_json()
        static_prompt = data.get('static_prompt', '').strip()
        auto_instruction = data.get('auto_instruction', '').strip()
        csv_file = data.get('csv_file', 'binance_solusdt_1h.csv').strip()

        # Provider settings from user
        provider = data.get('provider', 'moonshot').strip()
        user_api_key = data.get('api_key', '').strip()
        model = data.get('model', '').strip()
        using_own_key = bool(user_api_key)

        # If no user key, use server default (Moonshot) with rate limiting
        if not using_own_key:
            allowed, remaining, total = check_rate_limit()
            if not allowed:
                return jsonify({
                    'error': f'Demo limit reached ({total}/{total}). Add your own API key for unlimited use.',
                    'rate_limited': True
                }), 429
            # Force to server default
            provider = 'moonshot'
            user_api_key = config.get_moonshot_api_key()
            if not model:
                model = config.get_moonshot_model()

        if not model:
            # Default model per provider
            models = PROVIDERS.get(provider, {}).get('models', [])
            model = models[0]['id'] if models else ''

        if not static_prompt or not auto_instruction:
            return jsonify({'error': 'Both static prompt and auto instruction are required'}), 400

        if not using_own_key:
            increment_usage()

        logger.info(f"Provider: {provider}, Model: {model}, Own key: {using_own_key}")

        # Step 1: Generate strategy prompt
        logger.info("Step 1 - Generating strategy prompt")
        strategy_text, err = call_ai(
            provider, user_api_key, model, STRATEGY_SYSTEM,
            f"Generate a detailed, implementable trading strategy specification based on this instruction:\n\n{auto_instruction}\n\nOutput ONLY the strategy specification with numbered rules. No code, no markdown, just the precise trading rules."
        )
        if err or not strategy_text:
            return jsonify({'error': f'Strategy prompt generation failed: {err or "empty response"}'}), 500

        # Step 2: Create final combined prompt
        logger.info("Step 2 - Creating final combined prompt")
        final_prompt = static_prompt.replace("[[csv_file]]", csv_file).replace("[[strategy_prompt]]", strategy_text)

        # Step 3: Generate Python code
        logger.info("Step 3 - Generating Python code")
        code_text, err = call_ai(provider, user_api_key, model, CODE_SYSTEM, final_prompt)
        if err or not code_text:
            return jsonify({'error': f'Code generation failed: {err or "empty response"}'}), 500

        code = extract_code(code_text)

        # Step 4: Run code and fix errors iteratively
        max_attempts = config.get_max_fix_attempts()
        attempt = 0
        execution_log = []
        execution_log.append(f"Starting execution (max {max_attempts} attempts)...")

        while attempt < max_attempts:
            attempt += 1
            execution_log.append(f"--- Attempt {attempt}/{max_attempts} ---")

            success, output = run_python_code(code)

            if success:
                execution_log.append("Code executed successfully!")

                timestamp = int(time.time())
                final_filename = f"working_strategy_{timestamp}.py"
                save_success, save_path = save_code_to_file(code, final_filename)

                # Check for plot.html
                plot_html_content = None
                plot_file_path = os.path.join(os.getcwd(), 'plot.html')
                if os.path.exists(plot_file_path):
                    try:
                        with open(plot_file_path, 'r', encoding='utf-8') as f:
                            plot_html_content = f.read()
                        execution_log.append("plot.html generated and loaded")
                    except Exception as e:
                        execution_log.append(f"Error reading plot.html: {str(e)}")

                _, remaining_after, total_after = check_rate_limit()

                return jsonify({
                    'success': True,
                    'strategy_prompt': strategy_text,
                    'final_prompt': final_prompt,
                    'final_code': code,
                    'execution_log': execution_log,
                    'output': output,
                    'attempts': attempt,
                    'local_filename': f"good_codes/{final_filename}" if save_success else None,
                    'working_directory': os.getcwd(),
                    'models_used': {'provider': provider, 'model': model},
                    'plot_html': plot_html_content,
                    'rate_limit': {'remaining': remaining_after, 'total': total_after}
                })
            else:
                execution_log.append(f"Runtime error: {output}")
                if attempt < max_attempts:
                    execution_log.append("Attempting to fix...")
                    fix_prompt = f"Fix this Python code. The error and code are below.\n\nERROR:\n{output}\n\nCODE:\n{code}\n\nReturn ONLY the complete fixed Python code."
                    fixed_text, fix_err = call_ai(provider, user_api_key, model, FIX_SYSTEM, fix_prompt)
                    if fixed_text and fixed_text != code:
                        code = extract_code(fixed_text)
                        execution_log.append("Error fix attempted")
                    else:
                        execution_log.append(f"Could not fix: {fix_err or 'same code returned'}")
                        break

        execution_log.append(f"Could not resolve errors after {attempt} attempts")
        _, remaining_after, total_after = check_rate_limit()

        return jsonify({
            'success': False,
            'strategy_prompt': strategy_text,
            'final_prompt': final_prompt,
            'final_code': code,
            'execution_log': execution_log,
            'error': f"Could not resolve runtime errors after {attempt} attempts",
            'attempts': attempt,
            'local_filename': None,
            'working_directory': os.getcwd(),
            'models_used': {'provider': provider, 'model': model},
            'plot_html': None,
            'rate_limit': {'remaining': remaining_after, 'total': total_after}
        })

    except Exception as e:
        logger.error(f"Server error: {str(e)}")
        logger.error(traceback.format_exc())
        return jsonify({'error': f'Server error: {str(e)}'}), 500

if __name__ == '__main__':
    logger.info("Starting Trading Algo Generator...")
    logger.info(f"Server: http://{config.get_flask_host()}:{config.get_flask_port()}")
    logger.info(f"Default provider: Moonshot ({config.get_moonshot_model()})")
    app.run(debug=config.get_flask_debug(), host=config.get_flask_host(), port=config.get_flask_port())
