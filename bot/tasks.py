"""
Google Meet Recording Bot with Django API Integration

This solution combines:
1. A Selenium-based bot that joins Google Meet and records the session
2. A Django REST API endpoint to control the bot
3. Proper logging and error handling
"""

# Standard library imports
import os
import time
import tempfile
import subprocess
import logging
import random
import threading
from datetime import datetime

# Django imports
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt

# Django REST Framework imports
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework import status

# Selenium imports
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

# Set up logging
logger = logging.getLogger(__name__)
def generate_unique_profile_path():
    """Generate a unique temporary directory for Chrome profile"""
    return tempfile.mkdtemp(prefix=f"chrome_profile_{int(time.time())}_{random.randint(1000, 9999)}_")

class MeetBot:
    """Google Meet recording bot using Selenium"""
    
    def __init__(self, email, password, meeting_link, filename, duration, headless=False):
        self.email = email
        self.password = password
        self.meeting_link = meeting_link
        self.filename = filename
        self.headless = headless
        self.duration = duration
        self.driver = None
        self.recording_thread = None
        self.should_stop = False
        self.participants_check_count =0
        self.print_status("🔧 Bot initialized with provided credentials and configurations.")
        self.recording_thread = None
        self.ffmpeg_process = None
        
    def print_status(self, message):
        print(f"[BOT STATUS] {message}")

    def initialize_driver(self):
        """Initialize Chrome WebDriver with proper options for local and live"""
        options = webdriver.ChromeOptions()

        # Headless browser if needed
        if self.headless:
            options.add_argument("--headless=new")

        # Disable popups and permissions
        options.add_argument("--disable-notifications")
        options.add_argument("--use-fake-ui-for-media-stream")
        options.add_argument("--use-fake-device-for-media-stream")

        # Prevent Selenium detection
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option("useAutomationExtension", False)

        # For screen sharing simulation
        options.add_argument("--auto-select-desktop-capture-source=Entire screen")

        # ✅ Avoid "user-data-dir already in use" error
        user_data_dir = generate_unique_profile_path()
        options.add_argument(f"--user-data-dir={user_data_dir}")

        # Optional: Disable GPU for headless servers
        options.add_argument("--disable-gpu")

        # Optional: Set no-sandbox for CI/CD or restricted environments
        options.add_argument("--no-sandbox")

        # Start the driver
        self.driver = webdriver.Chrome(options=options)

        # Maximize only if not headless (some systems don’t support maximize in headless mode)
        if not self.headless:
            self.driver.maximize_window()

    def login_to_gmail(self):
        """Log into Gmail account"""
        logger.info("Logging into Gmail...")
        self.driver.get("https://mail.google.com")
        
        try:
            sign_in_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.LINK_TEXT, "Sign in"))
            )
            sign_in_button.click()
            logger.info("Clicked on 'Sign in' from Workspace landing page")
            # Enter email
            email_field = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.ID, "identifierId"))
            )
            email_field.send_keys(self.email)
            self.driver.find_element(By.ID, "identifierNext").click()
            time.sleep(2)  # give time for transition

            # Enter password
            password_field = WebDriverWait(self.driver, 20).until(
                EC.presence_of_element_located((By.NAME, "Passwd"))
            )
            password_field.send_keys(self.password)
            self.driver.find_element(By.ID, "passwordNext").click()
            
            # Wait for login to complete
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Inbox"))
            )
            logger.info("Successfully logged into Gmail")
            return True
            
        except TimeoutException:
            logger.error("Timeout during Gmail login")
            return False
    
    def start_recording(self):
        """Start recording the screen with audio"""
        self.print_status("Starting screen recording with audio...")
        try:
            # Ensure filename has .mp4 extension
            if not self.filename.lower().endswith('.mp4'):
                self.filename += '.mp4'
                
            # Get absolute path for output file
            output_path = os.path.abspath(self.filename)
            self.print_status(f"Output will be saved to: {output_path}")
            
            # First, try to detect available audio devices
            def get_audio_devices():
                try:
                    ffmpeg_path = 'ffmpeg'  # Assuming it's in PATH
                    result = subprocess.run(
                        [ffmpeg_path, '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
                        stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
                    )
                    output = result.stderr
                    audio_devices = []
                    for line in output.split('\n'):
                        if 'audio' in line.lower() and 'dshow' in line.lower():
                            device = line.split('"')[1]
                            audio_devices.append(device)
                    return audio_devices
                except:
                    return []

            available_devices = get_audio_devices()
            self.print_status(f"Available audio devices: {available_devices}")

            # Screen capture command base
            ffmpeg_cmd = [
                'ffmpeg',
                '-f', 'gdigrab',
                '-framerate', '30',
                '-video_size', '1920x1080',
                '-i', 'desktop',
            ]

            # Try different recording methods in order of preference
            try_methods = []

            # Method 1: Try with both system audio and microphone if available
            if len(available_devices) >= 2:
                try_methods.append(
                    ffmpeg_cmd + [
                        '-f', 'dshow',
                        '-i', f'audio={available_devices[0]}',
                        '-f', 'dshow',
                        '-i', f'audio={available_devices[1]}',
                        '-filter_complex', '[1:a][2:a]amix=inputs=2[a]',
                        '-map', '0:v',
                        '-map', '[a]',
                        '-c:v', 'libx264',
                        '-preset', 'ultrafast',
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac',
                        '-b:a', '192k',
                        '-movflags', '+faststart',
                        '-y',
                        output_path
                    ]
                )

            # Method 2: Try with just one audio device if available
            if available_devices:
                try_methods.append(
                    ffmpeg_cmd + [
                        '-f', 'dshow',
                        '-i', f'audio={available_devices[0]}',
                        '-c:v', 'libx264',
                        '-preset', 'ultrafast',
                        '-pix_fmt', 'yuv420p',
                        '-c:a', 'aac',
                        '-b:a', '192k',
                        '-movflags', '+faststart',
                        '-y',
                        output_path
                    ]
                )

            # Method 3: Fallback to video only
            try_methods.append(
                ffmpeg_cmd + [
                    '-c:v', 'libx264',
                    '-preset', 'ultrafast',
                    '-pix_fmt', 'yuv420p',
                    '-an',  # No audio
                    '-movflags', '+faststart',
                    '-y',
                    output_path
                ]
            )

            last_error = None
            success = False
            
            for method in try_methods:
                self.print_status(f"Trying command: {' '.join(method)}")
                
                try:
                    self.ffmpeg_process = subprocess.Popen(
                        method,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        shell=True
                    )
                    
                    # Wait briefly to ensure ffmpeg started
                    time.sleep(2)
                    
                    if self.ffmpeg_process.poll() is not None:
                        error = self.ffmpeg_process.stderr.read().decode('utf-8', errors='ignore')
                        last_error = error
                        self.print_status(f"Attempt failed: {error}")
                        if self.ffmpeg_process:
                            self.ffmpeg_process.kill()
                        continue
                    
                    success = True
                    break
                    
                except Exception as e:
                    last_error = str(e)
                    self.print_status(f"Error during attempt: {last_error}")
                    continue
            
            if not success:
                raise Exception(f"All recording attempts failed. Last error: {last_error}")
            
            self.recording_started = True
            self.print_status(f"Screen recording started successfully to {output_path}")
            
        except Exception as e:
            self.print_status(f"Error starting recording: {str(e)}")
            if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process:
                self.ffmpeg_process.kill()
            raise
    
    
    def monitor_recording(self):
        """Monitor the recording process and meeting status"""
        self.print_status(f"Monitoring recording for {self.duration} minutes...")
        start_time = time.time()
        end_time = start_time + (self.duration * 60)
        last_participant_check = 0
        
        try:
            while time.time() < end_time and not self.should_stop:
                current_time = time.time()
                elapsed = int(current_time - start_time)
                remaining = int(end_time - current_time)
                
                # Check participants every 30 seconds after first 2 minutes
                if current_time - last_participant_check > 30 and elapsed > 20:  # Reduced from 120 to 20 for testing
                    last_participant_check = current_time
                    if not self.check_participants():
                        self.participants_check_count += 1
                        self.print_status(f"No participants detected ({self.participants_check_count}/4 checks)")
                        
                        # Leave if no participants for 2 checks (1 minute)
                        if self.participants_check_count >= 2:
                            self.print_status("No other participants for 1 minute. Ending recording.")
                            self.should_stop = True
                            break
                    else:
                        self.participants_check_count = 0
                
                self.print_status(f"Recording... Elapsed: {elapsed}s | Remaining: {remaining}s")
                time.sleep(10)
            
            # Properly stop recording
            self.print_status("Stopping recording process...")
            if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
                try:
                    # First try graceful termination
                    self.print_status("Attempting graceful FFmpeg shutdown...")
                    
                    # Send 'q' to stdin (works for interactive FFmpeg)
                    try:
                        self.ffmpeg_process.stdin.write(b'q\n')
                        self.ffmpeg_process.stdin.flush()
                    except:
                        pass
                    
                    # Wait with timeout
                    try:
                        self.print_status("Waiting up to 15 seconds for FFmpeg to finish...")
                        self.ffmpeg_process.wait(timeout=15)
                    except subprocess.TimeoutExpired:
                        self.print_status("Graceful shutdown failed, terminating FFmpeg...")
                        self.ffmpeg_process.terminate()
                        try:
                            self.ffmpeg_process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            self.print_status("Forcing FFmpeg to close...")
                            self.ffmpeg_process.kill()
                    
                    # Verify output file
                    if os.path.exists(self.filename):
                        file_size = os.path.getsize(self.filename) / (1024 * 1024)  # in MB
                        self.print_status(f"Recording saved successfully! File size: {file_size:.2f} MB")
                        
                        # Verify file is playable
                        try:
                            subprocess.run(
                                [r"C:\ProgramData\chocolatey\bin\ffmpeg.exe", "-i", self.filename],
                                stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE,
                                timeout=5
                            )
                            self.print_status("Video file appears to be valid")
                        except:
                            self.print_status("Warning: Video file might be corrupted")
                    else:
                        raise Exception("Output file was not created")
                        
                except Exception as e:
                    self.print_status(f"Error stopping recording: {str(e)}")
                    raise
            
            # Save recording info
            info_file = f"{os.path.splitext(self.filename)[0]}_info.txt"
            with open(info_file, 'w') as f:
                f.write(f"Meeting: {self.meeting_link}\n")
                f.write(f"Duration: {int(time.time() - start_time)} seconds\n")
                f.write(f"Ended at: {datetime.now().isoformat()}\n")
                f.write(f"Participants left early: {self.participants_check_count >= 2}\n")
                f.write(f"Video file: {os.path.abspath(self.filename)}\n")
                if os.path.exists(self.filename):
                    f.write(f"File size: {os.path.getsize(self.filename) / (1024 * 1024):.2f} MB\n")
            
            self.print_status(f"Recording info saved to {info_file}")
            self.print_status("Recording process completed successfully")
            
        except Exception as e:
            self.print_status(f"Error during recording monitoring: {str(e)}")
            if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process:
                self.ffmpeg_process.kill()
            raise
    
    
    
    
    def join_meeting(self):
        """Join the Google Meet session silently"""
        self.print_status(f"Joining meeting: {self.meeting_link}")
        self.driver.get(self.meeting_link)

        try:

            # Turn off camera and mic before joining
            self.print_status("Turning off camera and mic...")

            for label in ['camera', 'microphone']:
                try:
                    selectors = [
                        f"div[aria-label*='Turn off {label}']",
                        f"div[aria-label*='Turn on {label}']",
                        f"div[jsname*='toggle{label.capitalize()}']",
                        f"button[aria-label*='{label}']"
                    ]
                    for selector in selectors:
                        try:
                            btn = WebDriverWait(self.driver, 3).until(
                                EC.element_to_be_clickable((By.CSS_SELECTOR, selector))
                            )
                            btn.click()
                            time.sleep(0.5)
                            self.print_status(f"{label.capitalize()} turned off")
                            break
                        except:
                            continue
                except Exception as e:
                    self.print_status(f"Could not turn off {label}: {str(e)}")

            # Click join/ask button
            self.print_status("Looking for join/ask button...")
            join_selectors = [
                ("xpath", "//span[contains(text(), 'Join now')]"),
                ("xpath", "//span[contains(text(), 'Ask to join')]"),
                ("xpath", "//button[contains(text(), 'Join now')]"),
                ("xpath", "//button[contains(text(), 'Ask to join')]"),
                ("css", "button[jscontroller][jsaction*='click'] span.UywwFc-vQzf8d")
            ]

            joined = False
            for by, value in join_selectors:
                try:
                    locator = (By.XPATH, value) if by == "xpath" else (By.CSS_SELECTOR, value)
                    join_btn = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable(locator)
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", join_btn)
                    time.sleep(0.5)
                    try:
                        join_btn.click()
                    except:
                        self.driver.execute_script("arguments[0].click();", join_btn)
                    self.print_status(f"Clicked join using {by}: {value}")
                    joined = True
                    break
                except Exception as e:
                    self.print_status(f"Selector failed: {value} -> {e}")

            # Fallback: click any button with join/ask text
            if not joined:
                try:
                    buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    for button in buttons:
                        if any(keyword in button.text.lower() for keyword in ["join", "ask"]):
                            try:
                                button.click()
                                joined = True
                                break
                            except:
                                self.driver.execute_script("arguments[0].click();", button)
                                joined = True
                                break
                except Exception as e:
                    self.print_status(f"Fallback failed: {e}")

            if joined:
                self.print_status("Successfully joined the meeting")
                return True
            else:
                self.print_status("Join button not found")
                return False

        except TimeoutException:
            self.print_status("Meeting load timeout")
            return False
        except Exception as e:
            self.print_status(f"Error: {str(e)}")
            return False

   
    def check_participants(self):
        """Check if there are other participants in the meeting"""
        try:
            # Try different ways to find participants count
            participants_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "div[aria-label*='participant'], div[jsname*='participant']"
            )
            
            # If we can't find specific elements, look for people indicators
            if not participants_elements:
                participants_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "div[aria-label*='person'], div[jsname*='person']"
                )
            
            # Count only visible participant elements
            visible_participants = [el for el in participants_elements if el.is_displayed()]
            
            self.print_status(f"Participants check: Found {len(visible_participants)} possible participants")
            return len(visible_participants) > 1  # More than just ourselves
            
        except Exception as e:
            self.print_status(f"Error checking participants: {str(e)}")
            return True  # Assume someone is there if we can't check

    def run(self):
        """Main bot execution flow"""
        try:
            self.print_status("Starting Google Meet Bot...")
            self.initialize_driver()
            
            # Start recording immediately after driver initialization
            self.start_recording()
            
            if not self.login_to_gmail():
                raise Exception("Failed to login to Google account")
                
            if not self.join_meeting():
                raise Exception("Failed to join meeting")
                
            # Start monitoring in a separate thread
            self.print_status("Starting monitoring thread...")
            self.recording_thread = threading.Thread(
                target=self.monitor_recording
            )
            self.recording_thread.start()
            
            # Wait for monitoring to complete
            self.print_status("Waiting for recording to complete...")
            self.recording_thread.join()
            self.print_status("Recording completed successfully")
            
        except Exception as e:
            self.print_status(f"Error in bot execution: {str(e)}")
            raise
        finally:
            self.stop()

    def stop(self):
        """Stop the monitoring and cleanup"""
        self.print_status("Stopping bot...")
        self.should_stop = True
        
        if self.recording_thread and self.recording_thread.is_alive():
            self.print_status("Waiting for monitoring thread to finish...")
            self.recording_thread.join(timeout=5)
        
        self.cleanup()
        self.print_status("Bot stopped successfully")

    def cleanup(self):
        """Clean up resources"""
        if self.driver:
            try:
                self.print_status("Closing browser...")
                self.driver.quit()
                self.print_status("Browser closed")
            except Exception as e:
                self.print_status(f"Error closing browser: {str(e)}")
        
        if self.ffmpeg_process and self.ffmpeg_process.poll() is None:
            try:
                self.print_status("Terminating ffmpeg process...")
                self.ffmpeg_process.terminate()
                try:
                    self.ffmpeg_process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    self.ffmpeg_process.kill()
                self.print_status("ffmpeg process terminated")
            except Exception as e:
                self.print_status(f"Error terminating ffmpeg process: {str(e)}")

