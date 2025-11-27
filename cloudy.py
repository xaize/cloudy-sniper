import customtkinter as ctk
from tkinter import messagebox
import threading
import discord
from discord.ext import commands
from datetime import datetime
import re
from http.server import HTTPServer, BaseHTTPRequestHandler
import json
import time
import asyncio
from functools import partial
import concurrent.futures
import sys
from PIL import Image, ImageDraw, ImageFilter
import io
import random
import math
import os
import urllib.request
import urllib.error


# Set the appearance mode and default color theme
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


# === AUTO-UPDATER CONFIGURATION ===
CURRENT_VERSION = "2.3.1"
# CHANGE THESE TO YOUR GITHUB REPO
GITHUB_USER = "xaize"
GITHUB_REPO = "cloudy-sniper"
GITHUB_BRANCH = "main"
VERSION_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/version.txt"
CODE_URL = f"https://raw.githubusercontent.com/{GITHUB_USER}/{GITHUB_REPO}/{GITHUB_BRANCH}/cloudy.py"
# ==================================


class AutoUpdater:
    """Handles automatic updates from GitHub."""
    
    @staticmethod
    def check_for_updates():
        """Check if a new version is available."""
        try:
            req = urllib.request.Request(VERSION_URL, headers={'User-Agent': 'Cloudy-Updater'})
            with urllib.request.urlopen(req, timeout=5) as response:
                remote_version = response.read().decode('utf-8').strip()
                
                if AutoUpdater._compare_versions(remote_version, CURRENT_VERSION) > 0:
                    return True, remote_version
                return False, remote_version
        except:
            return False, None
    
    @staticmethod
    def _compare_versions(v1, v2):
        """Compare two version strings."""
        try:
            parts1 = [int(x) for x in v1.split('.')]
            parts2 = [int(x) for x in v2.split('.')]
            
            while len(parts1) < 3:
                parts1.append(0)
            while len(parts2) < 3:
                parts2.append(0)
            
            for i in range(3):
                if parts1[i] > parts2[i]:
                    return 1
                elif parts1[i] < parts2[i]:
                    return -1
            return 0
        except:
            return 0
    
    @staticmethod
    def download_and_update():
        """Download new code and save it."""
        try:
            # Download new code
            req = urllib.request.Request(CODE_URL, headers={'User-Agent': 'Cloudy-Updater'})
            with urllib.request.urlopen(req, timeout=30) as response:
                new_code = response.read().decode('utf-8')
            
            # Get the path to save updated code
            if getattr(sys, 'frozen', False):
                # Running as exe - save next to exe
                exe_dir = os.path.dirname(sys.executable)
                code_path = os.path.join(exe_dir, "cloudy_code.py")
            else:
                # Running as script - update the script itself
                code_path = os.path.abspath(sys.argv[0])
            
            # Save new code
            with open(code_path, 'w', encoding='utf-8') as f:
                f.write(new_code)
            
            return True
            
        except:
            return False
    
    @staticmethod
    def restart_app():
        """Restart the application."""
        try:
            if getattr(sys, 'frozen', False):
                # Running as exe
                os.execv(sys.executable, [sys.executable])
            else:
                # Running as script
                os.execv(sys.executable, [sys.executable] + sys.argv)
        except:
            pass


# === LOGIN SCREEN CLASS ===
class CloudyLoginScreen:
    """Beautiful animated login screen with Discord token authentication."""
    
    # === CONFIGURATION - CHANGE THESE VALUES ===
    REQUIRED_GUILD_ID = 1436696093726609410  # Your Discord Server ID
    REQUIRED_ROLE_ID = 1443353853880832031   # Required Role ID to access
    SESSION_DURATION = 3600  # Session duration in seconds (1 hour = 3600)
    # ============================================
    
    def __init__(self, root, on_login_success):
        self.root = root
        self.on_login_success = on_login_success
        self.frame = None
        
        # Check for valid session first
        session_data = self._check_existing_session()
        if session_data:
            # Valid session exists, skip login
            self.root.after(100, lambda: on_login_success(session_data['token']))
            return
        
        # Animation states - use floats for smooth interpolation
        self.cloud_float_offset = 0.0
        self.title_glow_phase = 0.0
        self.card_glow_phase = 0.0
        self.particles = []
        self.is_validating = False
        self.fade_alpha = 0.0
        
        # Animation timing
        self.last_frame_time = time.time()
        self.target_fps = 60
        self.frame_time = 1.0 / self.target_fps
        
        # Smooth animation values (current, target, velocity)
        self.cloud_y_current = 0.0
        self.cloud_y_velocity = 0.0
        
        # Validation thread
        self.validation_thread = None
        self.validation_cancelled = False
        
        # Initialize particles
        for _ in range(12):
            self.particles.append({
                'x': random.uniform(0, 1200),
                'y': random.uniform(0, 700),
                'size': random.uniform(3, 8),
                'speed': random.uniform(0.3, 1.0),
                'opacity': random.uniform(0.1, 0.4)
            })
        
        self._create_login_ui()
        self._start_smooth_animations()
    
    def _check_existing_session(self):
        """Check if a valid session exists (not expired)."""
        try:
            if os.path.exists("cloudy_session.json"):
                with open("cloudy_session.json", "r") as f:
                    session = json.load(f)
                    
                    # Check if session has required fields
                    if 'token' in session and 'timestamp' in session and 'username' in session:
                        # Check if session is still valid (within SESSION_DURATION)
                        elapsed = time.time() - session['timestamp']
                        if elapsed < self.SESSION_DURATION:
                            remaining = int((self.SESSION_DURATION - elapsed) / 60)
                            # Valid session found
                            return session
                        else:
                            # Session expired, requiring new login
                            os.remove("cloudy_session.json")
        except Exception as e:
            pass
        
        return None
    
    def _save_session(self, token, username):
        """Save session with timestamp."""
        try:
            session = {
                'token': token,
                'username': username,
                'timestamp': time.time()
            }
            with open("cloudy_session.json", "w") as f:
                json.dump(session, f)
        except Exception as e:
            pass  # Silent fail
    
    @staticmethod
    def clear_session():
        """Clear the saved session (for logout)."""
        try:
            if os.path.exists("cloudy_session.json"):
                os.remove("cloudy_session.json")
        except:
            pass
    
    def _create_cloud_logo(self, parent, size=100):
        """Create a larger cloud logo for login screen."""
        img_size = 150
        image = Image.new('RGBA', (img_size, img_size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        s = 0.6  # Scale factor
        
        # Outer glow (cyan/blue)
        for i in range(3):
            glow_color = (100, 180, 255, 30 - i * 8)
            offset = i * 3
            draw.ellipse([int(55*s)-offset, int(80*s)-offset, int(195*s)+offset, int(170*s)+offset], fill=glow_color)
            draw.ellipse([int(35*s)-offset, int(95*s)-offset, int(115*s)+offset, int(160*s)+offset], fill=glow_color)
            draw.ellipse([int(135*s)-offset, int(95*s)-offset, int(215*s)+offset, int(160*s)+offset], fill=glow_color)
            draw.ellipse([int(70*s)-offset, int(55*s)-offset, int(140*s)+offset, int(125*s)+offset], fill=glow_color)
            draw.ellipse([int(110*s)-offset, int(55*s)-offset, int(180*s)+offset, int(125*s)+offset], fill=glow_color)
        
        # Apply blur for glow
        image = image.filter(ImageFilter.GaussianBlur(radius=8))
        
        # Main cloud (white with slight blue tint)
        draw = ImageDraw.Draw(image)
        cloud_color = (240, 248, 255, 255)
        draw.ellipse([int(60*s), int(85*s), int(190*s), int(165*s)], fill=cloud_color)
        draw.ellipse([int(40*s), int(100*s), int(110*s), int(155*s)], fill=cloud_color)
        draw.ellipse([int(140*s), int(100*s), int(210*s), int(155*s)], fill=cloud_color)
        draw.ellipse([int(75*s), int(60*s), int(135*s), int(120*s)], fill=cloud_color)
        draw.ellipse([int(115*s), int(60*s), int(175*s), int(120*s)], fill=cloud_color)
        
        # Soft blur
        image = image.filter(ImageFilter.GaussianBlur(radius=1))
        
        ctk_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=(size, size)
        )
        
        label = ctk.CTkLabel(parent, image=ctk_image, text="")
        label.image = ctk_image
        return label
    
    def _create_login_ui(self):
        """Create the login screen UI."""
        self.frame = ctk.CTkFrame(self.root, fg_color="#0a0f1a", corner_radius=0)
        self.frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Main container (centered)
        self.container = ctk.CTkFrame(self.frame, fg_color="transparent")
        self.container.place(relx=0.5, rely=0.5, anchor="center")
        
        # Cloud logo container (for floating animation)
        self.logo_container = ctk.CTkFrame(self.container, fg_color="transparent", height=130)
        self.logo_container.pack(pady=(0, 8))
        self.logo_container.pack_propagate(False)
        
        # Inner frame for smooth positioning
        self.logo_inner = ctk.CTkFrame(self.logo_container, fg_color="transparent")
        self.logo_inner.place(relx=0.5, rely=0.5, anchor="center")
        
        self.cloud_logo = self._create_cloud_logo(self.logo_inner, size=110)
        self.cloud_logo.pack()
        
        # Title with glow effect
        self.title_label = ctk.CTkLabel(
            self.container,
            text="Cloudy",
            font=("Segoe UI", 42, "bold"),
            text_color="#e0f0ff"
        )
        self.title_label.pack(pady=(0, 3))
        
        # Subtitle
        self.subtitle_label = ctk.CTkLabel(
            self.container,
            text="Job Drop Sniper",
            font=("Segoe UI", 14),
            text_color="#5a7a9a"
        )
        self.subtitle_label.pack(pady=(0, 25))
        
        # Login card - FIXED SIZE to prevent expansion
        self.login_card = ctk.CTkFrame(
            self.container,
            fg_color="#111827",
            corner_radius=16,
            border_width=2,
            border_color="#1e3a5f",
            width=390,
            height=340
        )
        self.login_card.pack(padx=25, pady=8)
        self.login_card.pack_propagate(False)  # Prevent size changes
        
        # Card inner content
        card_inner = ctk.CTkFrame(self.login_card, fg_color="transparent")
        card_inner.pack(padx=35, pady=25, fill="both", expand=True)
        
        # Welcome text - WHITE color
        ctk.CTkLabel(
            card_inner,
            text="Welcome Back",
            font=("Segoe UI", 20, "bold"),
            text_color="#ffffff"
        ).pack(anchor="w", pady=(0, 4))
        
        ctk.CTkLabel(
            card_inner,
            text="Enter your Discord token to continue",
            font=("Segoe UI", 12),
            text_color="#94a3b8"
        ).pack(anchor="w", pady=(0, 18))
        
        # Token input label
        ctk.CTkLabel(
            card_inner,
            text="🔑  Discord Token",
            font=("Segoe UI", 12, "bold"),
            text_color="#cbd5e1"
        ).pack(anchor="w", pady=(0, 8))
        
        # Token entry with icon
        entry_frame = ctk.CTkFrame(card_inner, fg_color="transparent")
        entry_frame.pack(fill="x", pady=(0, 6))
        
        self.token_entry = ctk.CTkEntry(
            entry_frame,
            width=320,
            height=42,
            corner_radius=10,
            font=("Segoe UI", 13),
            placeholder_text="Paste your token here...",
            border_width=2,
            border_color="#1e3a5f",
            fg_color="#0a1628",
            show="•"
        )
        self.token_entry.pack(fill="x")
        
        # Show/Hide toggle
        self.show_token = False
        self.toggle_btn = ctk.CTkButton(
            entry_frame,
            text="👁",
            width=36,
            height=36,
            corner_radius=8,
            fg_color="transparent",
            hover_color="#1e3a5f",
            font=("Segoe UI", 15),
            command=self._toggle_token_visibility
        )
        self.toggle_btn.place(relx=1.0, rely=0.5, anchor="e", x=-4)
        
        # Remember me checkbox
        self.remember_var = ctk.BooleanVar(value=True)
        self.remember_check = ctk.CTkCheckBox(
            card_inner,
            text="Remember my token",
            font=("Segoe UI", 12),
            text_color="#94a3b8",
            fg_color="#3b82f6",
            hover_color="#2563eb",
            border_color="#1e3a5f",
            checkbox_height=20,
            checkbox_width=20,
            variable=self.remember_var
        )
        self.remember_check.pack(anchor="w", pady=(10, 18))
        
        # Login button
        self.login_btn = ctk.CTkButton(
            card_inner,
            text="Continue",
            height=44,
            corner_radius=10,
            font=("Segoe UI", 14, "bold"),
            fg_color="#3b82f6",
            hover_color="#2563eb",
            text_color="#ffffff",
            text_color_disabled="#ffffff",
            command=self._validate_and_login
        )
        self.login_btn.pack(fill="x", pady=(0, 12))
        
        # Status label (for errors/loading)
        self.status_label = ctk.CTkLabel(
            card_inner,
            text="",
            font=("Segoe UI", 11),
            text_color="#ef4444",
            wraplength=300
        )
        self.status_label.pack()
        
        # Loading spinner frame (hidden initially)
        self.loading_frame = ctk.CTkFrame(card_inner, fg_color="transparent")
        self.spinner_dots = []
        self.spinner_phase = 0.0
        for i in range(3):
            dot = ctk.CTkLabel(
                self.loading_frame,
                text="●",
                font=("Segoe UI", 16),
                text_color="#3b82f6"
            )
            dot.pack(side="left", padx=4)
            self.spinner_dots.append(dot)
        
        # Version info at bottom - directly on main frame, not affected by card
        self.version_label = ctk.CTkLabel(
            self.frame,
            text=f"v{CURRENT_VERSION} • Role-Based Access",
            font=("Segoe UI", 11),
            text_color="#3a4a5a"
        )
        self.version_label.place(relx=0.5, rely=0.97, anchor="center")
        
        # Load saved token if exists
        self._load_saved_token()
    
    def _toggle_token_visibility(self):
        """Toggle between showing and hiding the token."""
        self.show_token = not self.show_token
        if self.show_token:
            self.token_entry.configure(show="")
            self.toggle_btn.configure(text="🔒")
        else:
            self.token_entry.configure(show="•")
            self.toggle_btn.configure(text="👁")
    
    def _load_saved_token(self):
        """Load saved token from file."""
        try:
            if os.path.exists("discord_token.txt"):
                with open("discord_token.txt", "r") as f:
                    token = f.read().strip()
                    if token:
                        self.token_entry.insert(0, token)
        except Exception:
            pass
    
    def _save_token(self, token):
        """Save token to file."""
        try:
            with open("discord_token.txt", "w") as f:
                f.write(token)
        except Exception:
            pass
    
    def _validate_and_login(self):
        """Validate the token and check for required role."""
        if self.is_validating:
            return
        
        token = self.token_entry.get().strip()
        
        if not token:
            self._show_error("Please enter your Discord token")
            self._shake_entry()
            return
        
        if len(token) < 50:
            self._show_error("Token appears to be invalid (too short)")
            self._shake_entry()
            return
        
        # Show loading state
        self.is_validating = True
        self.validation_cancelled = False
        self.login_btn.configure(text="Connecting to Discord...", state="disabled")
        self.status_label.configure(text="", text_color="#3b82f6")
        self.loading_frame.pack(pady=(10, 0))
        
        # Start validation in background thread
        self.validation_thread = threading.Thread(
            target=self._validate_discord_token,
            args=(token,),
            daemon=True
        )
        self.validation_thread.start()
    
    def _validate_discord_token(self, token):
        """Validate Discord token and check for required role (runs in thread)."""
        
        async def check_token():
            client = discord.Client()
            validation_result = {"success": False, "error": None, "username": None}
            
            @client.event
            async def on_ready():
                try:
                    # Get the required guild
                    guild = client.get_guild(self.REQUIRED_GUILD_ID)
                    
                    if guild is None:
                        validation_result["error"] = "You are not a member of the required server"
                        await client.close()
                        return
                    
                    # Get the member object
                    member = guild.get_member(client.user.id)
                    
                    if member is None:
                        # Try to fetch member if not in cache
                        try:
                            member = await guild.fetch_member(client.user.id)
                        except:
                            validation_result["error"] = "Could not verify server membership"
                            await client.close()
                            return
                    
                    # Check if user has the required role
                    has_role = any(role.id == self.REQUIRED_ROLE_ID for role in member.roles)
                    
                    if has_role:
                        validation_result["success"] = True
                        validation_result["username"] = str(client.user)
                    else:
                        validation_result["error"] = "You don't have the required role to access Cloudy"
                    
                    await client.close()
                    
                except Exception as e:
                    validation_result["error"] = f"Verification failed: {str(e)}"
                    await client.close()
            
            try:
                await asyncio.wait_for(client.start(token), timeout=15.0)
            except discord.errors.LoginFailure:
                validation_result["error"] = "Invalid Discord token"
            except asyncio.TimeoutError:
                validation_result["error"] = "Connection timed out"
                try:
                    await client.close()
                except:
                    pass
            except Exception as e:
                validation_result["error"] = f"Connection error: {str(e)}"
                try:
                    await client.close()
                except:
                    pass
            
            return validation_result
        
        # Run the async validation
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            result = loop.run_until_complete(check_token())
        except Exception as e:
            result = {"success": False, "error": f"Unexpected error: {str(e)}", "username": None}
        finally:
            loop.close()
        
        # Update UI on main thread
        if not self.validation_cancelled:
            self.root.after(0, lambda: self._handle_validation_result(result, token))
    
    def _handle_validation_result(self, result, token):
        """Handle the validation result on the main thread."""
        self.is_validating = False
        self.loading_frame.pack_forget()
        
        if result["success"]:
            # Save token if remember is checked
            if self.remember_var.get():
                self._save_token(token)
            
            # Save session for auto-login (1 hour)
            self._save_session(token, result['username'])
            
            self.login_btn.configure(text=f"✓ Welcome, {result['username']}!", fg_color="#10b981", text_color="#ffffff")
            self.status_label.configure(text="Access granted! Launching...", text_color="#10b981")
            
            # Fade out animation
            self.root.after(1200, lambda: self._fade_out(token))
        else:
            self.login_btn.configure(text="Continue", state="normal", fg_color="#3b82f6")
            self._show_error(result["error"])
            self._shake_entry()
    
    def _show_error(self, message):
        """Display error message with animation."""
        self.status_label.configure(text=message, text_color="#ef4444")
    
    def _shake_entry(self):
        """Shake animation for invalid input."""
        self.token_entry.configure(border_color="#ef4444")
        self.root.after(500, lambda: self.token_entry.configure(border_color="#1e3a5f"))
    
    def _lerp(self, start, end, t):
        """Linear interpolation for smooth animations."""
        return start + (end - start) * t
    
    def _ease_in_out(self, t):
        """Smooth ease-in-out function."""
        return t * t * (3 - 2 * t)
    
    def _start_smooth_animations(self):
        """Start the unified smooth animation loop."""
        self._animation_loop()
    
    def _animation_loop(self):
        """Main animation loop running at consistent FPS."""
        current_time = time.time()
        delta_time = current_time - self.last_frame_time
        self.last_frame_time = current_time
        
        # Cap delta time to prevent jumps
        delta_time = min(delta_time, 0.1)
        
        # Update animation phases
        self.cloud_float_offset += delta_time * 1.5  # Speed of floating
        self.title_glow_phase += delta_time * 1.2    # Speed of title glow
        self.card_glow_phase += delta_time * 1.8     # Speed of card border
        
        # === CLOUD FLOATING ANIMATION ===
        target_y = math.sin(self.cloud_float_offset) * 10
        # Smooth interpolation
        self.cloud_y_current = self._lerp(self.cloud_y_current, target_y, delta_time * 5)
        
        try:
            self.logo_inner.place(relx=0.5, rely=0.5 + (self.cloud_y_current / 180), anchor="center")
        except:
            pass
        
        # === TITLE GLOW ANIMATION ===
        intensity = 0.5 + 0.5 * math.sin(self.title_glow_phase)
        # Smoother color transitions
        r = int(self._lerp(180, 250, intensity))
        g = int(self._lerp(210, 250, intensity))
        b = int(self._lerp(235, 255, intensity))
        
        try:
            self.title_label.configure(text_color=f"#{r:02x}{g:02x}{b:02x}")
        except:
            pass
        
        # === CARD BORDER GLOW ANIMATION ===
        card_intensity = 0.5 + 0.5 * math.sin(self.card_glow_phase)
        cr = int(self._lerp(30, 70, card_intensity))
        cg = int(self._lerp(58, 140, card_intensity))
        cb = int(self._lerp(95, 200, card_intensity))
        
        try:
            self.login_card.configure(border_color=f"#{cr:02x}{cg:02x}{cb:02x}")
        except:
            pass
        
        # === SPINNER ANIMATION ===
        if self.is_validating:
            self.spinner_phase += delta_time * 4
            for i, dot in enumerate(self.spinner_dots):
                # Offset each dot's phase
                dot_phase = self.spinner_phase + (i * 0.5)
                dot_intensity = 0.5 + 0.5 * math.sin(dot_phase)
                
                r = int(self._lerp(59, 147, dot_intensity))
                g = int(self._lerp(130, 197, dot_intensity))
                b = int(self._lerp(246, 253, dot_intensity))
                
                try:
                    dot.configure(text_color=f"#{r:02x}{g:02x}{b:02x}")
                except:
                    pass
        
        # Schedule next frame (targeting 60 FPS)
        self.root.after(16, self._animation_loop)  # ~60 FPS
    
    def _login_success(self, token):
        """Handle successful login - transition to main app."""
        self.is_validating = False
        self.loading_frame.pack_forget()
        self.login_btn.configure(text="✓ Success!", fg_color="#10b981")
        self.status_label.configure(text="Launching Cloudy...", text_color="#10b981")
        
        # Fade out animation
        self.root.after(800, lambda: self._fade_out(token))
    
    def _fade_out(self, token):
        """Smooth fade out the login screen."""
        self.fade_alpha += 0.05  # Slower, smoother fade
        
        if self.fade_alpha < 1.0:
            # Smooth eased fade
            eased_alpha = self._ease_in_out(self.fade_alpha)
            darkness = int(10 + (eased_alpha * 15))
            color = f"#{darkness:02x}{darkness:02x}{int(darkness*1.2):02x}"
            try:
                self.frame.configure(fg_color=color)
            except:
                pass
            self.root.after(16, lambda: self._fade_out(token))  # 60 FPS
        else:
            # Destroy login and launch main app
            self.frame.destroy()
            self.on_login_success(token)

# === HTTP SERVER – SENDS JOB ID TO YOUR EXECUTOR ===
latest_drop = {
    "job": "",
    "name": "",
    "ms": 0.0,
    "players": "",
    "timestamp": 0
}

class HTTPHandler(BaseHTTPRequestHandler):
    """Handles HTTP requests to serve the latest drop data."""
    def log_message(self, format, *args):
        pass  # Disable HTTP request logging
    
    def do_GET(self):
        global latest_drop
        if self.path == "/latest":
            self.send_response(200)
            self.send_header("Content-type", "application/json")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            
            # Auto-clear drop after 10 seconds (prevents accidental re-joining)
            if latest_drop["timestamp"] > 0 and (time.time() - latest_drop["timestamp"]) > 10:
                latest_drop = {"job": "", "name": "", "ms": 0.0, "players": "", "timestamp": 0}
            
            self.wfile.write(json.dumps(latest_drop).encode())

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET")
        self.end_headers()

def run_http_server():
    """Starts the HTTP server in the main thread (blocking call)."""
    server_address = ("127.0.0.1", 8080)
    httpd = HTTPServer(server_address, HTTPHandler)
    httpd.serve_forever()


# === FLOATING CLOUD PARTICLE ===
class CloudParticle:
    """A floating cloud particle for background ambiance."""
    def __init__(self, canvas_width, canvas_height):
        self.x = random.uniform(0, canvas_width)
        self.y = random.uniform(0, canvas_height)
        self.size = random.uniform(20, 60)
        self.speed = random.uniform(0.2, 0.8)
        self.opacity = random.uniform(0.1, 0.3)
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height
        
    def update(self):
        self.x += self.speed
        if self.x > self.canvas_width + self.size:
            self.x = -self.size
            self.y = random.uniform(0, self.canvas_height)


# === NOTIFICATION TOAST CLASS ===
class NotificationToast(ctk.CTkFrame):
    """Animated notification toast that slides in and out."""
    def __init__(self, parent, message, notification_type="info", on_destroy=None, start_y=15):
        super().__init__(parent, corner_radius=12, fg_color="#1e293b", border_width=2, width=300, height=52)
        
        self.on_destroy_callback = on_destroy
        self.is_animating = False
        self.is_destroyed = False
        self.target_y = start_y
        self.current_y = start_y
        
        # Prevent frame from shrinking
        self.pack_propagate(False)
        
        # Color scheme based on type
        colors = {
            "info": ("#3b82f6", "ℹ"),
            "success": ("#10b981", "✓"),
            "error": ("#ef4444", "✗"),
            "warning": ("#f59e0b", "⚠")
        }
        
        color, icon = colors.get(notification_type, colors["info"])
        self.configure(border_color=color)
        
        # Content container
        content_frame = ctk.CTkFrame(self, fg_color="transparent")
        content_frame.pack(fill="both", expand=True, padx=4, pady=4)
        
        # Icon
        icon_label = ctk.CTkLabel(
            content_frame,
            text=icon,
            font=("Segoe UI", 16, "bold"),
            text_color=color,
            width=26
        )
        icon_label.pack(side="left", padx=(10, 6))
        
        # Message
        msg_label = ctk.CTkLabel(
            content_frame,
            text=message,
            font=("Segoe UI", 11, "bold"),
            text_color="#f1f5f9",
            anchor="w"
        )
        msg_label.pack(side="left", fill="x", expand=True, padx=(0, 10))
        
        # Store parent width
        self.parent_width = parent.winfo_width()
        
        # Start off-screen
        self.current_x = self.parent_width + 10
        self.place(x=self.current_x, y=self.target_y, anchor="nw")
        
        # Animate in after a brief delay
        self.after(50, self.animate_in)
    
    def set_target_y(self, new_y):
        """Update target Y position for smooth repositioning."""
        self.target_y = new_y
        
    def animate_in(self):
        """Smooth slide in animation from right."""
        if self.is_destroyed:
            return
            
        target_x = self.parent_width - 310
        
        # Smooth interpolation
        self.current_x += (target_x - self.current_x) * 0.15
        self.current_y += (self.target_y - self.current_y) * 0.15
        
        try:
            self.place(x=self.current_x, y=self.current_y, anchor="nw")
        except:
            return
        
        # Continue animating until close to target
        if abs(self.current_x - target_x) > 1:
            self.after(16, self.animate_in)
        else:
            self.current_x = target_x
            self.place(x=self.current_x, y=self.current_y, anchor="nw")
            # Start idle animation (keeps updating Y position)
            self.after(16, self.idle_animation)
            # Schedule fade out
            self.after(2500, self.animate_out)
    
    def idle_animation(self):
        """Keep updating Y position while visible."""
        if self.is_destroyed or self.is_animating:
            return
        
        # Smoothly move to target Y
        if abs(self.current_y - self.target_y) > 0.5:
            self.current_y += (self.target_y - self.current_y) * 0.15
            try:
                self.place(x=self.current_x, y=self.current_y, anchor="nw")
            except:
                return
        
        self.after(16, self.idle_animation)
    
    def animate_out(self):
        """Smooth slide out animation to right."""
        if self.is_destroyed:
            return
        self.is_animating = True
        
        target_x = self.parent_width + 10
        
        # Smooth interpolation
        self.current_x += (target_x - self.current_x) * 0.12
        
        try:
            self.place(x=self.current_x, y=self.current_y, anchor="nw")
        except:
            self._cleanup()
            return
        
        # Continue animating until off screen
        if abs(self.current_x - target_x) > 1:
            self.after(16, self.animate_out)
        else:
            self._cleanup()
    
    def _cleanup(self):
        """Clean up the notification."""
        if self.is_destroyed:
            return
        self.is_destroyed = True
        
        if self.on_destroy_callback:
            try:
                self.on_destroy_callback(self)
            except:
                pass
        
        try:
            self.destroy()
        except:
            pass


# === ANIMATED STATUS INDICATOR ===
class PulsingStatusIndicator(ctk.CTkFrame):
    """A pulsing status indicator with glow effect."""
    def __init__(self, parent, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        
        self.status = "disconnected"  # disconnected, connecting, connected
        self.pulse_phase = 0
        self.glow_intensity = 0
        
        # Create canvas for custom drawing
        self.canvas = ctk.CTkCanvas(self, width=24, height=24, bg="#1a1a2e", highlightthickness=0)
        self.canvas.pack()
        
        self.animate_pulse()
    
    def set_status(self, status):
        """Set the status: 'disconnected', 'connecting', or 'connected'"""
        self.status = status
        
    def animate_pulse(self):
        """Animate the pulsing effect."""
        self.pulse_phase += 0.15
        
        # Calculate glow based on status
        if self.status == "connected":
            # Smooth breathing glow
            self.glow_intensity = 0.5 + 0.5 * math.sin(self.pulse_phase)
            color = self._interpolate_color("#10b981", "#34d399", self.glow_intensity)
            glow_color = self._interpolate_color("#10b98133", "#34d39966", self.glow_intensity)
        elif self.status == "connecting":
            # Fast pulsing yellow
            self.glow_intensity = 0.5 + 0.5 * math.sin(self.pulse_phase * 2)
            color = self._interpolate_color("#f59e0b", "#fbbf24", self.glow_intensity)
            glow_color = self._interpolate_color("#f59e0b33", "#fbbf2466", self.glow_intensity)
        else:
            # Static red
            color = "#ef4444"
            glow_color = "#ef444433"
        
        # Clear and redraw
        self.canvas.delete("all")
        
        # Draw glow (outer circle)
        glow_size = 4 + (4 * self.glow_intensity) if self.status != "disconnected" else 2
        self.canvas.create_oval(
            12 - 8 - glow_size, 12 - 8 - glow_size,
            12 + 8 + glow_size, 12 + 8 + glow_size,
            fill=glow_color, outline=""
        )
        
        # Draw main indicator
        self.canvas.create_oval(8, 8, 16, 16, fill=color, outline="")
        
        self.after(50, self.animate_pulse)
    
    def _interpolate_color(self, color1, color2, factor):
        """Interpolate between two hex colors."""
        # Handle colors with alpha
        c1 = color1.lstrip('#')
        c2 = color2.lstrip('#')
        
        if len(c1) == 8:
            r1, g1, b1, a1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16), int(c1[6:8], 16)
            r2, g2, b2, a2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16), int(c2[6:8], 16)
            r = int(r1 + (r2 - r1) * factor)
            g = int(g1 + (g2 - g1) * factor)
            b = int(b1 + (b2 - b1) * factor)
            a = int(a1 + (a2 - a1) * factor)
            return f"#{r:02x}{g:02x}{b:02x}{a:02x}"
        else:
            r1, g1, b1 = int(c1[0:2], 16), int(c1[2:4], 16), int(c1[4:6], 16)
            r2, g2, b2 = int(c2[0:2], 16), int(c2[2:4], 16), int(c2[4:6], 16)
            r = int(r1 + (r2 - r1) * factor)
            g = int(g1 + (g2 - g1) * factor)
            b = int(b1 + (b2 - b1) * factor)
            return f"#{r:02x}{g:02x}{b:02x}"


# === MAIN SNIPER CLASS ===
class CloudySniper:
    def __init__(self, root, token=None):
        self.root = root
        self.root.title("Cloudy - Job Drop Sniper")
        
        # Set custom background color (darker, cloudier blue)
        self.root.configure(fg_color="#0f172a")

        self.running = False
        self.drop_count = 0
        self.min_ms = 0.0
        self.discord_token = token or ""
        
        self.processed_jobs = set() 
        self.discord_client = None
        self.executor = None 
        
        # === FIX: State management with locks ===
        self.state_lock = threading.Lock()
        self.connection_state = "disconnected"  # disconnected, connecting, connected
        self.stop_requested = False
        self.discord_loop = None
        self.connection_id = 0  # Unique ID for each connection attempt
        self.buttons_locked = False  # Prevent rapid clicking
        self.last_action_time = 0  # Cooldown tracking
        self.ACTION_COOLDOWN = 2.0  # 2 second cooldown between actions
        
        # Animation states for gradient sweep
        self.gradient_offset = 0
        
        # Cloud particles for background
        self.cloud_particles = [CloudParticle(900, 700) for _ in range(6)]
        
        # Notification queue
        self.active_notifications = []
        
        # Connection animation phase
        self.connection_glow_phase = 0
        
        # Main container frame (for fade-in animation)
        self.main_frame = ctk.CTkFrame(self.root, fg_color="#0f172a", corner_radius=0)
        self.main_frame.place(relx=0, rely=0, relwidth=1, relheight=1)
        
        # Fade in animation state
        self.fade_in_alpha = 0

        # --- MODERN GUI SETUP ---
        self._create_background_canvas()
        self._create_header()
        self._create_stats_cards()
        self._create_controls()
        self._create_log_section()
        
        # Set token in entry if provided
        if token:
            self.token_entry.delete(0, 'end')
            self.token_entry.insert(0, token)
        
        # Start animations
        self.animate_gradient_sweep()
        self.animate_cloud_particles()
        self.animate_connection_glow()
        
        # Fade in the main UI
        self._fade_in_ui()

    def _create_background_canvas(self):
        """Create a canvas for background cloud particles."""
        # This is handled by the frame backgrounds - we'll animate opacity effects instead
        pass
    
    def _fade_in_ui(self):
        """Fade in the main UI smoothly."""
        self.fade_in_alpha += 0.08
        
        if self.fade_in_alpha < 1.0:
            # Gradually lighten from black to normal
            self.root.after(30, self._fade_in_ui)
        else:
            self.fade_in_alpha = 1.0
            self.show_notification("☁️ Welcome to Cloudy!", "success")

    def show_notification(self, message, notification_type="info"):
        """Display an animated notification toast with proper stacking."""
        # Limit max notifications on screen
        if len(self.active_notifications) >= 5:
            # Remove oldest notification
            oldest = self.active_notifications.pop(0)
            try:
                oldest.is_destroyed = True
                oldest.destroy()
            except:
                pass
        
        # Calculate Y position based on existing notifications
        y_position = 15 + (len(self.active_notifications) * 58)
        
        def on_notification_destroy(notification):
            if notification in self.active_notifications:
                self.active_notifications.remove(notification)
                # Reposition remaining notifications
                self._reposition_notifications()
        
        toast = NotificationToast(self.root, message, notification_type, on_notification_destroy, start_y=y_position)
        self.active_notifications.append(toast)
    
    def _reposition_notifications(self):
        """Reposition all active notifications to remove gaps."""
        for i, notification in enumerate(self.active_notifications):
            if not notification.is_destroyed:
                notification.set_target_y(15 + (i * 58))

    def animate_gradient_sweep(self):
        """Animate a gradient sweep effect like the Lua UIGradient."""
        self.gradient_offset += 0.015
        if self.gradient_offset > 2.0:
            self.gradient_offset = -1.0
        
        normalized_offset = (self.gradient_offset + 1) / 3.0
        
        if normalized_offset < 0.3:
            r, g, b = 200, 220, 255  # Light sky blue
        elif normalized_offset < 0.5:
            progress = (normalized_offset - 0.3) / 0.2
            r = int(200 - (200 - 100) * progress)
            g = int(220 - (220 - 150) * progress)
            b = int(255 - (255 - 200) * progress)
        elif normalized_offset < 0.7:
            progress = (normalized_offset - 0.5) / 0.2
            r = int(100 + (200 - 100) * progress)
            g = int(150 + (220 - 150) * progress)
            b = int(200 + (255 - 200) * progress)
        else:
            r, g, b = 200, 220, 255
        
        try:
            self.title_label.configure(text_color=f"#{r:02x}{g:02x}{b:02x}")
        except:
            pass
        
        self.root.after(40, self.animate_gradient_sweep)

    def animate_cloud_particles(self):
        """Animate floating cloud particles in the background."""
        for particle in self.cloud_particles:
            particle.update()
        
        # Update every 50ms for smooth animation
        self.root.after(50, self.animate_cloud_particles)

    def animate_connection_glow(self):
        """Animate connection status glow effect."""
        self.connection_glow_phase += 0.1
        
        with self.state_lock:
            state = self.connection_state
        
        if state == "connected":
            # Breathing glow effect - subtle color change
            intensity = 0.5 + 0.5 * math.sin(self.connection_glow_phase)
            r = int(16 + (52 - 16) * intensity)
            g = int(185 + (211 - 185) * intensity)
            b = int(129 + (153 - 129) * intensity)
            color = f"#{r:02x}{g:02x}{b:02x}"
            
            try:
                self.status.configure(text_color=color)
                # Also animate the status card border
                self.status_card.configure(border_color=color)
            except:
                pass
                
        elif state == "connecting":
            # Fast pulsing yellow/orange
            intensity = 0.5 + 0.5 * math.sin(self.connection_glow_phase * 3)
            r = int(245 + (251 - 245) * intensity)
            g = int(158 + (191 - 158) * intensity)
            b = int(11 + (36 - 11) * intensity)
            color = f"#{r:02x}{g:02x}{b:02x}"
            
            try:
                self.status.configure(text_color=color)
                self.status_card.configure(border_color=color)
            except:
                pass
        else:
            # Static red for disconnected
            try:
                self.status.configure(text_color="#ef4444")
                self.status_card.configure(border_color="#4a5568")
            except:
                pass
        
        self.root.after(50, self.animate_connection_glow)

    def save_token(self):
        """Save the Discord token to a file."""
        token = self.token_entry.get().strip()
        if token:
            try:
                with open("discord_token.txt", "w") as f:
                    f.write(token)
                self.discord_token = token
                self.show_notification("Token saved successfully!", "success")
            except Exception as e:
                self.show_notification(f"Failed to save token", "error")
        else:
            self.show_notification("Please enter a Discord token", "warning")
    
    def load_token(self):
        """Load the Discord token from file."""
        try:
            with open("discord_token.txt", "r") as f:
                token = f.read().strip()
                if token:
                    self.token_entry.delete(0, 'end')
                    self.token_entry.insert(0, token)
                    self.discord_token = token
                    self.show_notification("Discord token loaded successfully", "success")
        except FileNotFoundError:
            pass  # File doesn't exist yet
        except Exception as e:
            self.show_notification(f"Failed to load token", "error")
    
    def clear_token(self):
        """Clear the Discord token."""
        self.token_entry.delete(0, 'end')
        self.discord_token = ""
        try:
            if os.path.exists("discord_token.txt"):
                os.remove("discord_token.txt")
            self.show_notification("Token cleared", "info")
        except Exception as e:
            self.show_notification(f"Failed to clear token", "error")
    
    def logout(self):
        """Logout and return to login screen."""
        # Stop sniper if running
        if self.running:
            self.stop()
        
        # Clear session
        CloudyLoginScreen.clear_session()
        
        self.show_notification("Logging out...", "info")
        
        # Restart the application
        self.root.after(1000, self._restart_app)
    
    def _restart_app(self):
        """Restart the application to show login screen."""
        # Destroy main frame
        self.main_frame.destroy()
        
        # Show login screen again
        def on_login(token):
            # Recreate the sniper
            self.__init__(self.root, token)
        
        CloudyLoginScreen(self.root, on_login)

    def create_cloud_icon(self):
        """Create a beautiful cloud icon programmatically with glow effect."""
        size = 140
        image = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        
        # Scale factor
        s = 0.7
        
        # Create gradient-like effect with multiple layers
        # Outer glow (light blue)
        glow_color = (135, 206, 250, 60)
        draw.ellipse([int(45*s), int(70*s), int(155*s), int(145*s)], fill=glow_color)
        draw.ellipse([int(28*s), int(78*s), int(97*s), int(138*s)], fill=glow_color)
        draw.ellipse([int(103*s), int(78*s), int(172*s), int(138*s)], fill=glow_color)
        draw.ellipse([int(53*s), int(53*s), int(113*s), int(113*s)], fill=glow_color)
        draw.ellipse([int(87*s), int(53*s), int(147*s), int(113*s)], fill=glow_color)
        
        # Apply blur for glow effect
        image = image.filter(ImageFilter.GaussianBlur(radius=6))
        
        # Main cloud (white)
        draw = ImageDraw.Draw(image)
        cloud_color = (255, 255, 255, 255)
        draw.ellipse([int(50*s), int(75*s), int(150*s), int(140*s)], fill=cloud_color)
        draw.ellipse([int(33*s), int(83*s), int(92*s), int(133*s)], fill=cloud_color)
        draw.ellipse([int(108*s), int(83*s), int(167*s), int(133*s)], fill=cloud_color)
        draw.ellipse([int(58*s), int(58*s), int(108*s), int(108*s)], fill=cloud_color)
        draw.ellipse([int(92*s), int(58*s), int(142*s), int(108*s)], fill=cloud_color)
        
        # Light smoothing
        image = image.filter(ImageFilter.GaussianBlur(radius=1))
        
        ctk_image = ctk.CTkImage(
            light_image=image,
            dark_image=image,
            size=(85, 85)
        )
        
        icon_label = ctk.CTkLabel(
            self.icon_container,
            image=ctk_image,
            text=""
        )
        icon_label.image = ctk_image
        return icon_label

    def _create_header(self):
        """Creates the modern header section."""
        header_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        header_frame.pack(fill='x', padx=30, pady=(25, 20))
        
        # Left side - App title with cloud icon
        title_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        title_container.pack(side='left')
        
        # Cloud icon and title in horizontal layout
        self.icon_container = ctk.CTkFrame(title_container, fg_color="transparent")
        self.icon_container.pack(side='left', padx=(0, 15))
        
        icon_label = self.create_cloud_icon()
        icon_label.pack()
        
        title_frame = ctk.CTkFrame(title_container, fg_color="transparent")
        title_frame.pack(side='left')
        
        # Title with gradient sweep effect
        self.title_label = ctk.CTkLabel(
            title_frame,
            text="Cloudy",
            font=("Segoe UI", 42, "bold"),
            text_color="#c8dcff"
        )
        self.title_label.pack(anchor='w')
        
        ctk.CTkLabel(
            title_frame,
            text="Job Drop Monitor & Executor",
            font=("Segoe UI", 14),
            text_color="#64748b"
        ).pack(anchor='w')
        
        # Right side - Start/Stop/Logout buttons
        btn_container = ctk.CTkFrame(header_frame, fg_color="transparent")
        btn_container.pack(side='right')
        
        # Logout button
        self.logout_btn = ctk.CTkButton(
            btn_container,
            text="Log in",
            width=45,
            height=40,
            corner_radius=10,
            fg_color="#475569",
            hover_color="#334155",
            font=("Segoe UI", 16),
            text_color="#ffffff",
            command=self.logout
        )
        self.logout_btn.pack(side='left', padx=(0, 10))
        
        self.start_btn = ctk.CTkButton(
            btn_container,
            text="Start",
            width=110,
            height=40,
            corner_radius=10,
            fg_color="#10b981",
            hover_color="#059669",
            font=("Segoe UI", 13, "bold"),
            command=self.start
        )
        self.start_btn.pack(side='left', padx=(0, 8))
        
        self.stop_btn = ctk.CTkButton(
            btn_container,
            text="■ Stop",
            width=110,
            height=40,
            corner_radius=10,
            fg_color="#ef4444",
            hover_color="#dc2626",
            font=("Segoe UI", 13, "bold"),
            command=self.stop,
            state="disabled"
        )
        self.stop_btn.pack(side='left')

    def _create_stats_cards(self):
        """Creates the statistics cards with cloudier design."""
        stats_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        stats_container.pack(fill='x', padx=30, pady=(0, 18))
        
        # Configure grid
        stats_container.grid_columnconfigure(0, weight=1)
        stats_container.grid_columnconfigure(1, weight=1)
        stats_container.grid_columnconfigure(2, weight=1)
        
        # Status Card with gradient-like effect
        self.status_card = ctk.CTkFrame(
            stats_container, 
            corner_radius=14, 
            fg_color="#1e293b",
            border_width=2, 
            border_color="#4a5568"
        )
        self.status_card.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        # Status indicator row
        status_header = ctk.CTkFrame(self.status_card, fg_color="transparent")
        status_header.pack(pady=(18, 6))
        
        ctk.CTkLabel(
            status_header,
            text="STATUS",
            font=("Segoe UI", 11, "bold"),
            text_color="#94a3b8"
        ).pack(side="left")
        
        self.status = ctk.CTkLabel(
            self.status_card,
            text="● Disconnected",
            font=("Segoe UI", 18, "bold"),
            text_color="#ef4444"
        )
        self.status.pack(pady=(0, 18))
        
        # Drops Count Card
        count_card = ctk.CTkFrame(
            stats_container, 
            corner_radius=14, 
            fg_color="#1e293b",
            border_width=2, 
            border_color="#4a5568"
        )
        count_card.grid(row=0, column=1, sticky="ew", padx=(0, 10))
        
        ctk.CTkLabel(
            count_card,
            text="DROPS CAUGHT",
            font=("Segoe UI", 11, "bold"),
            text_color="#94a3b8"
        ).pack(pady=(18, 6))
        
        self.count = ctk.CTkLabel(
            count_card,
            text="0",
            font=("Segoe UI", 20, "bold"),
            text_color="#818cf8"
        )
        self.count.pack(pady=(0, 18))
        
        # Filter Card
        filter_card = ctk.CTkFrame(
            stats_container, 
            corner_radius=14, 
            fg_color="#1e293b",
            border_width=2, 
            border_color="#4a5568"
        )
        filter_card.grid(row=0, column=2, sticky="ew")
        
        ctk.CTkLabel(
            filter_card,
            text="MINIMUM M/S",
            font=("Segoe UI", 11, "bold"),
            text_color="#94a3b8"
        ).pack(pady=(18, 6))
        
        self.filter_display = ctk.CTkLabel(
            filter_card,
            text="0",
            font=("Segoe UI", 20, "bold"),
            text_color="#10b981"
        )
        self.filter_display.pack(pady=(0, 18))

    def _create_controls(self):
        """Creates the control panel with improved styling."""
        control_container = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        control_container.pack(fill='x', padx=30, pady=(0, 18))
        
        control_container.grid_columnconfigure(0, weight=1)
        control_container.grid_columnconfigure(1, weight=1)
        
        # === TOKEN SECTION ===
        token_frame = ctk.CTkFrame(
            control_container, 
            corner_radius=14, 
            fg_color="#1e293b",
            border_width=2, 
            border_color="#4a5568"
        )
        token_frame.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        
        token_inner = ctk.CTkFrame(token_frame, fg_color="transparent")
        token_inner.pack(pady=18, padx=22, fill='x')
        
        ctk.CTkLabel(
            token_inner,
            text="🔑 Discord Token",
            font=("Segoe UI", 12, "bold"),
            text_color="#cbd5e1"
        ).pack(anchor='w', pady=(0, 10))
        
        token_input_frame = ctk.CTkFrame(token_inner, fg_color="transparent")
        token_input_frame.pack(fill='x')
        
        self.token_entry = ctk.CTkEntry(
            token_input_frame,
            height=40,
            corner_radius=10,
            font=("Segoe UI", 12),
            placeholder_text="Paste your Discord token here...",
            border_width=2,
            border_color="#374151",
            fg_color="#0f172a",
            show="*"
        )
        self.token_entry.pack(fill='x', pady=(0, 12))
        
        token_btn_frame = ctk.CTkFrame(token_inner, fg_color="transparent")
        token_btn_frame.pack(fill='x')
        
        self.save_token_btn = ctk.CTkButton(
            token_btn_frame,
            text="💾 Save",
            height=36,
            corner_radius=10,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            font=("Segoe UI", 12, "bold"),
            command=self.save_token
        )
        self.save_token_btn.pack(side='left', fill='x', expand=True, padx=(0, 6))
        
        self.load_token_btn = ctk.CTkButton(
            token_btn_frame,
            text="📂 Load",
            height=36,
            corner_radius=10,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            font=("Segoe UI", 12, "bold"),
            command=self.load_token
        )
        self.load_token_btn.pack(side='left', fill='x', expand=True, padx=(0, 6))
        
        self.clear_token_btn = ctk.CTkButton(
            token_btn_frame,
            text="🗑️ Clear",
            height=36,
            corner_radius=10,
            fg_color="#6366f1",
            hover_color="#4f46e5",
            font=("Segoe UI", 12, "bold"),
            command=self.clear_token
        )
        self.clear_token_btn.pack(side='left', fill='x', expand=True)
        
        # === FILTER SECTION ===
        filter_frame = ctk.CTkFrame(
            control_container, 
            corner_radius=14, 
            fg_color="#1e293b",
            border_width=2, 
            border_color="#4a5568"
        )
        filter_frame.grid(row=0, column=1, sticky="ew", padx=(10, 0))
        
        filter_inner = ctk.CTkFrame(filter_frame, fg_color="transparent")
        filter_inner.pack(pady=18, padx=22, fill='x')
        
        ctk.CTkLabel(
            filter_inner,
            text="⚡ Minimum M/s Filter",
            font=("Segoe UI", 12, "bold"),
            text_color="#cbd5e1"
        ).pack(anchor='w', pady=(0, 10))
        
        filter_input_frame = ctk.CTkFrame(filter_inner, fg_color="transparent")
        filter_input_frame.pack(fill='x')
        
        self.min_entry = ctk.CTkEntry(
            filter_input_frame,
            height=40,
            corner_radius=10,
            font=("Segoe UI", 13),
            justify="center",
            border_width=2,
            border_color="#374151",
            fg_color="#0f172a"
        )
        self.min_entry.insert(0, "0")
        self.min_entry.pack(side='left', fill='x', expand=True, padx=(0, 10))
        
        self.apply_filter_btn = ctk.CTkButton(
            filter_input_frame,
            text="✓ Apply",
            width=90,
            height=40,
            corner_radius=10,
            fg_color="#10b981",
            hover_color="#059669",
            font=("Segoe UI", 12, "bold"),
            command=self.apply_filter
        )
        self.apply_filter_btn.pack(side='left')

    def _create_log_section(self):
        """Creates the log display section with cloudier design."""
        log_frame = ctk.CTkFrame(
            self.main_frame, 
            corner_radius=14, 
            fg_color="#1e293b",
            border_width=2, 
            border_color="#4a5568"
        )
        log_frame.pack(fill='both', expand=True, padx=30, pady=(0, 25))
        
        # Log header with cloud icon
        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill='x', padx=18, pady=(15, 10))
        
        ctk.CTkLabel(
            log_header,
            text="☁️ Live Activity Log",
            font=("Segoe UI", 14, "bold"),
            text_color="#f1f5f9"
        ).pack(side='left')
        
        ctk.CTkLabel(
            log_header,
            text=f"v{CURRENT_VERSION}",
            font=("Segoe UI", 11),
            text_color="#64748b"
        ).pack(side='right')
        
        # Log text area
        self.logbox = ctk.CTkTextbox(
            log_frame,
            font=("Consolas", 12),
            corner_radius=10,
            fg_color="#0f172a",
            border_width=0,
            wrap='word'
        )
        self.logbox.pack(fill='both', expand=True, padx=18, pady=(0, 18))
        self.logbox.configure(state="disabled")

    def log(self, text, log_type="info"):
        """Thread-safe logging to the GUI with color coding."""
        t = datetime.now().strftime("%H:%M:%S")
        
        # Define colors based on log type
        colors = {
            "timestamp": "#64748b",
            "info": "#cbd5e1",
            "success": "#10b981",
            "warning": "#f59e0b",
            "error": "#ef4444",
            "drop": "#818cf8"
        }
        
        def do_log():
            self.logbox.configure(state="normal")
            
            # Add timestamp
            self.logbox.insert("end", f"[{t}] ", tags="timestamp")
            self.logbox.tag_config("timestamp", foreground=colors["timestamp"])
            
            # Add message with appropriate color
            self.logbox.insert("end", f"{text}\n", tags=log_type)
            self.logbox.tag_config(log_type, foreground=colors.get(log_type, colors["info"]))
            
            self.logbox.see("end")
            self.logbox.configure(state="disabled")
        
        # Schedule on main thread if called from another thread
        self.root.after(0, do_log)

    def apply_filter(self):
        """Applies the minimum M/s filter value."""
        try:
            val = float(self.min_entry.get())
            if val < 0: val = 0
            self.min_ms = val
            self.filter_display.configure(text=f"{val:,.0f}")
            self.show_notification(f"Filter set to {val:,.0f} M/s", "success")
        except:
            self.show_notification("Please enter a valid number", "error")

    def start(self):
        """Starts the sniper with proper state management."""
        current_time = time.time()
        
        # === HARD COOLDOWN - No actions within 2 seconds of each other ===
        if current_time - self.last_action_time < self.ACTION_COOLDOWN:
            remaining = self.ACTION_COOLDOWN - (current_time - self.last_action_time)
            self.show_notification(f"Please wait {remaining:.1f}s...", "warning")
            return
        
        # Check if buttons are locked
        if self.buttons_locked:
            return
        
        with self.state_lock:
            if self.connection_state != "disconnected":
                self.show_notification("Already connecting or connected!", "warning")
                return
            
            # Check if token is provided
            token = self.token_entry.get().strip()
            if not token:
                self.show_notification("Please enter your Discord token first", "warning")
                return
            
            # Lock everything
            self.buttons_locked = True
            self.last_action_time = current_time
            self.connection_state = "connecting"
            self.stop_requested = False
            self.connection_id += 1
            current_connection_id = self.connection_id
            self.discord_token = token
            self.running = True
        
        # Update UI - disable BOTH buttons
        self.status.configure(text="● Connecting...")
        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="disabled")
        
        self.drop_count = 0
        self.count.configure(text="0")
        self.processed_jobs.clear()

        self.log("☁️ Cloudy Sniper activated", "success")
        self.log(f"Python {sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro} | Thread Pool: 64 workers", "info")
        self.log("HTTP Server running at http://127.0.0.1:8080/latest", "info")

        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=64)

        threading.Thread(target=run_http_server, daemon=True).start()
        threading.Thread(target=self.run_discord, args=(current_connection_id,), daemon=True).start()
        
        # Enable stop button after delay (only if still connecting/connected)
        def enable_stop():
            with self.state_lock:
                if self.connection_state in ("connecting", "connected"):
                    self.stop_btn.configure(state="normal")
                self.buttons_locked = False
        self.root.after(1500, enable_stop)  # 1.5 second delay before stop is available

    def stop(self):
        """Stops the sniper with proper state management."""
        current_time = time.time()
        
        # === HARD COOLDOWN - No actions within 2 seconds of each other ===
        if current_time - self.last_action_time < self.ACTION_COOLDOWN:
            remaining = self.ACTION_COOLDOWN - (current_time - self.last_action_time)
            self.show_notification(f"Please wait {remaining:.1f}s...", "warning")
            return
        
        if self.buttons_locked:
            return
            
        with self.state_lock:
            if self.connection_state == "disconnected":
                return
            
            self.buttons_locked = True
            self.last_action_time = current_time
            self.stop_requested = True
            self.running = False
            self.connection_state = "disconnected"  # Set immediately
        
        # Update UI immediately - disable BOTH buttons
        self.status.configure(text="● Disconnecting...")
        self.stop_btn.configure(state="disabled")
        self.start_btn.configure(state="disabled")
        
        self.log("Stopping sniper...", "warning")
        
        # Close Discord client if running
        if self.discord_client:
            try:
                if not self.discord_client.is_closed():
                    if self.discord_loop and self.discord_loop.is_running():
                        asyncio.run_coroutine_threadsafe(self.discord_client.close(), self.discord_loop)
            except Exception as e:
                self.log(f"Error closing Discord: {e}", "error")
        
        # Shutdown executor
        if self.executor:
            try:
                self.executor.shutdown(wait=False)
            except:
                pass
            self.executor = None
        
        # Update final state after longer delay to ensure cleanup
        def finalize_stop():
            self.status.configure(text="● Disconnected")
            self.start_btn.configure(state="normal")
            self.stop_btn.configure(state="disabled")
            self.buttons_locked = False
            self.show_notification("Sniper stopped", "warning")
        
        # Wait 2 seconds to ensure old connection is fully dead
        self.root.after(2000, finalize_stop)

    def _handle_drop_sync(self, msg):
        """Synchronous function containing the core processing logic."""
        # Check if stop was requested
        with self.state_lock:
            if self.stop_requested or not self.running:
                return
        
        if not msg.embeds:
            return

        e = msg.embeds[0]
        
        name = None
        money_str = None
        players = None
        job_pc = None

        for field in e.fields:
            field_name = field.name.strip()
            field_value = field.value.replace("**", "").strip()
            normalized_name = field_name.lower().replace(' ', '')
            
            if e.fields.index(field) == 0:
                name = field_value
            elif "moneypersec" in normalized_name:
                money_str = field_value.replace("$", "").replace(",", "").replace(" ", "")
            elif "players" in normalized_name:
                players = field_value
            elif "jobid(pc)" in normalized_name or "jobid" in normalized_name:
                job_pc = field_value
        
        if not all([name, money_str, job_pc]):
            self.log(f"Incomplete drop data ignored", "warning")
            return

        match = re.search(r'[\d\.]+', money_str)
        if not match:
            self.log(f"Failed to parse M/s value: {money_str}", "warning")
            return
        
        money_num = float(match.group())

        if money_num < self.min_ms:
            return

        if job_pc in self.processed_jobs:
            return
        
        self.processed_jobs.add(job_pc)

        global latest_drop
        latest_drop = {
            "job": job_pc,
            "name": name,
            "ms": money_num,
            "players": players,
            "timestamp": time.time()
        }

        self.log(f"✓ {name} | ${money_num:,.0f}M/s | {players} players", "drop")
        
        self.drop_count += 1
        self.root.after(0, lambda: self.count.configure(text=str(self.drop_count)))

    def run_discord(self, connection_id):
        """Initializes and runs the Discord client with proper cleanup."""
        # Check if already cancelled before starting
        with self.state_lock:
            if self.stop_requested or self.connection_id != connection_id:
                return
        
        # Create a new event loop for this thread
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        self.discord_loop = loop
        
        self.discord_client = discord.Client()
        CHANNEL = 1401775181025775738

        @self.discord_client.event
        async def on_ready():
            """Called when the client is connected and ready."""
            # Check if stop was requested or this is an old connection
            with self.state_lock:
                if self.stop_requested or self.connection_id != connection_id:
                    await self.discord_client.close()
                    return
                self.connection_state = "connected"
            
            self.log(f"Discord connected: {self.discord_client.user}", "success")
            self.root.after(0, lambda: self.status.configure(text="● Connected"))
            self.root.after(0, lambda: self.show_notification("☁️ Discord connected!", "success"))

        @self.discord_client.event
        async def on_message(msg):
            """Processes incoming messages from Discord."""
            with self.state_lock:
                if not self.running or self.stop_requested or self.connection_id != connection_id:
                    return
            
            if msg.channel.id != CHANNEL or not msg.embeds:
                return

            await loop.run_in_executor(self.executor, partial(self._handle_drop_sync, msg))

        try:
            loop.run_until_complete(self.discord_client.start(self.discord_token))
        except discord.errors.LoginFailure:
            with self.state_lock:
                if self.connection_id != connection_id:
                    return  # Old connection, ignore
            self.log("Invalid Discord token - please check and try again", "error")
            self.root.after(0, lambda: self.show_notification("Invalid Discord token!", "error"))
            self.root.after(0, self._reset_to_disconnected)
        except asyncio.CancelledError:
            pass  # Expected when stopping
        except Exception as e:
            with self.state_lock:
                if self.connection_id != connection_id:
                    return  # Old connection, ignore
            self.log(f"Discord connection error: {e}", "error")
            self.root.after(0, lambda: self.show_notification(f"Connection error", "error"))
            self.root.after(0, self._reset_to_disconnected)
        finally:
            try:
                loop.close()
            except:
                pass
            self.discord_loop = None
    
    def _reset_to_disconnected(self):
        """Reset UI to disconnected state."""
        with self.state_lock:
            self.connection_state = "disconnected"
            self.running = False
            self.buttons_locked = False
        self.status.configure(text="● Disconnected")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def run(self):
        """Starts the application main loop (called externally)."""
        pass  # Main loop is handled by CloudyApp


# === MAIN APPLICATION CONTROLLER ===
class CloudyApp:
    """Main application controller that manages login and main screens."""
    
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Cloudy - Job Drop Sniper")
        self.root.geometry("900x720")
        self.root.resizable(False, False)
        self.root.configure(fg_color="#0a0f1a")
        
        # Set window icon (for taskbar and title bar)
        self._set_icon()
        
        self.sniper = None
        self.update_available = False
        self.new_version = None
        
        # Check for updates in background
        threading.Thread(target=self._check_updates, daemon=True).start()
        
        # Show login screen first
        self.login_screen = CloudyLoginScreen(self.root, self._on_login_success)
    
    def _set_icon(self):
        """Set the application icon for taskbar and window."""
        try:
            # Try to find icon in same directory as script
            import sys
            script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            icon_path = os.path.join(script_dir, "cloudy.ico")
            
            if os.path.exists(icon_path):
                self.root.iconbitmap(icon_path)
                
                # For Windows taskbar icon
                if sys.platform == 'win32':
                    import ctypes
                    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('cloudy.sniper.app')
        except Exception as e:
            pass  # Icon not found, continue without it
    
    def _safe_print(self, msg):
        """Print only if console exists (not in windowed mode)."""
        if sys.stdout is not None:
            try:
                print(msg)
            except:
                pass
    
    def _check_updates(self):
        """Check for updates in background."""
        while True:
            has_update, new_version = AutoUpdater.check_for_updates()
            
            if has_update:
                self.update_available = True
                self.new_version = new_version
                
                # Download new code
                success = AutoUpdater.download_and_update()
                
                if success:
                    # Show notification then restart
                    self.root.after(0, self._do_update_restart)
                    break
            
            # Check every 30 seconds
            time.sleep(30)
    
    def _do_update_restart(self):
        """Show notification and restart."""
        # Show notification
        if hasattr(self, 'sniper') and self.sniper:
            self.sniper.show_notification("New version found. Restarting...", "info")
            # Wait 2 seconds then restart
            self.root.after(2000, self._restart_app)
        else:
            # No sniper yet, restart immediately
            self.root.after(500, self._restart_app)
    
    def _restart_app(self):
        """Restart the application."""
        self.root.destroy()
        AutoUpdater.restart_app()
    
    def _show_update_notification(self):
        """Show update notification to user."""
        if hasattr(self, 'sniper') and self.sniper:
            self.sniper.show_notification("New version found. Restarting...", "info")
    
    def _on_login_success(self, token):
        """Called when login is successful."""
        # Create and show main sniper UI
        self.sniper = CloudySniper(self.root, token)
        
        # Show update notification if available
        if self.update_available:
            self.root.after(1500, self._show_update_notification)
    
    def run(self):
        """Start the application."""
        self.root.mainloop()


if __name__ == "__main__":
    # Fix Windows console encoding for emojis (only if console exists)
    import sys
    if sys.platform == "win32" and sys.stdout is not None:
        try:
            sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        except:
            pass
    
    # Only print if console exists
    if sys.stdout is not None:
        print("=" * 50)
        print("  CLOUDY - Job Drop Sniper")
        print("  Modern Discord monitoring solution")
        print("=" * 50)
    
    app = CloudyApp()
    app.run()
