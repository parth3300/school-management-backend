import os
import time
import subprocess
import logging
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
import os
from dotenv import load_dotenv
load_dotenv()
RECORDINGS_DIR = os.environ.get('RECORDINGS_DIR')
logger = logging.getLogger(__name__)

class MeetBot:
    def __init__(self, email, password, meeting_link, filename):
        self.email = email
        self.password = password
        self.meeting_link = meeting_link
        self.filename = filename
        self.driver = None
        self.recording_process = None
        self.recording_path = f"{RECORDINGS_DIR}/{filename}.mkv"
        
        # Ensure recordings directory exists
        os.makedirs("recordings", exist_ok=True)

    def setup_driver(self):
        """Configure and initialize Chrome WebDriver"""
        logger.info("Setting up Chrome WebDriver...")
        
        options = Options()
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--window-size=1366,768")
        options.add_argument("--disable-gpu")
        options.add_argument("--display=:99")
        
        self.driver = webdriver.Chrome(
            service=Service(ChromeDriverManager().install()), 
            options=options
        )
        logger.info("WebDriver setup complete")

    def login_to_google(self):
        """Login to Google account"""
        logger.info("Logging in to Google account...")
        
        self.driver.get("https://accounts.google.com/")
        time.sleep(2)

        try:
            # Enter email
            email_input = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.ID, "identifierId"))
            )
            email_input.send_keys(self.email)
            email_input.send_keys(Keys.ENTER)
            logger.info("Email entered")

            # Enter password
            password_input = WebDriverWait(self.driver, 15).until(
                EC.presence_of_element_located((By.NAME, "Passwd"))
            )
            password_input.send_keys(self.password)
            password_input.send_keys(Keys.ENTER)
            logger.info("Password entered")

            # Wait for login to complete
            WebDriverWait(self.driver, 15).until(
                EC.url_contains("myaccount.google.com"))
            logger.info("✅ Successfully logged into Google")

        except Exception as e:
            logger.error(f"❌ Failed to login: {e}")
            self.driver.save_screenshot("login_error.png")
            raise

    def join_meeting(self):
        """Join the Google Meet meeting"""
        logger.info("Joining Google Meet...")
        
        self.driver.get(self.meeting_link)
        logger.info(f"📞 Navigating to meeting link: {self.meeting_link}")
        
        WebDriverWait(self.driver, 15).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        time.sleep(5)

        wait = WebDriverWait(self.driver, 20)

        try:
            # Click "Cancel" button if present
            no_mic_btn = wait.until(
                EC.presence_of_element_located((By.XPATH, "//span[contains(text(),'Cancel')]")))
            no_mic_btn.click()
            logger.info("✅ Clicked 'Cancel' button")
        except Exception as e:
            logger.warning(f"❌ No Cancel button found: {e}")
            self.driver.save_screenshot("cancel_button_error.png")

        try:
            # Click "Continue without microphone" if present
            no_mic_btn = wait.until(
                EC.element_to_be_clickable((By.XPATH, "//span[contains(text(),'Continue without microphone')]")))
            no_mic_btn.click()
            logger.info("✅ Clicked 'Continue without microphone'")
        except Exception as e:
            logger.warning(f"❌ No microphone button found: {e}")

        # Join the meeting
        try:
            join_btn = self.driver.find_element(By.XPATH, "//span[contains(text(),'Join now')]")
            join_btn.click()
            logger.info("🚀 Successfully joined the meeting")
        except Exception as e:
            logger.error(f"❌ Could not join the meeting: {e}")
            raise

    def start_recording(self):
        """Start screen and audio recording with FFmpeg"""
        logger.info("🎬 Starting FFmpeg recording...")
        
        ffmpeg_cmd = [
            "ffmpeg", "-y",
            "-f", "x11grab", "-framerate", "25",
            "-video_size", "1366x768", "-i", ":99.0",
            "-f", "pulse", "-i", "alsa_output.usb-ZhuHai_JieLi_Technology_JieLi_BR21_20180105-01.analog-stereo.monitor",
            "-c:v", "libx264", "-preset", "ultrafast", "-pix_fmt", "yuv420p",
            "-c:a", "aac", "-b:a", "128k",
            "-shortest", self.recording_path
        ]

        self.recording_process = subprocess.Popen(ffmpeg_cmd)
        logger.info(f"Recording started. Saving to: {self.recording_path}")

    def monitor_participants(self, timeout_minutes=120):
        """Monitor meeting participants and stop when meeting ends"""
        logger.info("👥 Starting participant monitoring...")
        
        only_bot_timer_started = False
        bot_alone_start_time = None
        start_time = time.time()
        timeout_seconds = timeout_minutes * 60

        while True:
            try:
                # Check if we've exceeded the maximum meeting duration
                if time.time() - start_time > timeout_seconds:
                    logger.info("⏰ Maximum meeting duration reached")
                    break

                # Open participants panel
                people_button = WebDriverWait(self.driver, 20).until(
                    EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="People"]'))
                )
                people_button.click()

                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located((By.XPATH, '//div[@aria-label="Participants"]'))
                )

                # Get list of participants
                participants = self.driver.find_elements(By.XPATH, '//div[@role="listitem"]')
                participant_count = len(participants)
                logger.debug(f"Current participant count: {participant_count}")

                if participant_count <= 1:
                    if not only_bot_timer_started:
                        logger.info("🟡 Only bot is present. Starting 30 second grace period...")
                        bot_alone_start_time = time.time()
                        only_bot_timer_started = True
                    else:
                        elapsed = time.time() - bot_alone_start_time
                        logger.info(f"⏳ Waiting for participants... {int(elapsed)}s elapsed")

                        if elapsed >= 30:
                            logger.info("❌ No participants joined in 30 seconds.")
                            break
                else:
                    if only_bot_timer_started:
                        logger.info("🟢 Participants joined! Continuing recording.")
                        only_bot_timer_started = False
                        bot_alone_start_time = None

                time.sleep(10)

            except Exception as e:
                logger.error(f"⚠️ Error during participant check: {e}")
                break

    def run(self):
        """Main execution method"""
        try:
            self.setup_driver()
            self.login_to_google()
            self.join_meeting()
            self.start_recording()
            self.monitor_participants()
            
        except Exception as e:
            logger.error(f"❌ Error during bot execution: {e}")
            raise
            
        finally:
            # Stop recording
            if self.recording_process:
                self.recording_process.terminate()
                logger.info(f"✅ Recording saved: {self.recording_path}")

            # Leave meeting
            try:
                if self.driver:
                    leave_button = WebDriverWait(self.driver, 10).until(
                        EC.element_to_be_clickable((By.XPATH, '//button[@aria-label="Leave call"]'))
                    )
                    leave_button.click()
                    logger.info("👋 Bot has left the meeting")
                    time.sleep(2)
            except Exception as e:
                logger.warning(f"⚠️ Could not properly leave meeting: {e}")

            # Close browser
            if self.driver:
                self.driver.quit()
                logger.info("✅ Browser closed")

        return True