import json
import os

# File where the player's profile will be saved
PROFILE_FILE = "player.json"


# Player class to manage player stats and profile
class Player:
    def __init__(self, username, avatar):
        # Basic player info
        self.username = username
        self.avatar = avatar

        # Stats (default values for a new player)
        self.wins = 0
        self.losses = 0
        self.fastest_win = None  # Will store the least number of moves to win

    # Record a win and check if it's the fastest win
    def record_win(self, moves):
        self.wins += 1
        # Update fastest_win if this game was quicker (less moves)
        if self.fastest_win is None or moves < self.fastest_win:
            self.fastest_win = moves

    # Record a loss
    def record_loss(self):
        self.losses += 1

    # Save the player profile to a JSON file
    def save(self):
        data = {
            "username": self.username,
            "avatar": self.avatar,
            "wins": self.wins,
            "losses": self.losses,
            "fastest_win": self.fastest_win
        }
        # Open (or create) the file in write mode and dump the dictionary as JSON
        with open(PROFILE_FILE, "w") as f:
            json.dump(data, f)

    # Load an existing player profile from JSON file
    @staticmethod
    def load():
        # Check if the profile file exists
        if os.path.exists(PROFILE_FILE):
            # Read the file
            with open(PROFILE_FILE, "r") as f:
                data = json.load(f)

            # Create a new Player object using stored data
            p = Player(data["username"], data["avatar"])
            p.wins = data["wins"]
            p.losses = data["losses"]
            p.fastest_win = data["fastest_win"]
            return p

        # If no file exists, return None (no profile saved yet)
        return None
