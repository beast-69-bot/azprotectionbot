#!/usr/bin/env python3
"""
========================
SETUP VERIFICATION SCRIPT
========================
This script checks if your environment is properly configured
before running the bot.

Run this before starting the bot to catch configuration issues early.
"""

import os
import sys
import subprocess
from pathlib import Path

# Colors for terminal output
GREEN = '\033[92m'
RED = '\033[91m'
YELLOW = '\033[93m'
BLUE = '\033[94m'
RESET = '\033[0m'

def print_header(text):
    """Print a formatted header"""
    print(f"\n{BLUE}{'='*60}{RESET}")
    print(f"{BLUE}{text.center(60)}{RESET}")
    print(f"{BLUE}{'='*60}{RESET}\n")

def print_success(text):
    """Print success message"""
    print(f"{GREEN}✓ {text}{RESET}")

def print_error(text):
    """Print error message"""
    print(f"{RED}✗ {text}{RESET}")

def print_warning(text):
    """Print warning message"""
    print(f"{YELLOW}⚠ {text}{RESET}")

def check_python_version():
    """Check if Python version is 3.9 or higher"""
    print_header("Checking Python Version")
    
    version = sys.version_info
    version_str = f"{version.major}.{version.minor}.{version.micro}"
    
    if version.major >= 3 and version.minor >= 9:
        print_success(f"Python {version_str} (OK)")
        return True
    else:
        print_error(f"Python {version_str} (Need 3.9+)")
        return False

def check_ffmpeg():
    """Check if FFmpeg is installed"""
    print_header("Checking FFmpeg")
    
    try:
        result = subprocess.run(
            ['ffmpeg', '-version'],
            capture_output=True,
            text=True,
            timeout=5
        )
        
        if result.returncode == 0:
            # Extract version from first line
            first_line = result.stdout.split('\n')[0]
            print_success(f"FFmpeg installed: {first_line}")
            return True
        else:
            print_error("FFmpeg not working properly")
            return False
            
    except FileNotFoundError:
        print_error("FFmpeg not found")
        print_warning("Install with: sudo apt install ffmpeg (Ubuntu)")
        print_warning("            or: sudo dnf install ffmpeg (Amazon Linux)")
        return False
    except Exception as e:
        print_error(f"Error checking FFmpeg: {e}")
        return False

def check_required_files():
    """Check if all required files exist"""
    print_header("Checking Required Files")
    
    required_files = [
        'bot.py',
        'config.py',
        'video_processor.py',
        'requirements.txt',
        '.env'
    ]
    
    all_exist = True
    
    for filename in required_files:
        if os.path.exists(filename):
            print_success(f"{filename} exists")
        else:
            print_error(f"{filename} missing")
            all_exist = False
            
            if filename == '.env':
                print_warning("Copy .env.example to .env and fill in your credentials")
    
    return all_exist

def check_env_variables():
    """Check if .env file has all required variables"""
    print_header("Checking Environment Variables")
    
    if not os.path.exists('.env'):
        print_error(".env file not found")
        return False
    
    # Load .env file
    env_vars = {}
    with open('.env', 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                env_vars[key.strip()] = value.strip()
    
    required_vars = {
        'API_ID': 'Your API ID from my.telegram.org',
        'API_HASH': 'Your API Hash from my.telegram.org',
        'BOT_TOKEN': 'Your bot token from @BotFather',
        'ADMIN_ID': 'Your Telegram user ID',
        'CHANNEL_ID': 'Your channel username or ID',
        'SESSION_NAME': 'Session name (can be any name)'
    }
    
    all_set = True
    
    for var, description in required_vars.items():
        if var in env_vars and env_vars[var]:
            # Check if it's still a placeholder value
            value = env_vars[var]
            if 'your_' in value.lower() or 'here' in value.lower() or value == '12345678':
                print_warning(f"{var} is set but looks like a placeholder")
                print(f"         {description}")
                all_set = False
            else:
                print_success(f"{var} is set")
        else:
            print_error(f"{var} is missing")
            print(f"         {description}")
            all_set = False
    
    return all_set

def check_python_packages():
    """Check if required Python packages are installed"""
    print_header("Checking Python Packages")
    
    required_packages = [
        'pyrogram',
        'tgcrypto',
        'dotenv'
    ]
    
    all_installed = True
    
    for package in required_packages:
        try:
            __import__(package)
            print_success(f"{package} installed")
        except ImportError:
            print_error(f"{package} not installed")
            all_installed = False
    
    if not all_installed:
        print_warning("\nInstall missing packages with:")
        print_warning("pip install -r requirements.txt")
    
    return all_installed

def check_permissions():
    """Check file permissions"""
    print_header("Checking Permissions")
    
    files_to_check = ['bot.py', 'config.py', 'video_processor.py']
    
    all_ok = True
    
    for filename in files_to_check:
        if os.path.exists(filename):
            if os.access(filename, os.R_OK):
                print_success(f"{filename} is readable")
            else:
                print_error(f"{filename} is not readable")
                all_ok = False
        else:
            print_warning(f"{filename} not found")
    
    return all_ok

def check_disk_space():
    """Check available disk space"""
    print_header("Checking Disk Space")
    
    try:
        stat = os.statvfs('.')
        # Available space in GB
        available_gb = (stat.f_bavail * stat.f_frsize) / (1024**3)
        
        if available_gb >= 5:
            print_success(f"Available disk space: {available_gb:.2f} GB")
            return True
        elif available_gb >= 2:
            print_warning(f"Available disk space: {available_gb:.2f} GB (Low)")
            print_warning("Recommended: 5+ GB for smooth operation")
            return True
        else:
            print_error(f"Available disk space: {available_gb:.2f} GB (Too low)")
            print_error("Need at least 2 GB free space")
            return False
            
    except Exception as e:
        print_warning(f"Could not check disk space: {e}")
        return True

def main():
    """Run all checks"""
    print(f"\n{BLUE}{'='*60}")
    print(f"  TELEGRAM VIDEO PROTECTION BOT - SETUP VERIFICATION")
    print(f"{'='*60}{RESET}\n")
    
    checks = [
        ("Python Version", check_python_version),
        ("FFmpeg", check_ffmpeg),
        ("Required Files", check_required_files),
        ("Environment Variables", check_env_variables),
        ("Python Packages", check_python_packages),
        ("File Permissions", check_permissions),
        ("Disk Space", check_disk_space),
    ]
    
    results = {}
    
    for name, check_func in checks:
        try:
            results[name] = check_func()
        except Exception as e:
            print_error(f"Error during {name} check: {e}")
            results[name] = False
    
    # Summary
    print_header("SUMMARY")
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for name, result in results.items():
        status = f"{GREEN}PASS{RESET}" if result else f"{RED}FAIL{RESET}"
        print(f"{name:.<40} {status}")
    
    print(f"\n{BLUE}{'='*60}{RESET}")
    
    if passed == total:
        print(f"{GREEN}✓ All checks passed! You're ready to run the bot.{RESET}")
        print(f"\n{BLUE}Start the bot with:{RESET}")
        print(f"  python3 bot.py")
        print(f"\n{BLUE}Or run as service:{RESET}")
        print(f"  sudo systemctl start telegram-video-bot")
        return 0
    else:
        print(f"{RED}✗ {total - passed} check(s) failed. Please fix the issues above.{RESET}")
        print(f"\n{YELLOW}Common fixes:{RESET}")
        print(f"  • Install FFmpeg: sudo apt install ffmpeg")
        print(f"  • Install packages: pip install -r requirements.txt")
        print(f"  • Configure .env: cp .env.example .env && nano .env")
        return 1

if __name__ == "__main__":
    try:
        exit_code = main()
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print(f"\n\n{YELLOW}Interrupted by user{RESET}")
        sys.exit(1)
