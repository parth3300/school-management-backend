"""
Google Meet Recording Bot with Comprehensive Logging
"""
import string
import os
import time
import json
import tempfile
import base64
import subprocess
import logging
import random
import threading
from datetime import datetime
from collections import defaultdict
from io import BytesIO
import cv2
import numpy as np
import speech_recognition as sr
from deepface import DeepFace
import matplotlib.pyplot as plt
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException

class MeetBot:
    """Enhanced Google Meet recording bot with comprehensive logging"""

    def __init__(self, email, password, meeting_link, filename, duration, headless=False):
        self.email = email
        self.password = password
        self.meeting_link = meeting_link
        self.filename = filename
        self.headless = headless
        self.duration = duration
        self.email_recipient = "1111singalparth@gmail.com"
        self.driver = None
        self.recording_thread = None
        self.should_stop = False
        self.ffmpeg_process = None
        self.recording_start_time = None
        
        # Data collection
        self.transcript_by_speaker = defaultdict(list)
        self.emotions_by_person = defaultdict(list)
        self.speaker_count = 0
        self.current_speaker = None
        self.last_speaker_change = datetime.now()
        
        self.print_status("🔧 Enhanced bot initialized with speaker and emotion tracking")

    def print_status(self, message):
        """Enhanced logging function with timestamp"""
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        print(f"[{timestamp}] [BOT STATUS] {message}")
        logging.info(message)

    def initialize_driver(self):
        """Initialize Chrome WebDriver with comprehensive options"""
        self.print_status("Initializing Chrome WebDriver...")
        try:
            options = webdriver.ChromeOptions()
            if self.headless:
                options.add_argument("--headless=new")
                self.print_status("Running in headless mode")

            options.add_argument("--disable-notifications")
            options.add_argument("--use-fake-ui-for-media-stream")
            options.add_argument("--use-fake-device-for-media-stream")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)
            options.add_argument("--auto-select-desktop-capture-source=Entire screen")

            # Unique profile directory
            user_data_dir = tempfile.mkdtemp(prefix=f"chrome_profile_{int(time.time())}_")
            options.add_argument(f"--user-data-dir={user_data_dir}")
            self.print_status(f"Using Chrome profile at: {user_data_dir}")

            # Performance optimizations
            options.add_argument("--disable-gpu")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            
            self.driver = webdriver.Chrome(options=options)
            
            if not self.headless:
                self.driver.maximize_window()
                self.print_status("Browser window maximized")

            self.print_status("Chrome WebDriver initialized successfully")
        except Exception as e:
            self.print_status(f"Failed to initialize WebDriver: {str(e)}")
            raise

    def login_to_gmail(self):
        """Login to Gmail with robust error handling"""
        self.print_status("Starting Gmail login process...")
        try:
            signin_url = (
                "https://accounts.google.com/v3/signin/identifier?"
                "continue=https%3A%2F%2Fmail.google.com%2Fmail%2F&"
                "service=mail&flowName=GlifWebSignIn&flowEntry=ServiceLogin"
            )
            
            self.driver.delete_all_cookies()
            self.print_status("Cleared browser cookies")
            
            self.driver.get(signin_url)
            self.print_status("Navigated to Gmail signin page")

            # Email entry
            email_field = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.ID, "identifierId"))
            )
            email_field.send_keys(self.email)
            self.driver.find_element(By.ID, "identifierNext").click()
            self.print_status("Entered email address")

            # Password entry
            password_field = WebDriverWait(self.driver, 30).until(
                EC.element_to_be_clickable((By.NAME, "Passwd"))
            )
            password_field.send_keys(self.password)
            self.driver.find_element(By.ID, "passwordNext").click()
            self.print_status("Submitted password")

            # Wait for login completion
            WebDriverWait(self.driver, 30).until(
                EC.presence_of_element_located((By.PARTIAL_LINK_TEXT, "Inbox"))
            )
            self.print_status("Successfully logged into Gmail")

            # Handle "Continue as" prompt if it appears
            try:
                continue_button = WebDriverWait(self.driver, 10).until(
                    EC.element_to_be_clickable((By.XPATH, "//div[@role='button']//span[contains(text(), 'Continue as')]"))
                )
                continue_button.click()
                self.print_status("Clicked 'Continue as' button")
            except TimeoutException:
                self.print_status("No 'Continue as' prompt appeared")

            return True
            
        except TimeoutException:
            self.print_status("Timeout during Gmail login process")
            return False
        except Exception as e:
            self.print_status(f"Error during Gmail login: {str(e)}")
            return False

    def check_participants(self):
        """Check if there are other participants in the meeting by trying all methods"""
        try:
            self.print_status("🔍 Checking participants using multiple methods...")

            # Dump visible buttons/divs for inspection
            try:
                self.print_status("📋 Dumping visible buttons and divs...")
                elements = self.driver.find_elements(By.CSS_SELECTOR, "button, div")
                for i, el in enumerate(elements):
                    try:
                        label = el.get_attribute("aria-label")
                        role = el.get_attribute("role")
                        cls = el.get_attribute("class")
                        text = el.text.strip()
                        self.print_status(f"[{i}] tag=<{el.tag_name}> | aria-label='{label}' | role='{role}' | class='{cls}' | text='{text}'")
                    except Exception as e:
                        self.print_status(f"⚠️ Error reading element {i}: {str(e)}")
            except Exception as e:
                self.print_status(f"❌ Failed to dump selectors: {e}")

            method1_result = None
            method2_result = None
            method3_result = None

            # ✅ Method 1: People button with count
            try:
                self.print_status("👉 Method 1: People button badge...")
                people_button = WebDriverWait(self.driver, 5).until(
                    EC.presence_of_element_located((By.CSS_SELECTOR, "button[aria-label^='People']"))
                )
                count_text = people_button.text
                self.print_status(f"🧾 People Button Text: {count_text}")
                if count_text:
                    import re
                    match = re.search(r'\(?(\d+)\)?', count_text)
                    if match:
                        count = int(match.group(1))
                        self.print_status(f"✅ Method 1 count: {count}")
                        method1_result = count > 1
                    elif 'people' in count_text.lower():
                        self.print_status("✅ No count in text — likely alone.")
                        method1_result = False
            except Exception as e:
                self.print_status(f"❌ Method 1 failed: {e}")

            # ✅ Method 2: Open participant panel and count
            try:
                self.print_status("👉 Method 2: Opening people panel...")
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
                        self.print_status(f"✅ Method 2 count: {count} using selector: {selector}")
                        method2_result = count > 1
                        break  # Stop trying further selectors after success
                    except:
                        continue

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

            except Exception as e:
                self.print_status(f"❌ Method 2 failed: {e}")

            # ✅ Method 3: Check meeting status messages
            try:
                self.print_status("👉 Method 3: Checking meeting status text...")
                status_elements = self.driver.find_elements(
                    By.CSS_SELECTOR, "div[class*='status'], div[aria-label*='call']"
                )
                for element in status_elements:
                    text = element.text.strip().lower()
                    if 'alone' in text or 'waiting' in text:
                        self.print_status("✅ Status: Alone in meeting.")
                        method3_result = False
                        break
                    elif 'participant' in text or 'people' in text:
                        self.print_status(f"✅ Status mentions participants: {text}")
                        method3_result = True
                        break
            except Exception as e:
                self.print_status(f"❌ Method 3 failed: {e}")

            # Final Decision
            self.print_status(f"🧮 Final method results -> M1: {method1_result}, M2: {method2_result}, M3: {method3_result}")

            # If any method confirmed participants > 1, return True
            if any(res is True for res in [method1_result, method2_result, method3_result]):
                return True
            # If all are False, return False
            elif all(res is False for res in [method1_result, method2_result, method3_result]):
                return False
            # Otherwise, fallback to True (assume participants present)
            else:
                self.print_status("⚠️ Inconclusive results — assuming participants present.")
                return True

        except Exception as e:
            self.print_status(f"🔥 Fatal error in check_participants: {str(e)}")
            return True


    def join_meeting(self):
        """Join Google Meet meeting with multiple fallback strategies"""
        try:  # Added outer try block for consistency
            self.print_status(f"Attempting to join meeting: {self.meeting_link}")
            self.driver.get(self.meeting_link)
            self.print_status("Loaded meeting page")

            # Disable camera and microphone
            self.print_status("Attempting to disable camera and microphone")
            for device in ['camera', 'microphone']:
                try:
                    toggle_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((By.CSS_SELECTOR, 
                            f"button[aria-label*='{device}'], div[aria-label*='{device}']"))
                    )
                    toggle_btn.click()
                    self.print_status(f"Disabled {device}")
                    time.sleep(0.5)
                except Exception as e:
                    self.print_status(f"Could not disable {device}: {str(e)}")

            # Multiple strategies to find and click join button
            join_button_selectors = [
                ("css", "button[aria-label*='Join now']"),  # Primary selector
                ("css", "button[aria-label*='Ask to join']"),  # When requires permission
                ("css", "div[role='button'][aria-label*='Join']"),  # Div-based button
                ("xpath", "//span[contains(., 'Join') or contains(., 'Ask')]"),  # Text-based
                ("css", "button:has(> span:contains('Join')), button:has(> span:contains('Ask'))")  # Button with span
            ]

            joined = False
            for by, selector in join_button_selectors:
                if joined:  # Break if already joined
                    break
                    
                try:
                    self.print_status(f"Trying join button with {by}: {selector}")
                    join_btn = WebDriverWait(self.driver, 5).until(
                        EC.element_to_be_clickable((by, selector))
                    )
                    self.driver.execute_script("arguments[0].scrollIntoView(true);", join_btn)
                    time.sleep(0.5)
                    join_btn.click()
                    self.print_status(f"✅ Successfully clicked join button using {by} selector: {selector}")
                    joined = True
                    break  # Exit loop after successful click
                except Exception as e:
                    self.print_status(f"❌ Failed with {by} selector {selector}: {str(e)}")

            if not joined:
                # Final fallback - click any visible join-like button
                buttons = self.driver.find_elements(By.CSS_SELECTOR, "button,div[role='button']")
                for button in buttons:
                    try:
                        if any(keyword in button.text.lower() for keyword in ["join", "ask"]) or \
                        any(keyword in button.get_attribute('aria-label').lower() for keyword in ["join", "ask"]):
                            button.click()
                            self.print_status("✅ Clicked join button via final fallback")
                            joined = True
                            break
                    except:
                        continue

            return joined

        except Exception as e:  # Outer try block exception handling
            self.print_status(f"🔥 Error joining meeting: {str(e)}")
            return False
    
    def start_recording(self):
        """Start screen recording with multiple fallback methods"""
        self.print_status("Initializing screen recording...")
        try:
            # Ensure filename has .mp4 extension
            if not self.filename.lower().endswith('.mp4'):
                self.filename += '.mp4'
                self.print_status(f"Added .mp4 extension to filename: {self.filename}")
                
            output_path = os.path.abspath(self.filename)
            self.print_status(f"Output will be saved to: {output_path}")

            # Get available audio devices
            def get_audio_devices():
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
                    self.print_status(f"Error detecting audio devices: {str(e)}")
                    return []

            available_devices = get_audio_devices()
            self.print_status(f"Available audio devices: {available_devices}")

            # Define recording methods in order of preference
            recording_methods = []

            # Method 1: Both audio devices
            if len(available_devices) >= 2:
                recording_methods.append([
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
                recording_methods.append([
                    'ffmpeg', '-f', 'gdigrab', '-framerate', '30', '-video_size', '1920x1080', '-i', 'desktop',
                    '-f', 'dshow', '-i', f'audio={available_devices[0]}',
                    '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                    '-c:a', 'aac', '-b:a', '192k', '-movflags', '+faststart',
                    '-y', output_path
                ])

            # Method 3: Video only
            recording_methods.append([
                'ffmpeg', '-f', 'gdigrab', '-framerate', '30', '-video_size', '1920x1080', '-i', 'desktop',
                '-c:v', 'libx264', '-preset', 'ultrafast', '-pix_fmt', 'yuv420p',
                '-an', '-movflags', '+faststart', '-y', output_path
            ])

            # Try each method until one succeeds
            last_error = None
            for method in recording_methods:
                try:
                    self.print_status(f"Attempting recording with command: {' '.join(method)}")
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
                        self.print_status("Recording started successfully")
                        self.recording_start_time = datetime.now()
                        return True
                    else:
                        error = self.ffmpeg_process.stderr.read().decode('utf-8', errors='ignore')
                        last_error = error
                        self.print_status(f"Recording attempt failed: {error}")
                        self.ffmpeg_process.kill()
                except Exception as e:
                    last_error = str(e)
                    self.print_status(f"Error starting recording process: {str(e)}")

            raise Exception(f"All recording methods failed. Last error: {last_error}")
            
        except Exception as e:
            self.print_status(f"Critical error starting recording: {str(e)}")
            if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process:
                self.ffmpeg_process.kill()
            raise

    def monitor_recording(self):
        """Monitor the recording session and meeting status"""
        self.print_status(f"Starting recording monitor for {self.duration} minutes")
        start_time = time.time()
        end_time = start_time + (self.duration * 60)
        last_participant_check = 0
        participants_check_count = 0
        
        try:
            while time.time() < end_time and not self.should_stop:
                current_time = time.time()
                elapsed = int(current_time - start_time)
                remaining = int(end_time - current_time)
                
                self.print_status(f"Recording in progress - Elapsed: {elapsed}s, Remaining: {remaining}s")

                # Check participants periodically
                if current_time - last_participant_check > 30 and elapsed > 20:
                    last_participant_check = current_time
                    if not self.check_participants():
                        participants_check_count += 1
                        self.print_status(f"No participants detected ({participants_check_count}/2 checks)")
                        
                        if participants_check_count >= 2:
                            self.print_status("No participants for 1 minute - ending recording")
                            self.should_stop = True
                            break
                    else:
                        participants_check_count = 0
                
                time.sleep(10)

            # Recording completed normally
            self.print_status("Recording duration completed - stopping recording")
            self.stop_recording()

        except Exception as e:
            self.print_status(f"Error during recording monitoring: {str(e)}")
            self.stop_recording()
            raise

    def stop_recording(self):
        """Gracefully stop the recording process"""
        self.print_status("Beginning recording shutdown process")
        
        if not hasattr(self, 'ffmpeg_process') or not self.ffmpeg_process:
            self.print_status("No recording process to stop")
            return

        try:
            # Attempt graceful shutdown
            self.print_status("Attempting graceful FFmpeg shutdown")
            try:
                self.ffmpeg_process.stdin.write(b'q\n')
                self.ffmpeg_process.stdin.flush()
                self.print_status("Sent quit command to FFmpeg")
            except:
                self.print_status("Could not send quit command to FFmpeg")

            # Wait for process to finish
            try:
                self.print_status("Waiting for FFmpeg to finish...")
                self.ffmpeg_process.wait(timeout=15)
                self.print_status("FFmpeg exited cleanly")
            except subprocess.TimeoutExpired:
                self.print_status("FFmpeg did not exit - terminating")
                self.ffmpeg_process.terminate()
                try:
                    self.ffmpeg_process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.print_status("FFmpeg did not terminate - killing")
                    self.ffmpeg_process.kill()

            # Verify output file
            if os.path.exists(self.filename):
                file_size = os.path.getsize(self.filename) / (1024 * 1024)  # in MB
                self.print_status(f"Recording saved successfully - Size: {file_size:.2f} MB")
                
                # Validate file
                try:
                    result = subprocess.run(
                        ['ffprobe', '-v', 'error', '-show_format', self.filename],
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5
                    )
                    if result.returncode == 0:
                        self.print_status("Recording file is valid")
                    else:
                        self.print_status("Warning: Recording file might be corrupted")
                        self.repair_recording()
                except:
                    self.print_status("Could not validate recording file")
            else:
                self.print_status("Error: Recording file was not created")

        except Exception as e:
            self.print_status(f"Error stopping recording: {str(e)}")
            if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process:
                self.ffmpeg_process.kill()

    def repair_recording(self):
        """Attempt to repair a corrupted recording file"""
        self.print_status("Attempting to repair recording file...")
        try:
            temp_file = self.filename + '.temp.mp4'
            subprocess.run([
                'ffmpeg', '-i', self.filename, '-c', 'copy',
                '-f', 'mp4', '-movflags', '+faststart', temp_file
            ], check=True, timeout=30)
            
            if os.path.exists(temp_file):
                os.replace(temp_file, self.filename)
                self.print_status("Successfully repaired recording file")
            else:
                self.print_status("Repair attempt failed - no output file created")
        except Exception as e:
            self.print_status(f"Failed to repair recording: {str(e)}")
            if os.path.exists(temp_file):
                os.remove(temp_file)
                
    def capture_transcript(self):
        """Capture meeting transcript with speaker identification"""
        self.print_status("Starting transcript capture thread")
        r = sr.Recognizer()
        r.dynamic_energy_threshold = True
        r.pause_threshold = 0.8
        
        while not self.should_stop:
            try:
                with sr.Microphone() as source:
                    self.print_status("Adjusting for ambient noise...")
                    r.adjust_for_ambient_noise(source, duration=1)
                    
                    try:
                        self.print_status("Listening for speech...")
                        audio = r.listen(source, timeout=3, phrase_time_limit=15)
                        
                        try:
                            text = r.recognize_google(audio, show_all=False)
                            timestamp = datetime.now().strftime('%H:%M:%S')
                            
                            # Speaker change detection
                            if (datetime.now() - self.last_speaker_change).seconds > 10 or not self.current_speaker:
                                self.speaker_count += 1
                                self.current_speaker = f"speaker_{self.speaker_count}"
                                self.last_speaker_change = datetime.now()
                                self.print_status(f"New speaker detected: {self.current_speaker}")
                            
                            self.transcript_by_speaker[self.current_speaker].append({
                                'timestamp': timestamp,
                                'text': text
                            })
                            
                            self.print_status(f"[{timestamp}] {self.current_speaker}: {text}")
                            
                        except sr.UnknownValueError:
                            self.print_status("Could not understand audio")
                        except sr.RequestError as e:
                            self.print_status(f"Speech recognition error: {e}")
                            
                    except sr.WaitTimeoutError:
                        continue
                    
            except OSError as e:
                self.print_status(f"Microphone error: {e}")
                time.sleep(5)
            except Exception as e:
                self.print_status(f"Unexpected error in transcript: {e}")
                time.sleep(1)

    def analyze_emotions(self):
        """Analyze participant emotions via webcam"""
        self.print_status("Starting emotion analysis thread")
        face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')
        cap = cv2.VideoCapture(0)
        
        while not self.should_stop:
            ret, frame = cap.read()
            if not ret:
                continue
                
            try:
                gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                faces = face_cascade.detectMultiScale(gray, 1.3, 5)
                
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
                        
                        self.print_status(f"{face_id}: {dominant_emotion} ({analysis[0]['emotion'][dominant_emotion]:.1f}%)")
                        
                    except Exception as e:
                        self.print_status(f"Emotion analysis error: {e}")
                        
            except Exception as e:
                self.print_status(f"Face detection error: {e}")
                
            time.sleep(5)
            
        cap.release()
        self.print_status("Emotion analysis stopped")

    def generate_report(self):
        """Generate comprehensive meeting report"""
        self.print_status("Generating meeting report...")
        
        # Generate visualizations
        speaker_chart, emotion_chart = self.generate_visualizations()
        
        report_data = {
            'meeting_title': os.path.splitext(os.path.basename(self.filename))[0],
            'date': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'duration': self.get_recording_duration(),
            'transcript_by_speaker': dict(self.transcript_by_speaker),
            'emotions_by_person': dict(self.emotions_by_person),
            'meeting_link': self.meeting_link
        }
        
        # Save report to JSON file
        report_filename = os.path.splitext(self.filename)[0] + "_report.json"
        with open(report_filename, 'w') as f:
            json.dump(report_data, f, indent=2)
            self.print_status(f"Saved report to {report_filename}")
            
        return report_filename

    def generate_visualizations(self):
        """Generate charts for speaker and emotion data"""
        self.print_status("Generating data visualizations...")
        
        # Speaker distribution chart
        speaker_chart = None
        if self.transcript_by_speaker:
            speaker_counts = {speaker: len(entries) for speaker, entries in self.transcript_by_speaker.items()}
            plt.figure(figsize=(8, 6))
            plt.pie(speaker_counts.values(), labels=speaker_counts.keys(), autopct='%1.1f%%')
            plt.title('Speaker Contribution')
            speaker_buf = BytesIO()
            plt.savefig(speaker_buf, format='png')
            plt.close()
            speaker_buf.seek(0)
            speaker_chart = base64.b64encode(speaker_buf.read()).decode('utf-8')
            self.print_status("Generated speaker distribution chart")
        
        # Emotion distribution chart
        emotion_chart = None
        if self.emotions_by_person:
            emotion_counts = defaultdict(int)
            for person_emotions in self.emotions_by_person.values():
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
            self.print_status("Generated emotion distribution chart")
        
        return speaker_chart, emotion_chart

    def get_recording_duration(self):
        """Calculate recording duration"""
        if not hasattr(self, 'recording_start_time') or not self.recording_start_time:
            return "Unknown"
        
        duration = datetime.now() - self.recording_start_time
        hours, remainder = divmod(duration.seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        return f"{hours:02}:{minutes:02}:{seconds:02}"
    
    def run(self):
        """Main bot execution flow with proper error handling"""
        try:
            self.print_status("Starting enhanced Google Meet Bot...")
            self.recording_start_time = datetime.now()
            
            # Initialize driver first
            self.initialize_driver()
            
            # Start recording immediately to capture everything
            self.start_recording()
            
            try:
                # Start background services
                self.print_status("Starting background services...")
                self.transcript_thread = threading.Thread(target=self.capture_transcript, daemon=True)
                self.emotion_thread = threading.Thread(target=self.analyze_emotions, daemon=True)
                self.transcript_thread.start()
                self.emotion_thread.start()

                # Perform login and join meeting
                if not self.login_to_gmail():
                    raise Exception("Failed to login to Google account")
                    
                if not self.join_meeting():
                    raise Exception("Failed to join meeting")
                    
                # Start monitoring if everything succeeded
                self.print_status("Starting meeting monitoring...")
                self.monitor_recording()
                
                # Generate report if completed successfully
                self.generate_report()
                self.print_status("Meeting recording completed successfully")
                
            except Exception as e:
                self.print_status(f"Error in bot execution: {str(e)}")
                raise  # Re-raise to trigger finally block
                
        except Exception as e:
            self.print_status(f"Critical error: {str(e)}")
            # Don't re-raise here to prevent double error reporting
        finally:
            # Ensure cleanup happens in all cases
            self.stop()
            self.print_status("Bot execution finished")

    def stop(self):
        """Enhanced stop method to handle all threads and services"""
        self.print_status("Initiating shutdown sequence...")
        self.should_stop = True  # Signal all threads to stop
        
        # Stop monitoring thread if running
        if hasattr(self, 'recording_thread') and self.recording_thread and self.recording_thread.is_alive():
            self.print_status("Stopping monitoring thread...")
            self.recording_thread.join(timeout=5)
        
        # Stop transcript thread if running
        if hasattr(self, 'transcript_thread') and self.transcript_thread and self.transcript_thread.is_alive():
            self.print_status("Stopping transcript service...")
            self.transcript_thread.join(timeout=2)
        
        # Stop emotion analysis if running
        if hasattr(self, 'emotion_thread') and self.emotion_thread and self.emotion_thread.is_alive():
            self.print_status("Stopping emotion analysis...")
            self.emotion_thread.join(timeout=2)
        
        # Clean up resources
        self.cleanup()
        self.print_status("Shutdown completed")

    def cleanup(self):
        """Clean up all resources"""
        self.print_status("Starting resource cleanup...")
        
        # Stop FFmpeg if running
        if hasattr(self, 'ffmpeg_process') and self.ffmpeg_process:
            try:
                if self.ffmpeg_process.poll() is None:
                    self.print_status("Terminating recording process...")
                    self.ffmpeg_process.terminate()
                    try:
                        self.ffmpeg_process.wait(timeout=3)
                    except subprocess.TimeoutExpired:
                        self.ffmpeg_process.kill()
            except Exception as e:
                self.print_status(f"Error terminating FFmpeg: {str(e)}")

        # Close browser if exists
        if hasattr(self, 'driver') and self.driver:
            try:
                self.print_status("Closing browser...")
                self.driver.quit()
            except Exception as e:
                self.print_status(f"Error closing browser: {str(e)}")
        
        self.print_status("Cleanup completed")