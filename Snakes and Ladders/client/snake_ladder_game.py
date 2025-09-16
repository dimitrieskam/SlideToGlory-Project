# snake_ladder_game.py
import tkinter as tk
from tkinter import messagebox
from PIL import Image, ImageTk, ImageDraw
import random
import os
import math
import time
import json
import websocket  # websocket-client

# Намалена табла со подобар стил
BOARD_SIZE = 640
TILE_SIZE = BOARD_SIZE // 10
BOARD_MARGIN = 40  # Маргини околу таблата
ASSET_PATH = "snake_ladder_assets/"

# Точно поставени змии и скали според стандардната игра
SNAKES = {
    98: 78,  # Горе-лево до долу-средина
    95: 56,  # Горе-средина до средина
    87: 24,  # Горе-десно до долу-лево
    62: 18,  # Средина-десно до долу
    54: 34,  # Средина до долу-средина
    16: 6  # Долу-средина до почеток
}

LADDERS = {
    1: 38,  # Почеток до средина-лево
    4: 14,  # Почеток малку нагоре
    9: 21,  # Лево-долу до долу-средина
    28: 84,  # Средина до горе-лево
    36: 44,  # Средина-лево малку нагоре
    51: 67,  # Средина до средина-горе
    71: 91,  # Горе-лево до врв-лево
    80: 100  # Горе-десно до врв
}


class SnakeLadderGame:
    def __init__(self, root,
                 player_names: list[str] | None = None,
                 player_avatars: list[str] | None = None,
                 websocket_connection: websocket.WebSocketApp | None = None,
                 singleplayer: bool = False,
                 is_host: bool = True,
                 on_game_end=None,
                 server_update_fn=None,
                 logged_username=None):
        self.root = root
        self.root.title("Snake & Ladder Game")
        self.root.geometry(f"{BOARD_SIZE + BOARD_MARGIN * 2 + 320}x{BOARD_SIZE + BOARD_MARGIN * 2 + 100}")
        self.root.configure(bg="#2c3e50")

        self.ws = websocket_connection
        self.ws_connected = websocket_connection is not None
        self.singleplayer = singleplayer
        self.is_host = is_host
        self.on_game_end = on_game_end
        self.server_update_fn = server_update_fn
        self.logged_username = logged_username

        # Store username to display name mapping for online games
        self.username_to_display = {}
        self.display_to_username = {}

        self.start_time = time.time()
        self.total_moves = [0, 0]

        self.player_names = player_names or ["Player 1", "Player 2"]
        self.player_avatars = player_avatars or ["🙂", "😎"]

        self.local_score = self.load_local_score()
        self.setup_ui()
        self.init_game()

    def setup_ui(self):
        # Главна рамка со подобар стил
        main_frame = tk.Frame(self.root, bg="#2c3e50")
        main_frame.pack(expand=True, fill=tk.BOTH, padx=15, pady=15)

        # Лева страна - табла со фиксирана големина
        board_container = tk.Frame(main_frame, bg="#34495e", relief=tk.RAISED, bd=3)
        board_container.pack(side=tk.LEFT, padx=10, anchor="n")

        # Canvas со фиксирана големина
        canvas_width = BOARD_SIZE + BOARD_MARGIN * 2
        canvas_height = BOARD_SIZE + BOARD_MARGIN * 2

        self.canvas = tk.Canvas(board_container,
                                width=canvas_width,
                                height=canvas_height,
                                bg="#2c3e50",
                                highlightbackground="#34495e",
                                highlightthickness=3,
                                relief=tk.RAISED,
                                bd=2)
        self.canvas.pack(padx=8, pady=8)

        # Десна страна - контроли со фиксирана ширина
        self.controls_frame = tk.Frame(main_frame, bg="#34495e", width=280,
                                       relief=tk.RAISED, bd=3)
        self.controls_frame.pack(side=tk.RIGHT, fill=tk.Y, padx=10, anchor="n")
        self.controls_frame.pack_propagate(False)

        # Поставка на минимална големина на прозорецот
        min_width = canvas_width + 320 + 50
        min_height = canvas_height + 100
        self.root.minsize(min_width, min_height)

        self.draw_board()
        self.load_images()
        self.draw_snakes_and_ladders()

    def init_game(self):
        self.positions = [0, 0]

        # Креирај токени
        self.tokens = [
            self.canvas.create_oval(0, 0, 24, 24, fill='#e74c3c', outline='#c0392b', width=3, tags="player0"),
            self.canvas.create_oval(0, 0, 24, 24, fill='#3498db', outline='#2980b9', width=3, tags="player1")
        ]

        # Етикети за играчи
        self.labels = [
            self.canvas.create_text(0, 0, text=f"{self.player_avatars[0]}",
                                    font=("Arial", 16, "bold"), fill="#e74c3c", tags="label0"),
            self.canvas.create_text(0, 0, text=f"{self.player_avatars[1]}",
                                    font=("Arial", 16, "bold"), fill="#3498db", tags="label1")
        ]

        self.dice_value = 0
        self.current_player = 0
        self.movable = False

        self.setup_controls()
        self.move_token(0)
        self.move_token(1)

        # bind клик на токени
        self.canvas.tag_bind("player0", "<Button-1>", lambda e: self.try_move(0))
        self.canvas.tag_bind("player1", "<Button-1>", lambda e: self.try_move(1))

    def setup_controls(self):
        # Заглавие
        title_frame = tk.Frame(self.controls_frame, bg="#34495e")
        title_frame.pack(pady=15, fill="x")

        tk.Label(title_frame, text="Snake & Ladder", font=("Arial", 18, "bold"),
                 bg="#34495e", fg="#ecf0f1").pack()

        # Информации за играчи
        players_frame = tk.Frame(self.controls_frame, bg="#2c3e50", relief=tk.SUNKEN, bd=2)
        players_frame.pack(pady=10, padx=10, fill="x")

        self.player_labels = [
            tk.Label(players_frame, text=f"{self.player_avatars[0]} {self.player_names[0]}",
                     font=("Arial", 12, "bold"), bg="#2c3e50", fg="#e74c3c"),
            tk.Label(players_frame, text=f"{self.player_avatars[1]} {self.player_names[1]}",
                     font=("Arial", 12, "bold"), bg="#2c3e50", fg="#3498db")
        ]

        self.player_labels[0].pack(pady=2)
        tk.Label(players_frame, text="VS", font=("Arial", 10, "bold"),
                 bg="#2c3e50", fg="#bdc3c7").pack()
        self.player_labels[1].pack(pady=2)

        # Коцка
        dice_frame = tk.Frame(self.controls_frame, bg="#34495e")
        dice_frame.pack(pady=20)

        self.dice_label = tk.Label(dice_frame, bg="#34495e")
        self.dice_label.pack(pady=10)

        # Копчиња
        self.roll_button = tk.Button(dice_frame, text="Roll Dice", command=self.roll_dice,
                                     font=("Arial", 14, "bold"), bg="#27ae60", fg="white",
                                     activebackground="#2ecc71", relief=tk.RAISED, bd=3,
                                     padx=15, pady=8, width=12)
        self.roll_button.pack(pady=5)

        self.reset_button = tk.Button(dice_frame, text="Reset Game", command=self.reset_game,
                                      font=("Arial", 12), bg="#e67e22", fg="white",
                                      activebackground="#f39c12", relief=tk.RAISED, bd=3,
                                      padx=10, pady=5, width=12)
        self.reset_button.pack(pady=5)

        # Статус
        self.status_label = tk.Label(self.controls_frame, text=f"{self.player_names[0]}'s turn",
                                     font=("Arial", 14, "bold"), bg="#34495e", fg="#f1c40f",
                                     wraplength=250, justify="center")
        self.status_label.pack(pady=15)

        # Локални поени за singleplayer
        if self.singleplayer and self.local_score:
            self.show_local_score()

    def show_local_score(self):
        score_frame = tk.Frame(self.controls_frame, bg="#2c3e50", relief=tk.SUNKEN, bd=2)
        score_frame.pack(pady=10, padx=10, fill="x")

        tk.Label(score_frame, text="Local Statistics", font=("Arial", 12, "bold"),
                 bg="#2c3e50", fg="#95a5a6").pack(pady=5)

        wins = self.local_score.get('wins', 0)
        losses = self.local_score.get('losses', 0)
        fastest = self.local_score.get('fastest_win')

        tk.Label(score_frame, text=f"Wins: {wins}", font=("Arial", "10"),
                 bg="#2c3e50", fg="#27ae60").pack()
        tk.Label(score_frame, text=f"Losses: {losses}", font=("Arial", "10"),
                 bg="#2c3e50", fg="#e74c3c").pack()

        if fastest:
            tk.Label(score_frame, text=f"Best: {fastest}s", font=("Arial", "10"),
                     bg="#2c3e50", fg="#f39c12").pack()

    # ---------- Локално чување поени ----------
    def load_local_score(self):
        try:
            if os.path.exists("local_scores.json"):
                with open("local_scores.json", "r") as f:
                    return json.load(f)
        except:
            pass
        return {"wins": 0, "losses": 0, "fastest_win": None}

    def save_local_score(self, result, duration=None):
        if not self.singleplayer:
            return

        if result == "win":
            self.local_score["wins"] += 1
            if duration and (not self.local_score["fastest_win"] or duration < self.local_score["fastest_win"]):
                self.local_score["fastest_win"] = duration
        elif result == "loss":
            self.local_score["losses"] += 1

        try:
            with open("local_scores.json", "w") as f:
                json.dump(self.local_score, f)
        except:
            pass

    # ---------- WebSocket helpers ----------
    def safe_ws_send(self, message: str):
        if self.ws and self.ws_connected:
            try:
                self.ws.send(message)
            except Exception:
                self.ws_connected = False

    def safe_ws_send_json(self, obj: dict):
        try:
            self.safe_ws_send(json.dumps(obj))
        except Exception:
            pass

    # ---------- Dice ----------
    def create_dice_image(self, value, size=70):
        img = Image.new('RGB', (size, size), '#ecf0f1')
        draw = ImageDraw.Draw(img)
        dot_radius = size // 12
        center = size // 2
        offset = size // 4

        draw.rectangle([2, 2, size - 3, size - 3], outline='#34495e', width=3, fill='#ecf0f1')

        dots = {
            1: [(center, center)],
            2: [(center - offset, center - offset), (center + offset, center + offset)],
            3: [(center - offset, center - offset), (center, center), (center + offset, center + offset)],
            4: [(center - offset, center - offset), (center + offset, center - offset),
                (center - offset, center + offset), (center + offset, center + offset)],
            5: [(center - offset, center - offset), (center + offset, center - offset),
                (center - offset, center + offset), (center + offset, center + offset), (center, center)],
            6: [(center - offset, center - offset), (center + offset, center - offset),
                (center - offset, center), (center + offset, center),
                (center - offset, center + offset), (center + offset, center + offset)]
        }

        for x, y in dots[value]:
            draw.ellipse((x - dot_radius, y - dot_radius, x + dot_radius, y + dot_radius), fill='#e74c3c')
        return ImageTk.PhotoImage(img)

    def load_images(self):
        self.dice_images = [self.create_dice_image(i) for i in range(1, 7)]

        try:
            snake_path = os.path.join(ASSET_PATH, "snake_big.png")
            ladder_path = os.path.join(ASSET_PATH, "ladder_big.png")

            if os.path.exists(snake_path):
                self.base_snake_img = Image.open(snake_path).convert("RGBA")
            else:
                self.base_snake_img = self.create_snake_image()

            if os.path.exists(ladder_path):
                self.base_ladder_img = Image.open(ladder_path).convert("RGBA")
            else:
                self.base_ladder_img = self.create_ladder_image()

        except Exception:
            self.base_snake_img = self.create_snake_image()
            self.base_ladder_img = self.create_ladder_image()

    def create_snake_image(self):
        img = Image.new('RGBA', (80, 80), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.ellipse([10, 20, 70, 60], fill='#e74c3c', outline='#c0392b', width=3)
        draw.ellipse([50, 10, 75, 35], fill='#c0392b', outline='#8b0000', width=2)
        draw.ellipse([58, 16, 62, 20], fill='white')
        draw.ellipse([68, 16, 72, 20], fill='white')
        draw.ellipse([59, 17, 61, 19], fill='black')
        draw.ellipse([69, 17, 71, 19], fill='black')

        return img

    def create_ladder_image(self):
        img = Image.new('RGBA', (80, 80), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        draw.rectangle([25, 5, 30, 75], fill='#8B4513', outline='#654321', width=1)
        draw.rectangle([50, 5, 55, 75], fill='#8B4513', outline='#654321', width=1)

        for i in range(6):
            y = 10 + i * 11
            draw.rectangle([25, y, 55, y + 3], fill='#A0522D', outline='#654321', width=1)

        return img

    # ---------- Board ----------
    def draw_board(self):
        colors = ['#3498db', '#5dade2', '#85c1e9', '#aed6f1', '#d6eaf8', '#ebf5fb']

        for row in range(10):
            for col in range(10):
                x1 = col * TILE_SIZE + BOARD_MARGIN
                y1 = (9 - row) * TILE_SIZE + BOARD_MARGIN
                x2 = x1 + TILE_SIZE
                y2 = y1 + TILE_SIZE

                if row % 2 == 0:
                    index = row * 10 + col + 1
                else:
                    index = row * 10 + (9 - col) + 1

                color_index = (row + col) % len(colors)
                color = colors[color_index]

                if index == 1:
                    color = '#27ae60'
                elif index == 100:
                    color = '#f1c40f'
                elif index in SNAKES:
                    color = '#e74c3c'
                elif index in LADDERS:
                    color = '#2ecc71'

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline='#2c3e50', width=2)
                self.canvas.create_text(x1 + TILE_SIZE // 2, y1 + TILE_SIZE // 2,
                                        text=str(index), font=("Arial", 12, "bold"), fill="#2c3e50")

    def get_tile_center_coords(self, pos: int):
        if pos <= 0:
            x = 15
            y = BOARD_SIZE + BOARD_MARGIN - 40
            return x, y

        if pos > 100:
            pos = 100

        pos -= 1
        row = pos // 10

        if row % 2 == 0:
            col = pos % 10
        else:
            col = 9 - (pos % 10)

        x = col * TILE_SIZE + TILE_SIZE // 2 + BOARD_MARGIN
        y = BOARD_SIZE - (row * TILE_SIZE + TILE_SIZE // 2) + BOARD_MARGIN
        return x, y

    # ---------- Snakes & Ladders ----------
    def draw_snakes_and_ladders(self):
        self.snake_photo_images = []
        self.ladder_photo_images = []

        for start_pos, end_pos in SNAKES.items():
            self._draw_snake(start_pos, end_pos)

        for start_pos, end_pos in LADDERS.items():
            self._draw_ladder(start_pos, end_pos)

        self.canvas.tag_raise("player0")
        self.canvas.tag_raise("player1")
        self.canvas.tag_raise("label0")
        self.canvas.tag_raise("label1")

    def _draw_snake(self, start_pos, end_pos):
        start_x, start_y = self.get_tile_center_coords(start_pos)
        end_x, end_y = self.get_tile_center_coords(end_pos)

        self.canvas.create_line(start_x, start_y, end_x, end_y,
                                fill='#c0392b', width=8, smooth=True,
                                capstyle=tk.ROUND, arrow=tk.LAST, arrowshape=(16, 20, 6))

        try:
            resized_snake = self.base_snake_img.resize((40, 40), Image.Resampling.LANCZOS)
            snake_photo = ImageTk.PhotoImage(resized_snake)
            self.snake_photo_images.append(snake_photo)
            self.canvas.create_image(end_x, end_y, image=snake_photo)
        except Exception:
            self.canvas.create_oval(end_x - 8, end_y - 8, end_x + 8, end_y + 8,
                                    fill='#e74c3c', outline='#c0392b', width=2)

    def _draw_ladder(self, start_pos, end_pos):
        start_x, start_y = self.get_tile_center_coords(start_pos)
        end_x, end_y = self.get_tile_center_coords(end_pos)

        offset = 8
        self.canvas.create_line(start_x - offset, start_y, end_x - offset, end_y,
                                fill='#27ae60', width=4, capstyle=tk.ROUND)
        self.canvas.create_line(start_x + offset, start_y, end_x + offset, end_y,
                                fill='#27ae60', width=4, capstyle=tk.ROUND)

        steps = 5
        for i in range(1, steps):
            step_x1 = start_x + (end_x - start_x) * i / steps - offset
            step_y1 = start_y + (end_y - start_y) * i / steps
            step_x2 = start_x + (end_x - start_x) * i / steps + offset
            step_y2 = start_y + (end_y - start_y) * i / steps
            self.canvas.create_line(step_x1, step_y1, step_x2, step_y2,
                                    fill='#2ecc71', width=3)

        try:
            angle = math.atan2(end_y - start_y, end_x - start_x)
            angle_deg = math.degrees(angle)
            rotated_ladder = self.base_ladder_img.rotate(-angle_deg, expand=True)
            resized_ladder = rotated_ladder.resize((50, 50), Image.Resampling.LANCZOS)
            ladder_photo = ImageTk.PhotoImage(resized_ladder)
            self.ladder_photo_images.append(ladder_photo)
            mid_x = (start_x + end_x) // 2
            mid_y = (start_y + end_y) // 2
            self.canvas.create_image(mid_x, mid_y, image=ladder_photo)
        except Exception:
            pass

    # ---------- Gameplay ----------
    def roll_dice(self):
        if self.movable:
            self.status_label.config(text="Move your token first!")
            return

        if self.ws_connected:
            # Only allow the logged-in user to roll on their turn
            can_roll = False
            if self.is_host and self.current_player == 0:
                can_roll = True
            elif not self.is_host and self.current_player == 1:
                can_roll = True

            if not can_roll:
                self.status_label.config(text="Wait for your turn!")
                return

            self.roll_button.config(state=tk.DISABLED)
            self.safe_ws_send_json({"action": "roll", "player": self.logged_username})
        else:
            self.roll_button.config(state=tk.DISABLED)
            self.animate_dice()

    def animate_dice(self, frame=0):
        if frame < 15:
            value = random.randint(1, 6)
            self.dice_label.config(image=self.dice_images[value - 1])
            self.root.after(80, lambda: self.animate_dice(frame + 1))
        else:
            self.dice_value = random.randint(1, 6)
            self.dice_label.config(image=self.dice_images[self.dice_value - 1])
            self.movable = True
            self.roll_button.config(state=tk.NORMAL)

    def try_move(self, player: int):
        if player != self.current_player or not self.movable:
            self.status_label.config(text=f"It's {self.player_names[self.current_player]}'s turn!")
            return

        current_pos = self.positions[player]
        next_pos = current_pos + self.dice_value

        if current_pos == 0:
            next_pos = self.dice_value

        if next_pos > 100:
            self.status_label.config(text=f"{self.player_names[player]} overshot! Turn passes.")
            self.movable = False
            self.switch_turn()
            return

        self.total_moves[player] += 1
        self.animate_token_move(player, current_pos, next_pos)

    def animate_token_move(self, player, start_pos, end_pos, step=0):
        if step < (end_pos - start_pos):
            intermediate_pos = start_pos + step + 1
            self.positions[player] = intermediate_pos
            self.move_token(player)
            self.root.after(100, lambda: self.animate_token_move(player, start_pos, end_pos, step + 1))
        else:
            final_pos = end_pos

            if final_pos in LADDERS:
                self.status_label.config(text=f"{self.player_names[player]} climbed a ladder!")
                ladder_top = LADDERS[final_pos]
                self.root.after(500, lambda: self.animate_special_move(player, final_pos, ladder_top))
                return
            elif final_pos in SNAKES:
                self.status_label.config(text=f"{self.player_names[player]} was bitten by a snake!")
                snake_tail = SNAKES[final_pos]
                self.root.after(500, lambda: self.animate_special_move(player, final_pos, snake_tail))
                return

            self.positions[player] = final_pos
            self.move_token(player)
            self.movable = False

            if final_pos == 100:
                self.handle_victory(player)
            else:
                self.switch_turn()

    def animate_special_move(self, player, from_pos, to_pos):
        self.positions[player] = to_pos
        self.move_token(player)
        self.movable = False
        if to_pos == 100:
            self.handle_victory(player)
        else:
            self.switch_turn()

    def move_token(self, player):
        if self.positions[player] <= 0:
            if player == 0:
                x, y = 15, BOARD_SIZE + BOARD_MARGIN - 40
            else:
                x, y = BOARD_SIZE + BOARD_MARGIN * 2 - 15, BOARD_SIZE + BOARD_MARGIN - 40
        else:
            x, y = self.get_tile_center_coords(self.positions[player])

        if player == 0:
            offset_x, offset_y = -8, -8
        else:
            offset_x, offset_y = 8, 8

        self.canvas.coords(self.tokens[player],
                           x + offset_x - 12, y + offset_y - 12,
                           x + offset_x + 12, y + offset_y + 12)

        if self.positions[player] <= 0:
            label_y = y + offset_y - 30
        else:
            label_y = y + offset_y - 30

        self.canvas.coords(self.labels[player], x + offset_x, label_y)

    def handle_victory(self, player):
        winner_name = self.player_names[player]
        self.status_label.config(text=f"🎉 {winner_name} WINS! 🎉")
        self.roll_button.config(state=tk.DISABLED)

        duration = int(time.time() - self.start_time)

        if self.singleplayer:
            if player == 0:
                self.save_local_score("win", duration)
            else:
                self.save_local_score("loss")

        if self.server_update_fn and self.logged_username:
            try:
                if (player == 0 and self.is_host) or (player == 1 and not self.is_host):
                    self.server_update_fn(self.logged_username, "win", duration)
                elif not self.singleplayer:
                    self.server_update_fn(self.logged_username, "loss", None)
            except Exception:
                pass

        choice = messagebox.askquestion("Game Over",
                                        f"{winner_name} wins!\nGame duration: {duration}s\nPlay again?",
                                        icon='question')
        if choice == "yes":
            self.reset_game()
            if self.ws_connected:
                self.safe_ws_send_json({"type": "reset"})
        else:
            if callable(self.on_game_end):
                self.on_game_end(player)
            self.root.quit()

    def switch_turn(self):
        self.current_player = 1 - self.current_player
        self.status_label.config(text=f"{self.player_names[self.current_player]}'s turn")

        if self.singleplayer and self.current_player == 1:
            self.root.after(1000, self.roll_dice)

    def reset_game(self):
        self.positions = [0, 0]
        self.move_token(0)
        self.move_token(1)
        self.current_player = 0
        self.movable = False
        self.status_label.config(text=f"{self.player_names[0]}'s turn")
        self.dice_label.config(image='')
        self.roll_button.config(state=tk.NORMAL)
        self.total_moves = [0, 0]
        self.start_time = time.time()

    def update_player_info(self, player_idx, name, avatar):
        """Update player information and UI"""
        if 0 <= player_idx < len(self.player_names):
            self.player_names[player_idx] = name
            self.player_avatars[player_idx] = avatar

            if hasattr(self, 'player_labels') and player_idx < len(self.player_labels):
                color = "#e74c3c" if player_idx == 0 else "#3498db"
                self.player_labels[player_idx].config(text=f"{avatar} {name}", fg=color)

            if player_idx < len(self.labels):
                self.canvas.itemconfig(self.labels[player_idx], text=avatar)

    # ---------- WebSocket handler ----------
    def on_ws_message(self, message: str):
        try:
            obj = json.loads(message)
            print(f"Game received: {obj}")  # Debug logging
        except json.JSONDecodeError:
            return

        if obj.get("type") == "state_update":
            self.apply_server_state(obj)
        elif obj.get("type") == "player_info_update":
            if "players" in obj:
                self.update_players_from_server(obj["players"])
        elif obj.get("type") == "game_state":
            self.apply_server_state(obj)
        elif obj.get("type") == "notice":
            print(f"Game notice: {obj.get('message')}")
            if "positions" in obj:
                for pname, pos in obj["positions"].items():
                    self.move_piece_by_name(pname, pos)
            if "turn" in obj and obj["turn"]:
                turn_display = self.get_display_name_for_username(obj["turn"])
                if turn_display in self.player_names:
                    self.current_player = self.player_names.index(turn_display)
        elif obj.get("type") == "reset":
            self.reset_game()

    def apply_server_state(self, state):
        """Apply server state updates to the game - FIXED VERSION"""
        positions = state.get("positions", {})
        turn = state.get("turn")
        last_roll = state.get("last_roll")
        player = state.get("player")
        players_info = state.get("players", {})

        print(f"Applying state: positions={positions}, turn={turn}, players={players_info}")

        # Update player information FIRST
        if players_info:
            self.update_players_from_server(players_info)

        # Update board positions
        for pname, pos in positions.items():
            self.move_piece_by_name(pname, pos)

        # Update turn information and dice
        if last_roll and player:
            self.dice_label.config(image=self.dice_images[last_roll - 1])

            # Find which player should be current based on turn
            if turn:
                turn_display_name = self.get_display_name_for_username(turn)
                if turn_display_name in self.player_names:
                    self.current_player = self.player_names.index(turn_display_name)

            # Show turn message
            player_display_name = self.get_display_name_for_username(player)
            turn_display_name = self.get_display_name_for_username(turn) if turn else "Unknown"

            self.status_label.config(
                text=f"{player_display_name} rolled {last_roll}. Now it's {turn_display_name}'s turn."
            )

            # Enable/disable roll button based on whose turn it is
            can_roll = False
            if self.is_host and self.current_player == 0:
                can_roll = True
            elif not self.is_host and self.current_player == 1:
                can_roll = True

            self.roll_button.config(state=tk.NORMAL if can_roll else tk.DISABLED)
            self.movable = False  # Server handles movement

    def update_players_from_server(self, players_info):
        """Update player names and avatars from server data - FIXED VERSION"""
        if not players_info:
            return

        print(f"Updating players from server: {players_info}")

        # Clear existing mappings
        self.username_to_display = {}
        self.display_to_username = {}

        # Get list of usernames in order they joined
        usernames = list(players_info.keys())

        for i, username in enumerate(usernames):
            player_info = players_info[username]
            display_name = player_info.get("display_name", username)
            display_avatar = player_info.get("display_avatar", "🙂")

            # Store mappings
            self.username_to_display[username] = display_name
            self.display_to_username[display_name] = username

            # Determine which player slot this should go in
            # Host: their username goes to slot 0, other player to slot 1
            # Joiner: their username goes to slot 1, other player to slot 0
            if username == self.logged_username:
                # This is the logged-in user
                player_idx = 0 if self.is_host else 1
            else:
                # This is the other player
                player_idx = 1 if self.is_host else 0

            # Only update if we have a valid slot
            if 0 <= player_idx < len(self.player_names):
                print(f"Updating player {player_idx} with {display_name} ({display_avatar})")
                self.update_player_info(player_idx, display_name, display_avatar)

    def get_display_name_for_username(self, username):
        """Get display name for a given username"""
        return self.username_to_display.get(username, username)

    def move_piece_by_name(self, username, pos):
        """Move a player piece by username"""
        display_name = self.get_display_name_for_username(username)

        if display_name in self.player_names:
            idx = self.player_names.index(display_name)
            self.positions[idx] = pos
            self.move_token(idx)
            return

        # Fallback
        if username in self.player_names:
            idx = self.player_names.index(username)
            self.positions[idx] = pos
            self.move_token(idx)

    # ---------- WebSocket handler ----------
    def on_ws_message(self, message: str):
        try:
            obj = json.loads(message)
            print(f"Game received: {obj}")  # Debug logging
        except json.JSONDecodeError:
            return

        if obj.get("type") == "state_update":
            self.apply_server_state(obj)
        elif obj.get("type") == "player_info_update":
            if "players" in obj:
                self.update_players_from_server(obj["players"])
        elif obj.get("type") == "game_state":
            self.apply_server_state(obj)
        elif obj.get("type") == "notice":
            print(f"Game notice: {obj.get('message')}")
            if "positions" in obj:
                for pname, pos in obj["positions"].items():
                    self.move_piece_by_name(pname, pos)
            if "turn" in obj and obj["turn"]:
                turn_display = self.get_display_name_for_username(obj["turn"])
                if turn_display in self.player_names:
                    self.current_player = self.player_names.index(turn_display)
        elif obj.get("type") == "reset":
            self.reset_game()

    def apply_server_state(self, state):
        """Apply server state updates to the game - FIXED VERSION"""
        positions = state.get("positions", {})
        turn = state.get("turn")
        last_roll = state.get("last_roll")
        player = state.get("player")
        players_info = state.get("players", {})

        print(f"Applying state: positions={positions}, turn={turn}, players={players_info}")

        # Update player information FIRST
        if players_info:
            self.update_players_from_server(players_info)

        # Update board positions
        for pname, pos in positions.items():
            self.move_piece_by_name(pname, pos)

        # Update turn information and dice
        if last_roll and player:
            self.dice_label.config(image=self.dice_images[last_roll - 1])

            # Find which player should be current based on turn
            if turn:
                turn_display_name = self.get_display_name_for_username(turn)
                if turn_display_name in self.player_names:
                    self.current_player = self.player_names.index(turn_display_name)

            # Show turn message
            player_display_name = self.get_display_name_for_username(player)
            turn_display_name = self.get_display_name_for_username(turn) if turn else "Unknown"

            self.status_label.config(
                text=f"{player_display_name} rolled {last_roll}. Now it's {turn_display_name}'s turn."
            )

            # Enable/disable roll button based on whose turn it is
            can_roll = False
            if self.is_host and self.current_player == 0:
                can_roll = True
            elif not self.is_host and self.current_player == 1:
                can_roll = True

            self.roll_button.config(state=tk.NORMAL if can_roll else tk.DISABLED)
            self.movable = False  # Server handles movement

    def update_players_from_server(self, players_info):
        """Update player names and avatars from server data - FIXED VERSION"""
        if not players_info:
            return

        print(f"Updating players from server: {players_info}")

        # Clear existing mappings
        self.username_to_display = {}
        self.display_to_username = {}

        # Get list of usernames in order they joined
        usernames = list(players_info.keys())

        for i, username in enumerate(usernames):
            player_info = players_info[username]
            display_name = player_info.get("display_name", username)
            display_avatar = player_info.get("display_avatar", "🙂")

            # Store mappings
            self.username_to_display[username] = display_name
            self.display_to_username[display_name] = username

            # Determine which player slot this should go in
            # Host: their username goes to slot 0, other player to slot 1
            # Joiner: their username goes to slot 1, other player to slot 0
            if username == self.logged_username:
                # This is the logged-in user
                player_idx = 0 if self.is_host else 1
            else:
                # This is the other player
                player_idx = 1 if self.is_host else 0

            # Only update if we have a valid slot
            if 0 <= player_idx < len(self.player_names):
                print(f"Updating player {player_idx} with {display_name} ({display_avatar})")
                self.update_player_info(player_idx, display_name, display_avatar)

    def get_display_name_for_username(self, username):
        """Get display name for a given username"""
        return self.username_to_display.get(username, username)

    def move_piece_by_name(self, username, pos):
        """Move a player piece by username"""
        display_name = self.get_display_name_for_username(username)

        if display_name in self.player_names:
            idx = self.player_names.index(display_name)
            self.positions[idx] = pos
            self.move_token(idx)
            return

        # Fallback
        if username in self.player_names:
            idx = self.player_names.index(username)
            self.positions[idx] = pos
            self.move_token(idx)