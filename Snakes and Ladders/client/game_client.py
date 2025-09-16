# client.py  # English: Main client GUI for the Snake & Ladder game (entry-point file)
import tkinter as tk  # Import tkinter GUI toolkit and alias as tk for UI building
from tkinter import messagebox, simpledialog  # Import ready-made dialog utilities from tkinter
import requests  # Import requests to make HTTP calls to the game server
import threading  # Import threading to run network operations and websockets without freezing the UI
import websocket  # Import websocket-client to handle realtime WebSocket communication
import json  # Import JSON for serializing and deserializing local profile and server responses
import pyperclip  # Import pyperclip to copy invite links to the system clipboard
import time  # Import time for timing-related utilities (e.g., duration measurements)
import os  # Import os for filesystem operations like checking and reading files
from urllib.parse import urlparse
from snake_ladder_game import \
    SnakeLadderGame  # Import the core game class that renders and runs the board GUI and logic

SERVER_URL = "https://slidetoglory-project-2.onrender.com"


def build_ws_url(session_id: str, username: str) -> str:
    parsed = urlparse(SERVER_URL)
    scheme = "wss" if parsed.scheme == "https" else "ws"
    host = parsed.netloc
    return f"{scheme}://{host}/ws/{session_id}/{username}"


class GameClient:  # Define the main application class that handles UI flow, auth, and game sessions
    def __init__(self):  # Constructor for the GameClient class
        self.root = tk.Tk()  # Create the main Tkinter root window
        self.root.title("✨Slide To Glory!✨")  # Set window title shown in the OS
        self.root.configure(bg="#2a9d8f")  # Set the base background color for the root window
        self.username = None  # # Logged-in username (None if offline)
        self.avatar = "🙂"  # Default avatar emoji for the user
        self.display_name = None  # Display name shown in games (can differ from account)
        self.display_avatar = None  # Avatar used in-game (can be different from account avatar)
        self.is_host = True  # Tracks whether this client created (hosts) an online session
        self.local_profile = self.load_local_profile()  # Load local profile data for offline use
        self.show_register_window()  # Start the UI flow by showing registration screen

    # ---------- Локален профил за offline игри ----------
    def load_local_profile(self):
        """Вчитај локален профил од датотека"""  # Load local profile from file
        try:
            if os.path.exists("local_profile.json"):  # If a local profile file exists
                with open("local_profile.json", "r") as f:  # Open it for reading
                    return json.load(f)  # Parse and return the JSON content
        except:
            pass  # If anything goes wrong, silently ignore and fall back to default profile
        return {"display_name": "Player", "display_avatar": "🙂", "games_played": 0}  # Default local profile values

    def save_local_profile(self):
        """Зачувај локален профил"""  # Save the local profile to disk
        try:
            with open("local_profile.json", "w") as f:  # Open (or create) the local profile file for writing
                json.dump(self.local_profile, f)  # Serialize and write the profile dictionary
        except:
            pass  # Ignore any file write errors (best-effort persistence)

    def update_display_profile(self, name=None, avatar=None):
        """Ажурирај само display профилот (не го менува логираниот акаунт)"""  # Update just the display profile (not the account)
        if name:
            self.display_name = name  # Update in-memory display name
            self.local_profile["display_name"] = name  # Persist name to the local profile dict
        if avatar:
            self.display_avatar = avatar  # Update in-memory display avatar
            self.local_profile["display_avatar"] = avatar  # Persist avatar to the local profile dict
        self.save_local_profile()  # Save changes to disk

    # ---------- Auth screens ----------
    def show_register_window(self):
        self.clear_window()  # Remove any widgets currently in the root window
        self.root.geometry("600x600")  # Set the window size for the registration screen

        # Header frame
        header_frame = tk.Frame(self.root, bg="#34495e", height=80)  # Create a header frame with a darker background
        header_frame.pack(fill="x")  # Pack it horizontally across the top
        header_frame.pack_propagate(False)  # Prevent automatic resizing based on inner widgets

        tk.Label(header_frame, text="🐍 Snake & Ladder", font=("Arial", 20, "bold"),
                 bg="#34495e", fg="#ecf0f1").pack(pady=20)  # Title label placed inside the header frame

        # Main content frame
        content_frame = tk.Frame(self.root, bg="#2c3e50", padx=30, pady=20)  # Main content area background and padding
        content_frame.pack(expand=True, fill="both")  # Make it expand to use remaining window space

        tk.Label(content_frame, text="Create Account", font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="#ecf0f1").pack(pady=15)  # Section header for registration form

        # Input fields
        tk.Label(content_frame, text="Username:", font=("Arial", 12),
                 bg="#2c3e50", fg="#bdc3c7").pack(anchor="w", pady=(10, 2))  # Label for username field
        username_entry = tk.Entry(content_frame, font=("Arial", 12), width=30, relief=tk.FLAT,
                                  bd=5)  # Entry for username
        username_entry.pack(pady=5, ipady=5)  # Pack the username entry with vertical padding and internal padding

        tk.Label(content_frame, text="Password:", font=("Arial", 12),
                 bg="#2c3e50", fg="#bdc3c7").pack(anchor="w", pady=(10, 2))  # Label for password
        password_entry = tk.Entry(content_frame, show="*", font=("Arial", 12), width=30, relief=tk.FLAT,
                                  bd=5)  # Password entry with masked input
        password_entry.pack(pady=5, ipady=5)  # Pack the password entry widget

        tk.Label(content_frame, text="Avatar (emoji, optional):", font=("Arial", 12),
                 bg="#2c3e50", fg="#bdc3c7").pack(anchor="w", pady=(10, 2))  # Label for avatar input
        avatar_entry = tk.Entry(content_frame, font=("Arial", 12), width=30, relief=tk.FLAT,
                                bd=5)  # Entry where user can type or paste an emoji
        avatar_entry.pack(pady=5, ipady=5)  # Pack the avatar entry

        def attempt_register():
            username = username_entry.get().strip()  # Read and trim username from the entry widget
            password = password_entry.get().strip()  # Read and trim password from the entry widget
            avatar = avatar_entry.get().strip() or "🙂"  # Read avatar or fall back to a default emoji

            if not username or not password:
                messagebox.showerror("Error",
                                     "Username and password are required!")  # Show error if either field missing
                return  # Abort registration attempt

            try:
                r = requests.post(f"{SERVER_URL}/register",
                                  params={"username": username, "password": password,
                                          "avatar": avatar})  # Make POST request to server register endpoint with params
                if r.status_code == 200 and r.json().get(
                        "status") == "success":  # Check for success response from server
                    messagebox.showinfo("Success", "Registration successful!")  # Notify user of successful registration
                    self.show_login_window()  # Switch UI to login screen
                else:
                    messagebox.showerror("Error", r.json().get("message",
                                                               "Unknown error"))  # Show server-provided error message or fallback
            except Exception as e:
                messagebox.showerror("Error", f"Connection error: {e}")  # Show network/connection error details

        # Buttons
        tk.Button(content_frame, text="Register", command=attempt_register,
                  font=("Arial", 14, "bold"), bg="#27ae60", fg="white",
                  padx=20, pady=8, relief=tk.FLAT, width=15).pack(
            pady=15)  # Register button that triggers attempt_register

        tk.Button(content_frame, text="Already have account? Login", command=self.show_login_window,
                  font=("Arial", 12), bg="#3498db", fg="white",
                  padx=15, pady=5, relief=tk.FLAT).pack()  # Button to switch to the login screen

    def show_login_window(self):
        self.clear_window()  # Clear any existing widgets from the root window
        self.root.geometry("450x350")  # Set geometry for the login screen

        # Header frame
        header_frame = tk.Frame(self.root, bg="#34495e", height=80)  # Header frame similar to register screen
        header_frame.pack(fill="x")  # Pack it across the top
        header_frame.pack_propagate(False)  # Disable automatic propagation of child sizes

        tk.Label(header_frame, text="🐍 Snake & Ladder", font=("Arial", 20, "bold"),
                 bg="#34495e", fg="#ecf0f1").pack(pady=20)  # Title label

        # Main content frame
        content_frame = tk.Frame(self.root, bg="#2c3e50", padx=30, pady=20)  # Content area frame for login inputs
        content_frame.pack(expand=True, fill="both")  # Expand to fill available space

        tk.Label(content_frame, text="Login", font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="#ecf0f1").pack(pady=15)  # Login header

        # Input fields
        tk.Label(content_frame, text="Username:", font=("Arial", 12),
                 bg="#2c3e50", fg="#bdc3c7").pack(anchor="w", pady=(10, 2))  # Username label
        username_entry = tk.Entry(content_frame, font=("Arial", 12), width=30, relief=tk.FLAT,
                                  bd=5)  # Username entry widget
        username_entry.pack(pady=5, ipady=5)  # Pack username entry

        tk.Label(content_frame, text="Password:", font=("Arial", 12),
                 bg="#2c3e50", fg="#bdc3c7").pack(anchor="w", pady=(10, 2))  # Password label
        password_entry = tk.Entry(content_frame, show="*", font=("Arial", 12), width=30, relief=tk.FLAT,
                                  bd=5)  # Masked password entry
        password_entry.pack(pady=5, ipady=5)  # Pack password entry

        def attempt_login():
            username = username_entry.get().strip()  # Get username text and trim whitespace
            password = password_entry.get().strip()  # Get password text and trim whitespace

            if not username or not password:
                messagebox.showerror("Error",
                                     "Please enter both username and password!")  # Prompt if fields are missing
                return  # Stop further processing

            try:
                r = requests.post(f"{SERVER_URL}/login",
                                  params={"username": username,
                                          "password": password})  # Call server /login endpoint with credentials
                data = r.json()  # Parse JSON response from the server
                if r.status_code == 200 and data.get("status") == "success":  # Check successful login
                    self.username = data.get("username",
                                             username)  # Логиран корисник  # English: Set logged-in username (server may normalize it)
                    self.avatar = data.get("avatar", "🙂")  # Update account avatar from server response if available
                    # Иницијално display профилот е ист како логираниот
                    self.display_name = self.username  # Initialize display name to the account username
                    self.display_avatar = self.avatar  # Initialize display avatar to the account avatar
                    messagebox.showinfo("Success", f"Welcome back, {self.username}!")  # Greet the user
                    self.show_main_menu()  # Move to the main menu UI
                else:
                    messagebox.showerror("Error",
                                         data.get("message", "Invalid credentials"))  # Show error message from server
            except Exception as e:
                messagebox.showerror("Error", f"Connection error: {e}")  # Show exception details on connection error

        # Buttons
        tk.Button(content_frame, text="Login", command=attempt_login,
                  font=("Arial", 14, "bold"), bg="#27ae60", fg="white",
                  padx=20, pady=8, relief=tk.FLAT, width=15).pack(
            pady=15)  # Login button tied to attempt_login function

        tk.Button(content_frame, text="Back to Register", command=self.show_register_window,
                  font=("Arial", 12), bg="#e67e22", fg="white",
                  padx=15, pady=5, relief=tk.FLAT).pack()  # Button to return to registration screen

    # ---------- Main menu ----------
    def show_main_menu(self):
        self.clear_window()  # Clear previous UI widgets
        self.root.geometry("600x700")  # Set window size appropriate for main menu

        # Header
        header_frame = tk.Frame(self.root, bg="#34495e", height=100)  # Header frame for top area
        header_frame.pack(fill="x")  # Pack horizontally
        header_frame.pack_propagate(False)  # Fix header size

        current_display_name = self.display_name or self.local_profile.get("display_name",
                                                                           "Player")  # Determine current display name with fallback
        current_display_avatar = self.display_avatar or self.local_profile.get("display_avatar",
                                                                               "🙂")  # Determine current display avatar with fallback

        tk.Label(header_frame, text="🐍 Snake & Ladder", font=("Arial", 24, "bold"),
                 bg="#34495e", fg="#ecf0f1").pack(pady=10)  # Header title label

        if self.username:
            tk.Label(header_frame, text=f"Logged in as: {self.avatar} {self.username}",
                     font=("Arial", 12), bg="#34495e", fg="#95a5a6").pack()  # Show logged in account info
            tk.Label(header_frame, text=f"Playing as: {current_display_avatar} {current_display_name}",
                     font=("Arial", 14, "bold"), bg="#34495e", fg="#f1c40f").pack()  # Show the display persona
        else:
            tk.Label(header_frame, text=f"Playing as: {current_display_avatar} {current_display_name}",
                     font=("Arial", 14, "bold"), bg="#34495e", fg="#f1c40f").pack(
                pady=5)  # If not logged in, show only display profile

        # Main content
        content_frame = tk.Frame(self.root, bg="#2c3e50", padx=40, pady=30)  # Main content frame for menu options
        content_frame.pack(expand=True, fill="both")  # Expand to fill window

        tk.Label(content_frame, text="Choose Game Mode", font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="#ecf0f1").pack(pady=20)  # Section header for choosing game mode

        # Game mode buttons
        tk.Button(content_frame, text="🎮 Play Solo (vs Bot)", font=("Arial", 16, "bold"),
                  command=self.play_solo, bg="#e74c3c", fg="white",
                  padx=25, pady=12, width=25, relief=tk.FLAT).pack(pady=10)  # Button to start singleplayer game

        tk.Button(content_frame, text="🌐 Create Online Game", font=("Arial", 16, "bold"),
                  command=self.create_game_session, bg="#27ae60", fg="white",
                  padx=25, pady=12, width=25, relief=tk.FLAT).pack(pady=10)  # Button to host an online game session

        tk.Button(content_frame, text="🔗 Join Online Game", font=("Arial", 16, "bold"),
                  command=self.join_game_session, bg="#3498db", fg="white",
                  padx=25, pady=12, width=25, relief=tk.FLAT).pack(
            pady=10)  # Button to join someone else's session via invite link

        # Profile and settings
        profile_frame = tk.Frame(content_frame, bg="#2c3e50")  # Small frame for profile buttons
        profile_frame.pack(pady=20)  # Place it with padding

        tk.Button(profile_frame, text="👤 Game Profile", command=self.show_game_profile_window,
                  font=("Arial", 14), bg="#9b59b6", fg="white",
                  padx=15, pady=8, width=15, relief=tk.FLAT).pack(side="left",
                                                                  padx=5)  # Button to open game profile settings

        if self.username:
            tk.Button(profile_frame, text="📊 Account Stats", command=self.show_account_stats_window,
                      font=("Arial", 14), bg="#34495e", fg="white",
                      padx=15, pady=8, width=15, relief=tk.FLAT).pack(side="left",
                                                                      padx=5)  # If logged in, show button to view online account stats

        # Local statistics preview
        self.show_local_stats_preview(content_frame)  # Render a preview of local solo statistics

        # Logout button
        if self.username:
            tk.Button(content_frame, text="Logout", command=self.logout,
                      font=("Arial", 12), bg="#95a5a6", fg="white",
                      padx=10, pady=5, relief=tk.FLAT).pack(pady=20)  # Button to log out of the account

    def show_local_stats_preview(self, parent):
        """Прикажи краток преглед на локални статистики"""  # English: Show a small preview of local statistics
        try:
            if os.path.exists("local_scores.json"):  # If the local scores file exists
                with open("local_scores.json", "r") as f:  # Open it and load the scores
                    scores = json.load(f)

                stats_frame = tk.Frame(parent, bg="#34495e", relief=tk.FLAT, bd=2)  # Frame to contain the stats preview
                stats_frame.pack(pady=15, padx=20, fill="x")  # Pack it with some padding

                tk.Label(stats_frame, text="📊 Local Solo Game Stats",
                         font=("Arial", 14, "bold"), bg="#34495e", fg="#ecf0f1").pack(
                    pady=8)  # Title for the stats section

                stats_text = f"Wins: {scores.get('wins', 0)}  •  Losses: {scores.get('losses', 0)}"  # Compose a summary string of wins and losses
                if scores.get('fastest_win'):
                    stats_text += f"  •  Best: {scores['fastest_win']}s"  # Append fastest win time when present

                tk.Label(stats_frame, text=stats_text,
                         font=("Arial", 11), bg="#34495e", fg="#27ae60").pack(pady=5)  # Show the composed stats string
        except:
            pass  # If reading the scores fails, silently ignore

    def logout(self):
        """Излегување од акаунтот"""  # English: Log the user out
        self.username = None  # Clear logged-in username
        self.avatar = "🙂"  # Reset account avatar to default
        self.display_name = self.local_profile.get("display_name", "Player")  # Restore display name from local profile
        self.display_avatar = self.local_profile.get("display_avatar", "🙂")  # Restore display avatar from local profile
        messagebox.showinfo("Logged Out", "You have been logged out successfully!")  # Inform the user of logout
        self.show_main_menu()  # Return to the main menu UI after logout

    # ---------- Play modes ----------
    def play_solo(self):
        """Започни solo игра против бот"""  # English: Start a solo game against the built-in bot
        current_display_name = self.display_name or self.local_profile.get("display_name",
                                                                           "Player")  # Choose display name for this game
        current_display_avatar = self.display_avatar or self.local_profile.get("display_avatar",
                                                                               "🙂")  # Choose display avatar for this game

        # Зголеми games_played
        self.local_profile["games_played"] = self.local_profile.get("games_played",
                                                                    0) + 1  # Increment local games_played counter
        self.save_local_profile()  # Persist the incremented count to disk

        self.start_game(session_id=None, ws_url=None, is_host=True, singleplayer=True,
                        player_name=current_display_name,
                        player_avatar=current_display_avatar)  # Launch the game instance in singleplayer mode

    def create_game_session(self):
        """Создади онлајн игра"""  # English: Create (host) an online multiplayer game session
        if not self.username:
            messagebox.showwarning("Login Required",
                                   "Please login to create online games!")  # Require login to create online sessions
            return

        try:
            r = requests.post(
                f"{SERVER_URL}/create_session")  # Request the server to create a new session and return metadata
            if r.status_code == 200:
                session_info = r.json()  # Parse the session info JSON
                invite_link = session_info["invite_link"]  # Extract invite link from server response
                session_id = session_info["session_id"]  # Extract session id

                pyperclip.copy(invite_link)  # Copy the invite link to clipboard automatically

                def copy_link():
                    pyperclip.copy(invite_link)  # Local helper to re-copy the invite link
                    messagebox.showinfo("Copied", "Invite link copied to clipboard!")  # Notify the user

                # Stylish invite window
                invite_window = tk.Toplevel(self.root)  # Create a new top-level window to show invite link
                invite_window.title("Game Session Created")  # Title for the invite dialog
                invite_window.geometry("550x250")  # Size for the invite dialog
                invite_window.configure(bg="#2c3e50")  # Match app theme

                tk.Label(invite_window, text="🎮 Game Session Created!",
                         font=("Arial", 16, "bold"), bg="#2c3e50", fg="#f1c40f").pack(
                    pady=15)  # Heading inside invite dialog

                tk.Label(invite_window, text="Share this link with your friend:",
                         font=("Arial", 12), bg="#2c3e50", fg="#ecf0f1").pack(pady=5)  # Instructional label

                link_frame = tk.Frame(invite_window, bg="#2c3e50")  # Frame to hold the invite link entry and controls
                link_frame.pack(pady=10)  # Place the frame with vertical spacing

                link_entry = tk.Entry(link_frame, width=50, font=("Arial", 11), relief=tk.FLAT,
                                      bd=5)  # Entry showing invite link
                link_entry.insert(0, invite_link)  # Insert the invite URL into the entry widget
                link_entry.pack(pady=5)  # Pack the entry widget

                tk.Button(invite_window, text="📋 Copy Link", command=copy_link,
                          font=("Arial", 12, "bold"), bg="#27ae60", fg="white",
                          padx=20, pady=8, relief=tk.FLAT).pack(pady=15)  # Button to copy link again if needed

                ws_url = build_ws_url(session_id, self.username)  # Construct the websocket URL for the created session
                current_display_name = self.display_name or self.username  # Determine display name for the host player
                current_display_avatar = self.display_avatar or self.avatar  # Determine display avatar for the host player

                self.start_game(session_id=session_id, ws_url=ws_url, is_host=True, singleplayer=False,
                                player_name=current_display_name,
                                player_avatar=current_display_avatar)  # Start the multiplayer game as host
            else:
                messagebox.showerror("Error",
                                     "Failed to create game session.")  # Inform the user if the server didn't return success
        except Exception as e:
            messagebox.showerror("Error", f"Server error: {e}")  # Handle network/server exceptions gracefully

    def join_game_session(self):
        """Приклучи се кон онлајн игра"""  # English: Join an existing online game using an invite link
        if not self.username:
            messagebox.showwarning("Login Required",
                                   "Please login to join online games!")  # Require login before joining online sessions
            return

        invite_link = simpledialog.askstring("Join Game",
                                             "Paste the invite link:")  # Ask the user to paste the invite URL
        if not invite_link:
            return  # If user cancels or enters nothing, abort
        try:
            session_id = invite_link.strip().split("/")[-1]  # Extract the session id from the invite URL
            ws_url = build_ws_url(session_id, self.username)  # Build websocket URL for the session

            current_display_name = self.display_name or self.username  # Choose display name for joining player
            current_display_avatar = self.display_avatar or self.avatar  # Choose display avatar for joining player

            self.start_game(session_id=session_id, ws_url=ws_url, is_host=False, singleplayer=False,
                            player_name=current_display_name,
                            player_avatar=current_display_avatar)  # Start the client as a joining participant
        except Exception as e:
            messagebox.showerror("Error", f"Invalid invite link: {e}")  # Error handling for malformed invites

    # ---------- Game window ----------
    def start_game(self, session_id, ws_url, is_host: bool, singleplayer: bool,
                   player_name=None, player_avatar=None):
        """Започни игра"""  # English: Start the game window and initialize networking/players
        self.session_id = session_id  # Store session identifier on the client instance
        self.is_host = is_host  # Store whether this client is the host
        self.root.withdraw()  # скриј главен прозорец  # English: Hide the main menu window while the game runs

        game_window = tk.Toplevel(self.root)  # Create a separate window for the actual game board/UI
        game_window.title("Snake & Ladder Game")  # Title the game window

        # WebSocket врска за мултиплејер
        self.ws_app = None  # Initialize websocket attribute
        if ws_url:
            self.ws_app = websocket.WebSocketApp(
                ws_url,
                on_message=self.on_ws_message,
                on_close=lambda ws, *args: print("Disconnected from session."),
                on_open=lambda ws, *args: self.on_ws_open(ws, player_name, player_avatar)
            )  # Create a websocket client and wire callbacks for receiving messages and lifecycle events
            threading.Thread(target=self.ws_app.run_forever,
                             daemon=True).start()  # Run the websocket client in a background thread so UI remains responsive

        # Подготви имиња и аватари
        current_name = player_name or "Player"  # Use provided player_name or fallback to a generic name
        current_avatar = player_avatar or "🙂"  # Use provided avatar or default

        if singleplayer:
            names = [current_name, "Bot"]  # For singleplayer, second player is the built-in bot
            avatars = [current_avatar, "🤖"]  # Avatars for player and bot
        else:
            names = [current_name, "Waiting..."] if is_host else ["Waiting...",
                                                                  current_name]  # Placeholder names depending on host/joiner
            avatars = [current_avatar, "😎"] if is_host else ["🙂", current_avatar]  # Avatars accordingly

        def update_stats(username: str, result: str, duration: int | None):
            """Ажурирај серверски статистики - само за логиран корисник"""  # English: Update server-side stats when a game finishes (only for logged in users)
            if self.username:  # Ажурирај само ако е логиран  # English: Only attempt server update if user is logged in
                try:
                    requests.post(f"{SERVER_URL}/update_stats",
                                  params={"username": self.username, "result": result,
                                          "duration": duration or 0})  # Send result and duration to server endpoint
                except Exception:
                    pass  # If it fails, ignore to avoid disrupting game cleanup

        # Создади инстанца на играта
        self.game_instance = SnakeLadderGame(
            game_window,
            player_names=names,
            player_avatars=avatars,
            websocket_connection=self.ws_app,
            singleplayer=singleplayer,
            is_host=is_host,
            on_game_end=self.on_game_end,
            server_update_fn=update_stats,
            logged_username=self.username
            # Проследи го логираниот корисник  # English: Pass the logged-in username to the game instance
        )  # Instantiate the SnakeLadderGame which will render the board and manage gameplay logic

    # ---------- WebSocket handlers ----------
    def on_ws_open(self, ws, player_name, player_avatar):
        """Called when WebSocket connection opens"""
        # Send player information to server
        player_info = {
            "action": "player_info",
            "display_name": player_name or self.display_name or self.username or "Player",
            "display_avatar": player_avatar or self.display_avatar or self.avatar or "🙂"
        }
        try:
            ws.send(json.dumps(player_info))
            print(f"Sent player info: {player_info}")
        except Exception as e:
            print(f"Failed to send player info: {e}")

    def on_ws_message(self, ws, message: str):
        """Handle WebSocket messages"""
        try:
            data = json.loads(message)
            print(f"Received: {data}")  # Debug logging

            if hasattr(self, "game_instance"):
                if data["type"] == "state_update":
                    self.game_instance.apply_server_state(data)
                elif data["type"] == "player_info_update":
                    self.update_game_players(data["players"])
                elif data["type"] == "game_state":
                    # Initial game state when joining
                    self.game_instance.apply_server_state(data)
                    if "players" in data:
                        self.update_game_players(data["players"])
                elif data["type"] == "notice":
                    print("Server notice:", data["message"])
                    # Also update players info if included
                    if "players" in data:
                        self.update_game_players(data["players"])

        except json.JSONDecodeError:
            print(f"Invalid JSON received: {message}")
        except Exception as e:
            print(f"Error handling message: {e}")

    def update_game_players(self, players_data):
        """Update player names and avatars in the game instance"""
        if not hasattr(self, "game_instance") or not players_data:
            return

        # Convert server player data to game format
        player_names = []
        player_avatars = []

        for username, player_info in players_data.items():
            player_names.append(player_info["display_name"])
            player_avatars.append(player_info["display_avatar"])

        # Update game instance
        if len(player_names) >= 1:
            if self.is_host:
                self.game_instance.update_player_info(0, player_names[0], player_avatars[0])
                if len(player_names) >= 2:
                    self.game_instance.update_player_info(1, player_names[1], player_avatars[1])
            else:
                # For joining player, reverse the order
                if len(player_names) >= 2:
                    self.game_instance.update_player_info(0, player_names[1], player_avatars[1])
                self.game_instance.update_player_info(1, player_names[0], player_avatars[0])

        print(f"Updated game players: {player_names} with avatars {player_avatars}")

    def on_game_end(self, winner_idx: int):
        """Кога играта завршува"""  # English: Called when a game finishes to perform cleanup and return to menu
        try:
            if hasattr(self, 'ws_app') and self.ws_app:
                self.ws_app.close()  # Close the websocket connection if present
        except Exception:
            pass  # Ignore any errors while closing
        self.root.deiconify()  # Re-show the main window that was hidden when the game started
        self.show_main_menu()  # Освежи мени за нови статистики  # English: Refresh the main menu to reflect any updated stats

    # ---------- Profile windows ----------
    def show_game_profile_window(self):
        """Прикажи прозорец за игра профил (локален display профил)"""  # English: Show local display profile editing window
        profile_window = tk.Toplevel(self.root)  # Create a top-level window for profile settings
        profile_window.title("Game Profile Settings")  # Title the profile window
        profile_window.geometry("500x600")  # Size for profile window
        profile_window.configure(bg="#2c3e50")  # Match app theme

        # Header
        tk.Label(profile_window, text="🎮 Game Profile", font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="#ecf0f1").pack(pady=15)  # Heading label

        tk.Label(profile_window, text="This name and avatar will be shown in games",
                 font=("Arial", 11), bg="#2c3e50", fg="#95a5a6").pack()  # Helper text explaining display profile

        # Avatar selection
        tk.Label(profile_window, text="Choose Game Avatar:", font=("Arial", 14, "bold"),
                 bg="#2c3e50", fg="#bdc3c7").pack(pady=(20, 10))  # Section label for avatar selection

        avatars = ["🙂", "😎", "🤖", "🐍", "🐱", "🐯", "🐸", "🐧", "🚀", "⚡", "🎮", "🏆", "👑", "🎭", "🦸",
                   "🧙"]  # List of avatar emoji choices
        current_avatar = self.display_avatar or self.local_profile.get("display_avatar",
                                                                       avatars[0])  # Determine current avatar selection
        selected_avatar = tk.StringVar(value=current_avatar)  # Tk variable to hold the currently selected avatar

        # Avatar grid
        avatar_frame = tk.Frame(profile_window, bg="#2c3e50")  # Frame to place the avatar buttons in a grid
        avatar_frame.pack(pady=10)  # Pack with spacing

        for i, emoji in enumerate(avatars):
            row = i // 4  # 4 columns layout logic: compute row index
            col = i % 4  # column index in the grid
            b = tk.Radiobutton(
                avatar_frame,
                text=emoji,
                variable=selected_avatar,
                value=emoji,
                indicatoron=False,
                font=("Arial", 20),
                width=2,
                height=1,
                relief="raised",
                selectcolor="#3498db",
                bg="#ecf0f1",
                activebackground="#2ecc71"
            )  # Create a styled radiobutton that looks like a selectable tile with the emoji text
            b.grid(row=row, column=col, padx=3, pady=3)  # Place the radiobutton into the grid

        # Name entry
        tk.Label(profile_window, text="Game Display Name:", font=("Arial", 14, "bold"),
                 bg="#2c3e50", fg="#bdc3c7").pack(pady=(20, 5))  # Label for display name input

        name_entry = tk.Entry(profile_window, font=("Arial", 12), width=25, relief=tk.FLAT,
                              bd=5)  # Entry widget for the display name
        current_name = self.display_name or self.local_profile.get("display_name",
                                                                   "")  # Pre-fill with current display name or local profile
        name_entry.insert(0, current_name)  # Insert the current display name into the entry widget
        name_entry.pack(pady=5, ipady=5)  # Pack the name entry

        def save_game_profile():
            """Зачувај game профил (не го менува акаунтот)"""  # English: Save the game display profile (does not modify account)
            avatar = selected_avatar.get()  # Get the chosen avatar from the Tk variable
            new_name = name_entry.get().strip() or "Player"  # Get the new display name or default to 'Player'

            self.update_display_profile(new_name, avatar)  # Update the in-memory and local persisted display profile

            messagebox.showinfo("Profile Updated",
                                f"Game profile updated!\nName: {new_name}\nAvatar: {avatar}\n\nThis won't change your account settings.")  # Notify the user of the change
            profile_window.destroy()  # Close the profile window
            self.show_main_menu()  # Return to main menu so changes are visible

        # Save button
        tk.Button(profile_window, text="💾 Save Game Profile", command=save_game_profile,
                  font=("Arial", 14, "bold"), bg="#27ae60", fg="white",
                  padx=25, pady=10, relief=tk.FLAT).pack(pady=25)  # Button to save the local display profile changes

        # Show local stats
        self.show_local_stats_in_profile(profile_window)  # Display the local solo stats inside the profile window

    def show_local_stats_in_profile(self, parent):
        """Прикажи локални статистики во профил прозорецот"""  # English: Show local statistics inside the profile window
        stats_frame = tk.Frame(parent, bg="#34495e", relief=tk.RAISED,
                               bd=2)  # Frame with raised border to highlight stats
        stats_frame.pack(pady=15, padx=30, fill="x")  # Pack it full-width with padding

        tk.Label(stats_frame, text="📈 Local Solo Game Statistics",
                 font=("Arial", 14, "bold"), bg="#34495e", fg="#ecf0f1").pack(pady=10)  # Stats header

        try:
            if os.path.exists("local_scores.json"):  # Check local scores file presence
                with open("local_scores.json", "r") as f:
                    local_stats = json.load(f)  # Load the local stats JSON

                tk.Label(stats_frame, text=f"Solo Wins: {local_stats.get('wins', 0)}",
                         font=("Arial", 12), bg="#34495e", fg="#27ae60").pack()  # Display wins
                tk.Label(stats_frame, text=f"Solo Losses: {local_stats.get('losses', 0)}",
                         font=("Arial", 12), bg="#34495e", fg="#e74c3c").pack()  # Display losses

                if local_stats.get('fastest_win'):
                    tk.Label(stats_frame, text=f"Fastest Win: {local_stats['fastest_win']} seconds",
                             font=("Arial", 12), bg="#34495e", fg="#f39c12").pack()  # Display fastest win when present
            else:
                tk.Label(stats_frame, text="No solo games played yet",
                         font=("Arial", 12), bg="#34495e", fg="#95a5a6").pack()  # If no stats, show placeholder message

            tk.Label(stats_frame, text=f"Total Games Started: {self.local_profile.get('games_played', 0)}",
                     font=("Arial", 12), bg="#34495e", fg="#9b59b6").pack(
                pady=5)  # Show total games started from local profile
        except Exception:
            tk.Label(stats_frame, text="Error loading statistics",
                     font=("Arial", 12), bg="#34495e",
                     fg="#e74c3c").pack()  # If something goes wrong, display error message

    def show_account_stats_window(self):
        """Прикажи серверски статистики на акаунтот"""  # English: Display server-backed account statistics for the logged in user
        if not self.username:
            messagebox.showwarning("Not Logged In",
                                   "Please login to view account statistics!")  # Prompt to login if no account attached
            return

        stats_window = tk.Toplevel(self.root)  # Create a top-level window to show account stats
        stats_window.title("Account Statistics")  # Title the window
        stats_window.geometry("450x500")  # Size of the stats window
        stats_window.configure(bg="#2c3e50")  # Match theme

        tk.Label(stats_window, text="📊 Account Statistics", font=("Arial", 18, "bold"),
                 bg="#2c3e50", fg="#ecf0f1").pack(pady=20)  # Header inside stats window

        tk.Label(stats_window, text=f"Account: {self.avatar} {self.username}",
                 font=("Arial", 14), bg="#2c3e50", fg="#f1c40f").pack(pady=10)  # Show account identifier

        stats_frame = tk.Frame(stats_window, bg="#34495e", relief=tk.RAISED, bd=3)  # Frame to contain fetched stats
        stats_frame.pack(pady=20, padx=30, fill="both", expand=True)  # Pack it to expand within the window

        try:
            r = requests.get(f"{SERVER_URL}/stats",
                             params={"username": self.username})  # Fetch stats from server endpoint
            if r.status_code == 200 and r.json().get("status") != "error":  # If server returns usable stats
                stats = r.json()  # Parse server response JSON

                tk.Label(stats_frame, text="🌐 Online Game Statistics",
                         font=("Arial", 16, "bold"), bg="#34495e", fg="#ecf0f1").pack(
                    pady=15)  # Subheader for online stats

                stats_info = tk.Frame(stats_frame, bg="#34495e")  # Inner frame for stat labels
                stats_info.pack(pady=10)  # Pack it with spacing

                tk.Label(stats_info, text=f"Online Wins: {stats['wins']}",
                         font=("Arial", 14), bg="#34495e", fg="#27ae60").pack(
                    pady=3)  # Show wins fetched from the server
                tk.Label(stats_info, text=f"Online Losses: {stats['losses']}",
                         font=("Arial", 14), bg="#34495e", fg="#e74c3c").pack(pady=3)  # Show losses fetched from server

                if stats["fastest_win_seconds"] < 9999:
                    tk.Label(stats_info, text=f"Fastest Online Win: {stats['fastest_win_seconds']} seconds",
                             font=("Arial", 14), bg="#34495e", fg="#f39c12").pack(
                        pady=3)  # Display fastest online win if it's a valid value

                total_games = stats['wins'] + stats['losses']  # Compute total online games from wins/losses
                if total_games > 0:
                    win_rate = (stats['wins'] / total_games) * 100  # Calculate win percentage
                    tk.Label(stats_info, text=f"Win Rate: {win_rate:.1f}%",
                             font=("Arial", 14, "bold"), bg="#34495e", fg="#3498db").pack(
                        pady=8)  # Show win rate formatted with one decimal
            else:
                tk.Label(stats_frame, text="Could not load online statistics",
                         font=("Arial", 14), bg="#34495e", fg="#e74c3c").pack(
                    pady=20)  # Message if server returned an error state
        except Exception as e:
            tk.Label(stats_frame, text=f"Error connecting to server: {e}",
                     font=("Arial", 12), bg="#34495e", fg="#e74c3c").pack(
                pady=20)  # Display network/exception error details

        # Account management button
        def change_account_profile():
            """Промени серверски акаунт профил"""  # English: Provide UI to change server account profile (username/avatar)
            change_window = tk.Toplevel(stats_window)  # Create a nested top-level window for changing profile
            change_window.title("Change Account Profile")  # Title the change window
            change_window.geometry("400x350")  # Size of the change dialog
            change_window.configure(bg="#2c3e50")  # Match theme

            tk.Label(change_window, text="Change Account Profile", font=("Arial", 16, "bold"),
                     bg="#2c3e50", fg="#ecf0f1").pack(pady=15)  # Header inside change window

            tk.Label(change_window, text="Warning: This changes your actual account!",
                     font=("Arial", 10), bg="#2c3e50", fg="#e74c3c").pack(pady=5)  # Warning label

            tk.Label(change_window, text="New Username:", font=("Arial", 12),
                     bg="#2c3e50", fg="#bdc3c7").pack(pady=(15, 2))  # Label for new username entry
            username_entry = tk.Entry(change_window, font=("Arial", 12),
                                      width=25)  # Entry widget pre-filled with current username
            username_entry.insert(0, self.username)  # Insert current username as default
            username_entry.pack(pady=5)  # Pack username entry

            tk.Label(change_window, text="New Avatar (emoji):", font=("Arial", 12),
                     bg="#2c3e50", fg="#bdc3c7").pack(pady=(10, 2))  # Label for new avatar entry
            avatar_entry = tk.Entry(change_window, font=("Arial", 12), width=25)  # Entry widget to input avatar emoji
            avatar_entry.insert(0, self.avatar)  # Insert current avatar as default
            avatar_entry.pack(pady=5)  # Pack avatar entry

            def save_account_changes():
                new_username = username_entry.get().strip()  # Read new username value
                new_avatar = avatar_entry.get().strip() or self.avatar  # Read new avatar or fallback to current avatar

                if not new_username:
                    messagebox.showerror("Error", "Username cannot be empty!")  # Guard against empty usernames
                    return

                try:
                    r = requests.post(f"{SERVER_URL}/update_profile",
                                      params={"username": self.username, "avatar": new_avatar,
                                              "new_name": new_username})  # Send update request to server to change account data
                    data = r.json()  # Parse server response
                    if r.status_code == 200 and data.get("status") == "success":  # If update succeeded
                        # Ажурирај ги локалните податоци
                        self.username = data.get("username",
                                                 new_username)  # Update local client username to server-provided or new value
                        self.avatar = data.get("avatar", new_avatar)  # Update local avatar

                        # Ажурирај го и display профилот ако е ист како акаунтот
                        if self.display_name == username_entry.get() or not self.display_name:
                            self.display_name = self.username  # If display name was the same as account, update it as well
                        if self.display_avatar == avatar_entry.get() or not self.display_avatar:
                            self.display_avatar = self.avatar  # Update display avatar if it matched the account avatar

                        messagebox.showinfo("Success",
                                            "Account profile updated successfully!")  # Notify user of success
                        change_window.destroy()  # Close change dialog
                        stats_window.destroy()  # Close stats window to refresh state
                        self.show_main_menu()  # Return to main menu to show updated values
                    else:
                        messagebox.showerror("Error", data.get("message",
                                                               "Failed to update account"))  # Show server error message
                except Exception as e:
                    messagebox.showerror("Error", f"Connection error: {e}")  # Show connection error

            tk.Button(change_window, text="💾 Save Account Changes", command=save_account_changes,
                      font=("Arial", 12, "bold"), bg="#e67e22", fg="white",
                      padx=15, pady=8, relief=tk.FLAT).pack(pady=20)  # Button to submit account changes to server

            tk.Button(change_window, text="Cancel", command=change_window.destroy,
                      font=("Arial", 10), bg="#95a5a6", fg="white",
                      padx=10, pady=5, relief=tk.FLAT).pack()  # Cancel button to close the change dialog without saving

        tk.Button(stats_frame, text="🔧 Change Account Profile", command=change_account_profile,
                  font=("Arial", 12), bg="#9b59b6", fg="white",
                  padx=15, pady=8, relief=tk.FLAT).pack(pady=20)  # Button to open account profile change dialog

    # ---------- Utils ----------
    def clear_window(self):
        """Исчисти ги сите елементи од прозорецот"""  # English: Remove all widgets from the root window
        for widget in self.root.winfo_children():
            widget.destroy()  # Destroy each child widget to clear the UI

    def run(self):
        """Започни ја апликацијата"""  # English: Start the Tkinter mainloop and run the application
        self.root.mainloop()  # Enter Tkinter's main event loop


if __name__ == "__main__":
    client = GameClient()  # Instantiate the GameClient application class
    client.run()  # Run the application mainloop