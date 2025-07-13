import os
import json
import time
import logging
import threading
import subprocess
import tempfile
import cv2
import speech_recognition as sr
from datetime import datetime
from collections import defaultdict
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException
from deepface import DeepFace
import matplotlib.pyplot as plt
from io import BytesIO
import base64
from urllib.parse import urlparse


class Logger:
    @staticmethod
    def print_status(message):
        """Enhanced logging function with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [BOT STATUS] {message}")
        logging.info(message)

class WebDriverManager:
    def __init__(self, headless=False):
        self.headless = headless
        self.driver = None
        
    def initialize(self):
        """Initialize Chrome WebDriver with comprehensive options"""
        print("Initializing Chrome WebDriver...")
        try:
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument("--headless=new")
                print("Running in headless mode")

            options.add_argument("--disable-notifications")
            options.add_argument("--use-fake-ui-for-media-stream")
            options.add_argument("--use-fake-device-for-media-stream")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--auto-select-desktop-capture-source=Entire screen")

            # Static path for Chrome profile
            user_data_dir = os.path.join(os.getcwd(), "chrome_profiles", "my_chrome_profile")
            os.makedirs(user_data_dir, exist_ok=True)
            options.add_argument(f"--user-data-dir={user_data_dir}")
            print(f"Using Chrome profile at: {user_data_dir}")

            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            prefs = {
                "credentials_enable_service": False,
                "profile.password_manager_enabled": False
            }
            options.add_experimental_option("prefs", prefs)
            
            self.driver = webdriver.Chrome(options=options)
            
            if not self.headless:
                self.driver.maximize_window()
                print("Browser window maximized")

            print("Chrome WebDriver initialized successfully")
            return True
        except Exception as e:
            print(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def quit(self):
        """Close the WebDriver instance"""
        if self.driver:
            try:
                self.driver.quit()
                print("Browser closed successfully")
                return True
            except Exception as e:
                print(f"Error closing browser: {str(e)}")
                return False
        return True

class CookieManager:
    def __init__(self):
        pass  # No cookie file needed as we're using persistent profile

    def clear_cookies(self, driver):
        """Clear all cookies if needed"""
        try:
            driver.delete_all_cookies()
            print("All cookies cleared")
            return True
        except Exception as e:
            print(f"Error clearing cookies: {e}")
            return False

class GoogleMeetAuthenticator:
    def __init__(self, driver, email=None, password=None):
        self.driver = driver
        self.email = email
        self.password = password

    def is_logged_in(self):
        """Check if we're logged in by visiting Gmail"""
        try:
            self.driver.get("https://mail.google.com")
            WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Inbox"))
            )
            print("✅ Verified logged in via Gmail")
            return True
        except:
            print("⚠️ Not logged in")
            return False

    def login(self):
        """Login to Google account if not already logged in"""
        print("🚀 Starting Google authentication check...")
        
        if self.is_logged_in():
            print("✅ Already logged in via persistent profile")
            return True

        try:
            # Clear cookies and proceed with manual login
            self.driver.delete_all_cookies()
            print("🧹 Cleared browser cookies")

            signin_url = (
                "https://accounts.google.com/v3/signin/identifier?"
                "continue=https%3A%2F%2Fmail.google.com%2Fmail%2F&"
                "service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin"
            )
            self.driver.get(signin_url)
            print("🌐 Navigated to Google signin page")

            email_field = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.ID, "identifierId"))
            )
            email_field.send_keys(self.email)
            self.driver.find_element(By.ID, "identifierNext").click()
            print("📧 Entered email address")

            password_field = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.NAME, "Passwd"))
            )
            password_field.send_keys(self.password)
            self.driver.find_element(By.ID, "passwordNext").click()
            print("🔒 Submitted password")

            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Inbox"))
            )
            print("✅ Successfully logged into Google account")

            # Optional: Handle "Continue as..." screen
            try:
                continue_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='button']//span[contains(text(), 'Continue as')]"))
                )
                continue_button.click()
                print("👉 Clicked 'Continue as'")
            except TimeoutException:
                print("ℹ️ No 'Continue as' prompt")

            return True

        except TimeoutException:
            print("❌ Timeout during Google login process")
            self.driver.save_screenshot("login_error.png")
            print("📸 Screenshot saved as login_error.png")
            return False
        except Exception as e:
            print(f"❌ Error during Google login: {str(e)}")
            return False

class MeetingJoiner:
    def __init__(self, driver):
        self.driver = driver
        
    def join(self, meeting_link):
        """Join Google Meet meeting with multiple fallback strategies"""
        Logger.print_status(f"Attempting to join meeting: {meeting_link}")
        try:
            self.driver.get(meeting_link)
            Logger.print_status("Loaded meeting page")

            # Disable camera and microphone
            Logger.print_status("Attempting to disable camera and microphone")
            for device in ['camera', 'microphone']:
                try:
                    toggle_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 
                            f"button[aria-label*='{device}'], div[aria-label*='{device}']"))
                    )
                    toggle_btn.click()
                    Logger.print_status(f"Disabled {device}")
                    time.sleep(0.5)
                except Exception as e:
                    Logger.print_status(f"Could not disable {device}: {str(e)}")

            # Multiple strategies to find and click join button
            join_button_selectors = [
                ("css", "button[aria-label*='Join now']"),
                ("css", "button[aria-label*='Ask to join']"),
                ("css", "div[role='button'][aria-label*='Join']"),
                ("xpath", "//span[contains(., 'Join') or contains(., 'Ask')]"),
                ("css", "button:has(> span:contains('Join')), button:has(> span:contains('Ask'))")
            ]

            joined = False
            for by, selector in join_button_selectors:
                if joined:
                    break
                    
                try:
                    Logger.print_status(f"Trying join button with {by}: {selector}")
                    join_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", join_btn)
                    time.sleep(0.5)
                    join_btn.click()
                    Logger.print_status(f"✅ Successfully clicked join button using {by} selector: {selector}")
                    joined = True
                    break
                except Exception as e:
                    Logger.print_status(f"❌ Failed with {by} selector {selector}: {str(e)}")

            if not joined:
                # Final fallback - click any visible join-like button
                buttons = self.driver.find_elements(By.CSS_SELECTOR, "button,div[role='button']")
                for button in buttons:
                    try:
                        if any(keyword in button.text.lower() for keyword in ["join", "ask"]) or \
                           any(keyword in button.get_attribute('aria-label').lower() for keyword in ["join", "ask"]):
                            button.click()
                            Logger.print_status("✅ Clicked join button via final fallback")
                            joined = True
                            break
                    except:
                        continue

            return joined
            
        except Exception as e:
            Logger.print_status(f"Error joining meeting: {str(e)}")
            return False

class ParticipantAnalyzer:
    def __init__(self, driver):
        self.driver = driver
        
    def check_participants(self):
        """Check if there are other participants in the meeting by trying all methods"""
        Logger.print_status("🔍 Checking participants using multiple methods...")
        try:
            # Method 1: People button with count
            method1_result = self._check_participant_count_badge()
            
            # Method 2: Open participant panel and count
            method2_result = self._check_participant_list()
            
            # Method 3: Check meeting status messages
            method3_result = self._check_meeting_status()
            
            # Final Decision
            Logger.print_status(f"🧮 Final method results -> M1: {method1_result}, M2: {method2_result}, M3: {method3_result}")

            if any(res is True for res in [method1_result, method2_result, method3_result]):
                return True
            elif all(res is False for res in [method1_result, method2_result, method3_result]):
                return False
            else:
                Logger.print_status("⚠️ Inconclusive results — assuming participants present.")
                return True

        except Exception as e:
            Logger.print_status(f"Error checking participants: {str(e)}")
            return True

    def _check_participant_count_badge(self):
        """Check participant count using the people button badge"""
        try:
            Logger.print_status("👉 Method 1: People button badge...")
            people_button = WebDriverWait(self.driver, 5).until(
                EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label^='People']"))
            )
            count_text = people_button.text
            Logger.print_status(f"🧾 People Button Text: {count_text}")
            
            if count_text:
                import re
                match = re.search(r'\(?(\d+)\)?', count_text)
                if match:
                    count = int(match.group(1))
                    Logger.print_status(f"✅ Method 1 count: {count}")
                    return count > 1
                elif 'people' in count_text.lower():
                    Logger.print_status("✅ No count in text — likely alone.")
                    return False
            return False
        except Exception as e:
            Logger.print_status(f"❌ Method 1 failed: {e}")
            return False

    def _check_participant_list(self):
        """Check participants by opening the people panel"""
        try:
            Logger.print_status("👉 Method 2: Opening people panel...")
            people_button = WebDriverWait(self.driver, 5).until(
                EC.element_to_be_clickable((By.CSS_SELECTOR, "button[aria-label^='People']"))
            )
            people_button.click()
            time.sleep(1)

            participant_selectors = [
                "div[role='listitem']",
                "div[class*='participant']",
                "div[aria-label*='participant']"
            ]

            for selector in participant_selectors:
                try:
                    participants = WebDriverWait(self.driver, 3).until(
                        EC.presence_of_all_elements_located((By.CSS_SELECTOR, selector))
                    )
                    count = len(participants)
                    Logger.print_status(f"✅ Method 2 count: {count} using selector: {selector}")
                    
                    # Try to close people panel
                    try:
                        close_buttons = self.driver.find_elements(By.CSS_SELECTOR, "button[aria-label^='Close']")
                        for btn in close_buttons:
                            try:
                                btn.click()
                                break
                            except:
                                continue
                    except:
                        pass
                    
                    return count > 1
                except:
                    continue
            return False
        except Exception as e:
            Logger.print_status(f"❌ Method 2 failed: {e}")
            return False

    def _check_meeting_status(self):
        """Check participants by examining meeting status messages"""
        try:
            Logger.print_status("👉 Method 3: Checking meeting status text...")
            status_elements = self.driver.find_elements(
                By.CSS_SELECTOR, "div[class*='status'], div[aria-label*='call']"
            )
            
            for element in status_elements:
                try:
                    text = element.text.strip().lower()
                    if not text:  # Skip empty elements
                        continue
                        
                    Logger.print_status(f"Found status text: {text}")
                    
                    if 'alone' in text or 'waiting' in text:
                        Logger.print_status("✅ Status: Alone in meeting.")
                        return False
                    elif 'participant' in text or 'people' in text:
                        Logger.print_status(f"✅ Status mentions participants: {text}")
                        return True
                    elif 'joined' in text or 'connected' in text:
                        Logger.print_status("✅ Status indicates someone joined")
                        return True
                        
                except Exception as element_error:
                    Logger.print_status(f"⚠️ Error processing element: {element_error}")
                    continue
                    
            Logger.print_status("No conclusive status found")
            return False
            
        except Exception as e:
            Logger.print_status(f"❌ Method 3 failed: {str(e)}")
            return False
        
class MeetingRecorder:
    def __init__(self, filename, duration):
        self.filename = filename
        self.duration = duration
        self.ffmpeg_process = None
        self.recording_start_time = None
        self.should_stop = False
        
    def start_recording(self):
        """Start screen recording with multiple fallback methods"""
        Logger.print_status("Initializing screen recording...")
        try:
            # Ensure filename has .mp4 extension
            if not self.filename.lower().endswith('.mp4'):
                self.filename += '.mp4'
                Logger.print_status(f"Added .mp4 extension to filename: {self.filename}")
                
            output_path = os.path.abspath(self.filename)
            Logger.print_status(f"Output will be saved to: {output_path}")

            # Define recording methods in order of preference
            recording_methods = self._get_recording_methods(output_path)

            # Try each method until one succeeds
            last_error = None
            for method in recording_methods:
                try:
                    Logger.print_status(f"Attempting recording with command: {' '.join(method)}")
                    self.ffmpeg_process = subprocess.Popen(
                        method,
                        stdin=subprocess.PIPE,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        creationflags=subprocess.CREATE_NO_WINDOW,
                        shell=True
                    )
                    
                    # Verify process started successfully
                    time.sleep(2)
                    if self.ffmpeg_process.poll() is None:
                        Logger.print_status("Recording started successfully")
                        self.recording_start_time = datetime.now()
                        return True
                    else:
                        error = self.ffmpeg_process.stderr.read().decode('utf-8', errors='ignore')
                        last_error = error
                        Logger.print_status(f"Recording attempt failed: {error}")
                        self.ffmpeg_process.kill()
                except Exception as e:
                    last_error = str(e)
                    Logger.print_status(f"Error starting recording process: {str(e)}")

            raise Exception(f"All recording methods failed. Last error: {last_error}")
            
        except Exception as e:
            Logger.print_status(f"Critical error starting recording: {str(e)}")
            if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process:
                self.ffmpeg_process.kill()
            raise

    def _get_recording_methods(self, output_path):
        """Generate different recording method commands based on available audio devices"""
        methods = []
        available_devices = self._get_audio_devices()
        Logger.print_status(f"Available audio devices: {available_devices}")

        # Method 1: Both audio devices
        if len(available_devices) >= 2:
            methods.append([
                'ffmpeg', '-f', 'gdigrab', '-framerate', '30', '-video_size', '1920x1080', '-i', 'desktop',
                '-f', 'dshow', '-i', f'audio={available_devices[0]}',
                '-f', 'dshow', '-i', f'audio={available_devices[1]}',
                '-filter_complex', '[1:a][2:a]amix=inputs=2[a]',
                '-map', '0:v', '-map', '[a]',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
                '-y', output_path
            ])

        # Method 2: Single audio device
        if available_devices:
            methods.append([
                'ffmpeg', '-f', 'gdigrab', '-framerate', '30', '-video_size', '1920x1080', '-i', 'desktop',
                '-f', 'dshow', '-i', f'audio={available_devices[0]}',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
                '-y', output_path
            ])

        # Method 3: Video only
        methods.append([
            'ffmpeg', '-f', 'gdigrab', '-framerate', '30', '-video_size', '1920x1080', '-i', 'desktop',
            '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
            '-an', '-movflags', '+faststart', '-y', output_path
        ])
        
        return methods

    def _get_audio_devices(self):
        """Get list of available audio devices"""
        try:
            result = subprocess.run(
                ['ffmpeg', '-list_devices', 'true', '-f', 'dshow', '-i', 'dummy'],
                stderr=subprocess.PIPE, stdout=subprocess.PIPE, text=True
            )
            devices = []
            for line in result.stderr.split('\n'):
                if 'audio' in line.lower() and 'dshow' in line.lower():
                    device = line.split('"')[1]
                    devices.append(device)
            return devices
        except Exception as e:
            Logger.print_status(f"Error detecting audio devices: {str(e)}")
            return []

    def stop_recording(self):
        """Gracefully stop the recording process"""
        Logger.print_status("Beginning recording shutdown process")
        
        if not hasattr(self, 'ffmpeg_process') or not self.ffmpeg_process:
            Logger.print_status("No recording process to stop")
            return

        try:
            # Attempt graceful shutdown
            Logger.print_status("Attempting graceful FFmpeg shutdown")
            try:
                self.ffmpeg_process.stdin.write(b'q\n')
                self.ffmpeg_process.stdin.flush()
                Logger.print_status("Sent quit command to FFmpeg")
            except:
                Logger.print_status("Could not send quit command to FFmpeg")

            # Wait for process to finish
            try:
                Logger.print_status("Waiting for FFmpeg to finish...")
                self.ffmpeg_process.wait(timeout=15)
                Logger.print_status("FFmpeg exited cleanly")
            except subprocess.TimeoutExpired:
                Logger.print_status("FFmpeg did not exit - terminating")
                self.ffmpeg_process.terminate()
                try:
                    self.ffmpeg_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    Logger.print_status("FFmpeg did not terminate - killing")
                    self.ffmpeg_process.kill()

            # Verify output file
            if os.path.exists(self.filename):
                file_size = os.path.getsize(self.filename) / (1024 * 1024)  # in MB
                Logger.print_status(f"Recording saved successfully - Size: {file_size:.2f} MB")
                
                # Validate file
                try:
                    result = subprocess.run(
                        ['ffprobe', '-v', 'error', '-show_format', self.filename],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5
                    )
                    if result.returncode == 0:
                        Logger.print_status("Recording file is valid")
                    else:
                        Logger.print_status("Warning: Recording file might be corrupted")
                except:
                    Logger.print_status("Could not validate recording file")
            else:
                Logger.print_status("Error: Recording file was not created")

        except Exception as e:
            Logger.print_status(f"Error stopping recording: {str(e)}")
            if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process:
                self.ffmpeg_process.kill()


class MeetingMonitor:
    def __init__(self, driver, recorder, participant_analyzer, duration):
        self.driver = driver
        self.recorder = recorder
        self.participant_analyzer = participant_analyzer
        self.duration = duration
        self.should_stop = False
        
    def monitor(self):
        """Monitor the recording session and meeting status"""
        Logger.print_status(f"Starting recording monitor for {self.duration} minutes")
        start_time = time.time()
        end_time = start_time + (self.duration * 60)
        last_participant_check = 0
        participants_check_count = 0
        
        try:
            while time.time() < end_time and not self.should_stop:
                current_time = time.time()
                elapsed = int(current_time - start_time)
                remaining = int(end_time - current_time)
                
                Logger.print_status(f"Recording in progress - Elapsed: {elapsed}s, Remaining: {remaining}s")

                # Check participants periodically
                if current_time - last_participant_check > 30 and elapsed > 20:
                    last_participant_check = current_time
                    if not self.participant_analyzer.check_participants():
                        participants_check_count += 1
                        Logger.print_status(f"No participants detected ({participants_check_count}/2 checks)")
                        
                        if participants_check_count >= 2:
                            Logger.print_status("No participants for 1 minute - ending recording")
                            self.should_stop = True
                            break
                    else:
                        participants_check_count = 0
                
                # 10 seconds gap between participent check
                time.sleep(10)

            # Recording completed normally
            Logger.print_status("Recording duration completed - stopping recording")
            self.recorder.stop_recording()

        except Exception as e:
            Logger.print_status(f"Error during recording monitoring: {str(e)}")
            self.recorder.stop_recording()
            raise

class AudioTranscriber:
    def __init__(self, driver):
        self.driver = driver
        self.transcript_by_speaker = defaultdict(list)
        self.speaker_cache = {}  # Optional: Cache last known speaker name
        self.recognizer = sr.Recognizer()
        self.recognizer.dynamic_energy_threshold = True
        self.recognizer.pause_threshold = 0.8
        self.should_stop = False
    def get_active_speaker_name(self):
        """
        Detects the currently speaking participant on Google Meet using:
        - aria-label "is speaking"
        - speaker tiles with dynamic classes/styles
        - nested child element name lookup
        - full attribute dumps for debug
        """

        def extract_name_from_children(el):
            """Recursively extract participant name from nested children"""
            try:
                children = el.find_elements(By.XPATH, ".//*")
                for child in children:
                    name_attrs = [
                        child.get_attribute("data-self-name"),
                        child.get_attribute("aria-label"),
                        child.get_attribute("title"),
                        child.text
                    ]
                    for val in name_attrs:
                        if val and val.strip() and 2 < len(val.strip()) < 50:
                            print(f"   🔍 Found child name: {val.strip()}")
                            return val.strip()
            except Exception as e:
                print(f"⚠️ Error in child name lookup: {e}")
            return None

        try:
            print("\n🔍 Scanning Google Meet UI for active speaker...")

            # 🧠 Strategy 1: Look for aria-labels saying someone "is speaking"
            try:
                speaking_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[aria-label*='is speaking']")
                for el in speaking_elements:
                    label = el.get_attribute("aria-label")
                    if label and "is speaking" in label:
                        name = label.replace(" is speaking", "").strip()
                        print(f"✅ Found speaker via aria-label: {name}")
                        return name
            except Exception as e:
                print(f"⚠️ aria-label strategy failed: {e}")

            # 🎯 Strategy 2: Inspect tiles using class clues and attributes
            tiles = self.driver.find_elements(By.CSS_SELECTOR, "div[jsname][class*='Kqi1ib'], div[class*='Kqi1ib']")
            print(f"🧱 Found {len(tiles)} possible speaker tiles")

            for i, tile in enumerate(tiles):
                try:
                    print(f"\n🔎 Tile {i + 1}")
                    # Print direct attributes
                    tile_attrs = self.driver.execute_script("""
                        var element = arguments[0];
                        var attrs = {};
                        for (var i = 0; i < element.attributes.length; i++) {
                            var attr = element.attributes[i];
                            attrs[attr.name] = attr.value;
                        }
                        return attrs;
                    """, tile)

                    for attr_name, attr_value in tile_attrs.items():
                        print(f"   🏷️ {attr_name}: {attr_value}")

                    class_name = tile.get_attribute("class") or ""
                    style = tile.get_attribute("style") or ""

                    # Heuristic indicators of active speaker
                    if "border" in class_name or "pulse" in class_name or "scale" in style or "z-index" in style:
                        print("   💡 Possible visual cue of speaking")
                        nested_name = extract_name_from_children(tile)
                        if nested_name:
                            print(f"✅ Active speaker via tile visual + nested: {nested_name}")
                            return nested_name

                    # Fallback: check top-level text or attribute
                    raw_name = tile.get_attribute("data-self-name") or tile.get_attribute("aria-label") or tile.text
                    if raw_name and raw_name.strip():
                        print(f"🛟 Fallback tile name: {raw_name.strip()}")
                        return raw_name.strip()

                except Exception as tile_err:
                    print(f"⚠️ Error in tile {i + 1}: {tile_err}")

            # 🚑 Strategy 3: Global fallback scan of named divs
            fallback_elements = self.driver.find_elements(By.CSS_SELECTOR, "div[data-self-name], div[aria-label], div[title]")
            print(f"\n🔍 Running fallback scan for names from {fallback_elements} elements")
            for el in fallback_elements:
                try:
                
                    try:
                        print(f"\n🔎 Globle fallback {i + 1}")
                        # Print direct attributes
                        tile_attrs = self.driver.execute_script("""
                            var element = arguments[0];
                            var attrs = {};
                            for (var i = 0; i < element.attributes.length; i++) {
                                var attr = element.attributes[i];
                                attrs[attr.name] = attr.value;
                            }
                            return attrs;
                        """, el)

                        for attr_name, attr_value in tile_attrs.items():
                            print(f"   🏷️ {attr_name}: {attr_value}")

                        class_name = el.get_attribute("class") or ""
                        style = el.get_attribute("style") or ""

                        # Heuristic indicators of active speaker
                        if "border" in class_name or "pulse" in class_name or "scale" in style or "z-index" in style:
                            print("   💡 Possible visual cue of speaking")
                            nested_name = extract_name_from_children(tile)
                            if nested_name:
                                print(f"✅ Active speaker via tile visual + nested: {nested_name}")
                                return nested_name

                        # Fallback: check top-level text or attribute
                        raw_name = tile.get_attribute("data-self-name") or tile.get_attribute("aria-label") or tile.text
                        if raw_name and raw_name.strip():
                            print(f"🛟 Fallback tile name: {raw_name.strip()}")
                            return raw_name.strip()

                    except Exception as tile_err:
                        print(f"⚠️ Error in tile {i + 1}: {tile_err}")

                    name = el.get_attribute("data-self-name") or el.get_attribute("aria-label") or el.get_attribute("title") or el.text
                    if name and name.strip():
                        print(f"🛟 Fallback match: {name.strip()}")
                        return name.strip()
                except:
                    continue

            print("❌ No speaker name determined using all methods.")
            return "Unknown"

        except Exception as outer_e:
            print(f"❌ Fatal error in get_active_speaker_name: {outer_e}")
            return "Unknown"

    def capture_transcript(self):
        Logger.print_status("🎙️ Starting transcript capture...")

        while not self.should_stop:
            with sr.Microphone() as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=1)
                try:
                    audio = self.recognizer.listen(source, timeout=3, phrase_time_limit=10)
                    text = self.recognizer.recognize_google(audio)
                    timestamp = datetime.now().strftime('%H:%M:%S')

                    # 🧠 Assign speaker name from UI
                    speaker_name = self.get_active_speaker_name()  # Or pull from another bot class if shared

                    self.transcript_by_speaker[speaker_name].append({
                        "timestamp": timestamp,
                        "text": text
                    })

                    Logger.print_status(f"[{timestamp}] {speaker_name}: {text}")

                except sr.UnknownValueError:
                    Logger.print_status("Could not understand audio")
                except sr.WaitTimeoutError:
                    continue
    
    def detect_active_speaker_loop(self):
        """Continuously check who is the active speaker from the DOM every second"""
        self.recent_speaker = "Unknown"
        while not self.should_stop:
            speaker = self.get_active_speaker_name()
            if speaker != "Unknown":
                self.recent_speaker = speaker
            time.sleep(1)

    def get_transcript(self):
        print("\n📄 Transcript by Speaker:")
        for speaker, entries in self.transcript_by_speaker.items():
            print(f"\n🗣️ {speaker}:")
            for item in entries:
                print(f"[{item['timestamp']}] {item['text']}")


class EmotionAnalyzer:
    def __init__(self):
        self.emotions_by_person = defaultdict(list)
        self.should_stop = False
        self.face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        
    def analyze_emotions(self):
        """Analyze participant emotions via webcam"""
        Logger.print_status("Starting emotion analysis thread")
        cap = cv2.VideoCapture(0)
        
        while not self.should_stop:
            ret, frame = cap.read()
            if not ret:
                continue
                
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = self.face_cascade.detectMultiScale(gray, 1.3, 5)
                
                for i, (x, y, w, h) in enumerate(faces):
                    face_img = frame[y:y+h, x:x+w]
                    
                    try:
                        face_id = f"person_{i+1}"
                        analysis = DeepFace.analyze(face_img, actions=['emotion'], enforce_detection=False)
                        dominant_emotion = analysis[0]['dominant_emotion']
                        timestamp = datetime.now().strftime('%H:%M:%S')
                        
                        self.emotions_by_person[face_id].append({
                            'timestamp': timestamp,
                            'emotion': dominant_emotion,
                            'confidence': analysis[0]['emotion'][dominant_emotion]
                        })
                        
                        Logger.print_status(f"{face_id}: {dominant_emotion} ({analysis[0]['emotion'][dominant_emotion]:.1f}%)")
                        
                    except Exception as e:
                        Logger.print_status(f"Emotion analysis error: {e}")
                        
            except Exception as e:
                Logger.print_status(f"Face detection error: {e}")
                
            time.sleep(5)
            
        cap.release()
        Logger.print_status("Emotion analysis stopped")

    def get_emotion_data(self):
        """Get the current emotion data"""
        return dict(self.emotions_by_person)

class MeetingReporter:
    @staticmethod
    def generate_report(filename, transcript_data, emotion_data, meeting_link):
        """Generate comprehensive meeting report"""
        Logger.print_status("Generating meeting report...")
        
        # Generate visualizations
        speaker_chart, emotion_chart = MeetingReporter._generate_visualizations(transcript_data, emotion_data)
        
        report_data = {
            'meeting_title': os.path.splitext(os.path.basename(filename))[0],
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'duration': MeetingReporter._get_recording_duration(),
            'transcript_by_speaker': transcript_data,
            'emotions_by_person': emotion_data,
            'meeting_link': meeting_link,
            'speaker_chart': speaker_chart,
            'emotion_chart': emotion_chart
        }
        
        # Save report to JSON file
        report_filename = os.path.splitext(filename)[0] + "_report.json"
        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=2)
            Logger.print_status(f"Saved report to {report_filename}")
            
        return report_filename

    @staticmethod
    def _generate_visualizations(transcript_data, emotion_data):
        """Generate charts for speaker and emotion data"""
        Logger.print_status("Generating data visualizations...")
        
        # Speaker distribution chart
        speaker_chart = None
        if transcript_data:
            speaker_counts = {speaker: len(entries) for speaker, entries in transcript_data.items()}
            plt.figure(figsize=(8, 6))
            plt.pie(speaker_counts.values(), labels=speaker_counts.keys(), autopct='%1.1f%%')
            plt.title('Speaker Contribution')
            speaker_buf = BytesIO()
            plt.savefig(speaker_buf, format='png')
            plt.close()
            speaker_buf.seek(0)
            speaker_chart = base64.b64encode(speaker_buf.read()).decode('utf-8')
            Logger.print_status("Generated speaker distribution chart")
        
        # Emotion distribution chart
        emotion_chart = None
        if emotion_data:
            emotion_counts = defaultdict(int)
            for person_emotions in emotion_data.values():
                for entry in person_emotions:
                    emotion_counts[entry['emotion']] += 1
            
            plt.figure(figsize=(8, 6))
            plt.pie(emotion_counts.values(), labels=emotion_counts.keys(), autopct='%1.1f%%')
            plt.title('Emotion Distribution')
            emotion_buf = BytesIO()
            plt.savefig(emotion_buf, format='png')
            plt.close()
            emotion_buf.seek(0)
            emotion_chart = base64.b64encode(emotion_buf.read()).decode('utf-8')
            Logger.print_status("Generated emotion distribution chart")
        
        return speaker_chart, emotion_chart

    @staticmethod
    def _get_recording_duration(start_time, end_time):
        """Calculate recording duration in HH:MM:SS format
        
        Args:
            start_time (datetime): When the meeting was joined
            end_time (datetime): When the meeting was stopped
            
        Returns:
            str: Duration in HH:MM:SS format
        """
        if not start_time or not end_time:
            return "00:00:00"
        
        duration = end_time - start_time
        total_seconds = int(duration.total_seconds())
        
        # Calculate hours, minutes, seconds
        hours = total_seconds // 3600
        remaining_seconds = total_seconds % 3600
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        
        # Format as HH:MM:SS with leading zeros
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

class MeetBot:
    """Main Google Meet bot class that coordinates all components"""
    
    def __init__(self, email, password, meeting_link, filename, duration, headless=False):
        self.email = email
        self.password = password
        self.meeting_link = meeting_link
        self.filename = filename
        self.duration = duration
        self.headless = headless
        # Timing attributes
        self.meeting_start_time = None
        self.meeting_end_time = None
        
        # Initialize components
        self.driver_manager = WebDriverManager(headless)
        self.authenticator = None
        self.meeting_joiner = None
        self.participant_analyzer = None
        self.recorder = None
        self.monitor = None
        self.transcriber = None
        self.emotion_analyzer = None
        
        # Threads
        self.transcript_thread = None
        self.emotion_thread = None
        self.active_user_thread = None
        
        Logger.print_status("🔧 MeetBot initialized with all components")

    def run(self):
        """Main bot execution flow with proper error handling"""
        try:
            Logger.print_status("Starting Google Meet Bot...")
            
            # Initialize driver first
            self.driver_manager.initialize()
            driver = self.driver_manager.driver
            
            # Initialize components that need the driver
            self.authenticator = GoogleMeetAuthenticator(driver, self.email, self.password)
            self.meeting_joiner = MeetingJoiner(driver)
            
            # Perform login and join meeting
            if not self.authenticator.login():
                raise Exception("Failed to login to Google account")
            
            joined = self.meeting_joiner.join(self.meeting_link)    

            if joined:
                self.participant_analyzer = ParticipantAnalyzer(driver)
                
                # Start recording immediately
                self.recorder = MeetingRecorder(self.filename, self.duration)
                self.recorder.start_recording()
                
                try:
                    # Start background services
                    Logger.print_status("Starting background services...")
                    self._start_background_services(driver)
                    

                    # Record meeting start time    
                    self.meeting_start_time = datetime.now()
                        
                    # Start monitoring
                    self.monitor = MeetingMonitor(driver, self.recorder, self.participant_analyzer, self.duration)
                    Logger.print_status("Starting meeting monitoring...")
                    self.monitor.monitor()
                    
                    # Generate report if completed successfully
                    self._generate_final_report()
                    Logger.print_status("Meeting recording completed successfully")
                    
                except Exception as e:
                    Logger.print_status(f"Error in bot execution: {str(e)}")
                    raise
            else:
                Logger.print_status("❌ Failed to join meeting. Aborting service start.")
                
        except Exception as e:
            Logger.print_status(f"Critical error: {str(e)}")
        finally:
            self.stop()

    def _start_background_services(self, driver):
        """Start all background services in separate threads"""
        self.transcriber = AudioTranscriber(driver)
        self.emotion_analyzer = EmotionAnalyzer()
        
        self.transcript_thread = threading.Thread(
            target=self.transcriber.capture_transcript, 
            daemon=True,
            name="TranscriptThread"
        )
        self.emotion_thread = threading.Thread(
            target=self.emotion_analyzer.analyze_emotions,
            daemon=True,
            name="EmotionThread"
        )
        # Checking for active talking person 
        self.active_user_thread = threading.Thread(
            target=self.transcriber.detect_active_speaker_loop,
            daemon=True,
            name="ActiveUserThread"
        )
        
        self.transcript_thread.start()
        self.emotion_thread.start()
        self.active_user_thread.start()

        Logger.print_status("✅ Background services started")

    def _generate_final_report(self):
        """Generate the final meeting report"""
        try:
            Logger.print_status("📊 Generating final report...")
            
            # Get all collected data
            transcript_data = self.transcriber.get_transcript() if self.transcriber else {}
            emotion_data = self.emotion_analyzer.get_emotion_data() if self.emotion_analyzer else {}
            
            # Create report structure
            report = {
                "meeting_details": {
                    "title": os.path.splitext(os.path.basename(self.filename))[0],
                    "link": self.meeting_link,
                    "duration": self._get_recording_duration(),
                    "start_time": self.meeting_start_time.isoformat() if self.meeting_start_time else None,
                    "end_time": self.meeting_end_time.isoformat() if self.meeting_end_time else None,
                    "participant_count": len(self.participant_analyzer.get_participant_data()) if self.participant_analyzer else 0,
                    "recording_path": os.path.abspath(self.filename)
                },
                "transcript": transcript_data,
                "emotion_analysis": emotion_data,
                "summary": self._generate_summary(transcript_data),
                "visualizations": self._generate_visualizations(transcript_data, emotion_data)
            }
            
            # Save report to file
            report_filename = f"report_{os.path.splitext(self.filename)[0]}.json"
            with open(report_filename, 'w') as f:
                json.dump(report, f, indent=2)
                
            Logger.print_status(f"✅ Report generated successfully: {report_filename}")
            return report
            
        except Exception as e:
            Logger.print_status(f"❌ Error generating report: {str(e)}")
            return None

    def _generate_summary(self, transcript_data):
        """Generate a summary of the meeting"""
        summary = {
            "key_topics": [],
            "action_items": [],
            "sentiment": "neutral"
        }
        
        try:
            if transcript_data:
                # Extract all text from transcript
                all_text = " ".join(
                    entry['text'] 
                    for speaker in transcript_data.values() 
                    for entry in speaker
                )
                
                # Simple keyword extraction (in real implementation use NLP)
                action_words = ['action', 'todo', 'task', 'follow up', 'next steps']
                summary['action_items'] = [
                    sentence.strip() 
                    for sentence in all_text.split('.') 
                    if any(word in sentence.lower() for word in action_words)
                ]
                
                # Get most frequent words as key topics
                from collections import Counter
                words = [word.lower() for word in all_text.split() if len(word) > 4]
                summary['key_topics'] = [word for word, count in Counter(words).most_common(5)]
                
        except Exception as e:
            Logger.print_status(f"⚠️ Error generating summary: {str(e)}")
            
        return summary

    def _generate_visualizations(self, transcript_data, emotion_data):
        """Generate visualization data for the report"""
        visualizations = {}
        
        try:
            if transcript_data:
                # Speaker distribution chart
                speaker_counts = {speaker: len(entries) for speaker, entries in transcript_data.items()}
                visualizations['speaker_distribution'] = speaker_counts
                
            if emotion_data:
                # Emotion distribution
                emotion_counts = defaultdict(int)
                for person_emotions in emotion_data.values():
                    for entry in person_emotions:
                        emotion_counts[entry['emotion']] += 1
                visualizations['emotion_distribution'] = dict(emotion_counts)
                
        except Exception as e:
            Logger.print_status(f"⚠️ Error generating visualizations: {str(e)}")
            
        return visualizations

    def _get_recording_duration(self):
        """Calculate actual recording duration"""
        if not self.meeting_start_time or not self.meeting_end_time:
            return "00:00:00"
        
        duration = self.meeting_end_time - self.meeting_start_time
        total_seconds = int(duration.total_seconds())
        
        hours = total_seconds // 3600
        remaining_seconds = total_seconds % 3600
        minutes = remaining_seconds // 60
        seconds = remaining_seconds % 60
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def stop(self):
        """Cleanup all resources and stop all components"""
        Logger.print_status("🛑 Stopping MeetBot and cleaning up resources...")
        
        # Record end time
        self.meeting_end_time = datetime.now()
        
        # Stop monitoring if active
        if self.monitor:
            self.monitor.should_stop = True
            
        # Stop recording if active
        if self.recorder:
            self.recorder.stop_recording()
        
        # Stop background services
        if self.transcriber:
            self.transcriber.should_stop = True
        if self.emotion_analyzer:
            self.emotion_analyzer.should_stop = True
            
        # Wait for threads to finish
        if self.transcript_thread and self.transcript_thread.is_alive():
            self.transcript_thread.join(timeout=5)
        if self.emotion_thread and self.emotion_thread.is_alive():
            self.emotion_thread.join(timeout=5)
        
        # Quit driver
        if self.driver_manager:
            self.driver_manager.quit()
        
        # Print final duration
        if self.meeting_start_time and self.meeting_end_time:
            Logger.print_status(f"⏱️ Total meeting duration: {self._get_recording_duration()}")
        
        Logger.print_status("✅ MeetBot stopped successfully")