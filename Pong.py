from tkinter import Tk, Button, Label, Entry, messagebox
import arcade
import socket
import threading
import json
import random
import math

SCREEN_HEIGHT = 700
SCREEN_WIDTH = 1000
SCREEN_TITLE = "CL Pong"
BALL_SPEED = 300
PADDLE_SPEED = 200
IP = "0.0.0.0"
PORT = 42069
HOST = False
PADDLE_WIDTH = 10
PADDLE_HEIGHT = 100

HEADERSIZE = 5


if SCREEN_HEIGHT > 9999 or SCREEN_WIDTH > 9999:
    print("Unsuported screen height or width")
    exit()


class Lan:
    """ Class for communicating with the host or being the host """

    def __init__(self):
        pass

    def start(self):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        if HOST:
            try:
                self.sock.bind((IP, PORT))
            except OSError:
                messagebox.showerror("ERROR", "There is propably already a game running.")
            self.sock.listen(5)
        else:
            self.sock.connect((IP, PORT))
            game.started = True
        if HOST:
            c, a = self.sock.accept()
            game.started = True
            self.c = c
            self.a = a
            data = {
                "type": "ball",
                "x": game.ball.x,
                "y": game.ball.y,
                "cx": game.ball.change_x,
                "cy": game.ball.change_y
            }
            self.send(data)

        cThread = threading.Thread(target=self.connection)
        cThread.daemon = True
        cThread.start()

    def send(self, data):
        data = json.dumps(data)
        data = f"{len(data):^{HEADERSIZE}}" + data
        data = bytes(data, "utf-8")
        if HOST:
            self.c.send(data)  # send the data to connection if host
        else:
            self.sock.send(data)  # send the data to server if not host

    def connection(self):
        while True:
            if HOST:
                data = self.c.recv(HEADERSIZE)
                full_data = self.c.recv(int(data.decode("utf-8")))
            else:
                data = self.sock.recv(HEADERSIZE)
                full_data = self.sock.recv(int(data.decode("utf-8")))

            # handle data
            full_data = json.loads(full_data)
            if full_data['type'] == 'ball':
                game.ball.x = full_data['x']
                game.ball.y = full_data['y']
                game.ball.change_x = full_data['cx']
                game.ball.change_y = full_data['cy']
            if full_data['type'] == 'padd':
                game.other_paddle.y = full_data['y']
                game.other_paddle.change_y = full_data['cy']
            if full_data['type'] == 'scre':
                game.score = [int(float(full_data['p1'])), int(float(full_data['p2']))]


class Ball:
    """ The class for the ball in te game """

    def __init__(self):
        self.radius = 10
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_WIDTH // 2
        self.change_x = 0
        self.change_y = 0
        if HOST:
            self.start_moving()

    def reset(self):
        self.x = SCREEN_WIDTH // 2
        self.y = SCREEN_HEIGHT // 2
        self.start_moving()
        data = {
            "type": "ball",
            "x": self.x,
            "y": self.y,
            "cx": self.change_x,
            "cy": self.change_y
        }
        game.lan.send(data)

    def start_moving(self):
        self.change_x = random.uniform(BALL_SPEED / 2, BALL_SPEED)  # get random float with the change_x at least being 50% of the speed
        # use pytagoras to calculate self.change_y
        self.change_y = math.sqrt(BALL_SPEED * BALL_SPEED - self.change_x * self.change_x)
        # change going left or right randomly
        self.change_x = self.change_x * random.choice([-1, 1])

    def update(self, delta_time):
        if HOST:
            updated_direction = False
            if self.y + self.radius > SCREEN_HEIGHT or self.y - self.radius < 0:
                # bounce from the top or bottom walls
                self.change_y = self.change_y * -1
                updated_direction = True

            # Check for collision with paddle
            if (self.change_x < 0 and self.x - self.radius < PADDLE_WIDTH) or (self.change_x > 0 and self.x + self.radius > SCREEN_WIDTH - PADDLE_WIDTH):
                bounce = False
                if self.change_x > 0 and (self.y + self.radius < game.other_paddle.y + PADDLE_HEIGHT / 2 and self.y - self.radius > game.other_paddle.y - PADDLE_HEIGHT / 2):
                    bounce = True
                elif self.change_x < 0 and (self.y + self.radius < game.paddle.y + PADDLE_HEIGHT / 2 and self.y - self.radius > game.paddle.y - PADDLE_HEIGHT / 2):
                    bounce = True
                if bounce:
                    updated_direction = True
                    self.change_x = self.change_x * -1

            if updated_direction:
                data = {
                    "type": "ball",
                    "x": self.x,
                    "y": self.y,
                    "cx": self.change_x,
                    "cy": self.change_y
                }
                game.lan.send(data)

            # check for score
            scored = False
            if self.x > SCREEN_WIDTH:
                game.score[0] += 1
                scored = True
                self.reset()
            elif self.x < 0:
                game.score[1] += 1
                scored = True
                self.reset()
            if scored:
                data = {
                    "type": "scre",
                    "p1": game.score[0],
                    "p2": game.score[1]
                }
                game.lan.send(data)

        # update possition
        self.x += self.change_x * delta_time
        self.y += self.change_y * delta_time

    def on_draw(self):
        arcade.draw_circle_filled(self.x, self.y, self.radius, (255, 255, 255))


class Paddle:
    """ The class for both the paddles in the game """

    def __init__(self, x):
        self.x = x
        self.y = SCREEN_HEIGHT / 2
        self.change_y = 0
        self.width = PADDLE_WIDTH
        self.height = PADDLE_HEIGHT

    def update(self, delta_time):
        if not ((self.y - self.height / 2 < 0 and self.change_y < 0) or (self.y + self.height / 2 > SCREEN_HEIGHT and self.change_y > 0)):
            self.y += self.change_y * delta_time

    def on_draw(self):
        arcade.draw_rectangle_filled(self.x, self.y, self.width, self.height, (255, 255, 255))


class Game(arcade.Window):
    """ Main game class """

    def __init__(self):
        super().__init__(SCREEN_WIDTH, SCREEN_HEIGHT, SCREEN_TITLE)
        arcade.set_background_color((0, 0, 0))

    def setup(self):
        self.started = False
        self.ball = Ball()
        self.score = [0, 0]
        if HOST:
            x = PADDLE_WIDTH // 2
        else:
            x = SCREEN_WIDTH - PADDLE_WIDTH // 2
        self.paddle = Paddle(x)
        if HOST:
            x = SCREEN_WIDTH - PADDLE_WIDTH // 2
        else:
            x = PADDLE_WIDTH // 2
        self.other_paddle = Paddle(x)
        self.lan = Lan()
        lThread = threading.Thread(target=self.lan.start)
        lThread.daemon = True
        lThread.start()

    def update(self, delta_time):
        if not self.started:
            return
        self.ball.update(delta_time)
        self.paddle.update(delta_time)
        self.other_paddle.update(delta_time)

    def on_draw(self):
        arcade.start_render()
        # draw all the parts
        self.paddle.on_draw()
        self.other_paddle.on_draw()
        self.ball.on_draw()
        # draw the score board
        arcade.draw_text(f"{game.score[0]}    {game.score[1]}", SCREEN_WIDTH / 2, SCREEN_HEIGHT - 50, arcade.color.WHITE, 40, width=200, align="center", anchor_y="center", anchor_x="center")

    def on_key_press(self, key, mod):
        updated_direction = False
        if key == arcade.key.W:
            self.paddle.change_y += PADDLE_SPEED
            updated_direction = True
        if key == arcade.key.S:
            self.paddle.change_y -= PADDLE_SPEED
            updated_direction = True

        if updated_direction:
            data = {
                "type": "padd",
                "y": self.paddle.y,
                "cy": self.paddle.change_y
            }
            self.lan.send(data)

    def on_key_release(self, key, mod):
        updated_direction = False
        if key == arcade.key.W:
            self.paddle.change_y -= PADDLE_SPEED
            updated_direction = True
        if key == arcade.key.S:
            self.paddle.change_y += PADDLE_SPEED
            updated_direction = True

        if updated_direction:
            data = {
                "type": "padd",
                "y": self.paddle.y,
                "cy": self.paddle.change_y
            }
            self.lan.send(data)


def main():
    global root
    root = Tk()
    root.title("PONG")

    Label(
        text="PONG",
        font="arial 30"
    ).grid(row=0, column=0, columnspan=2)

    Button(
        text="HOST",
        font="arial 20",
        command=start_host
    ).grid(row=1, column=0)

    Button(
        text="JOIN",
        font="arial 20",
        command=join_screen,
    ).grid(row=1, column=1)

    root.mainloop()


def join_screen():
    for i in root.winfo_children():
        i.destroy()

    Label(
        text="JOIN GAME",
        font="arial 30"
    ).grid(row=0, column=0)

    ip_entry = Entry(
        font='arial 20'
    )

    ip_entry.grid()

    Button(
        text="JOIN",
        font="arial 20",
        command=lambda ip_entry=ip_entry: join(ip_entry)
    ).grid(row=2, column=0)


def join(ip_entry):
    global IP
    IP = ip_entry.get()
    root.destroy()
    start()


def start_host():
    global HOST
    HOST = True
    start()


def start():
    global game
    game = Game()
    game.setup()
    arcade.run()


if __name__ == "__main__":
    main()
