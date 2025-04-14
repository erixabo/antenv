import curses
import socket
import pandas as pd
import time
import matplotlib.pyplot as plt
import numpy as np
import os

# GQRX TCP/IP kapcsolat beállításai
GQRX_HOST = "127.0.0.1"
GQRX_PORT = 37356

# Adatlista a mérési eredmények tárolására
data = {}

# GQRX kapcsolat létrehozása
def send_gqrx_command(command):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((GQRX_HOST, GQRX_PORT))
        s.sendall((command + "\n").encode())
        time.sleep(0.1)
        response = s.recv(1024).decode().strip()
        return response

def get_signal_strength():
    return float(send_gqrx_command("l STRENGTH"))

def set_gqrx_frequency(freq):
    return send_gqrx_command(f"F {freq}")

def set_gqrx_mode(mode):
    return send_gqrx_command(f"M {mode}")

def plot_polar_chart(data, min_strength, max_strength):
    angles = np.radians(sorted(data.keys()))
    strengths = [data[angle][3] for angle in sorted(data.keys())]
    
    fig, ax = plt.subplots(subplot_kw={'projection': 'polar'})
    ax.scatter(angles, strengths, color='r', label='Jelerősség')
    ax.plot(angles, strengths, linestyle='-', color='b')
    ax.set_theta_zero_location('N')  # 0 fok felül
    ax.set_theta_direction(-1)  # Óramutató járásával megegyező
    ax.set_title("Jelerősség polar diagram")
    ax.set_ylim(min_strength, max_strength)  # Skáladinamika beállítása
    plt.legend()
    plt.savefig("signal_strength_polar.png")
    plt.show()

def main(stdscr):
    curses.curs_set(0)  # Rejtett kurzor
    stdscr.nodelay(0)
    stdscr.keypad(1)

    # Bekérjük a fájl nevét
    stdscr.addstr(0, 0, "Add meg a mentés fájlnevét (pl. measurements.xlsx): ")
    stdscr.refresh()
    curses.echo()
    filename = stdscr.getstr(1, 0, 30).decode().strip()
    
    # Ha nincs kiterjesztés vagy üres, adjunk hozzá egy alapértelmezett nevet
    if not filename:
        filename = "measurements.xlsx"
    elif not filename.lower().endswith(".xlsx"):
        filename += ".xlsx"
    
    stdscr.addstr(2, 0, "Add meg a frekvenciát Hz-ben: ")
    stdscr.refresh()
    freq = stdscr.getstr(3, 0, 20).decode()
    
    stdscr.addstr(4, 0, "Hányszor vegyen mintát egy méréskor? ")
    stdscr.refresh()
    samples = int(stdscr.getstr(5, 0, 5).decode())
    
    stdscr.addstr(6, 0, "Válassz modulációs módot (AM, FM, USB, LSB, CW): ")
    stdscr.refresh()
    mode = stdscr.getstr(7, 0, 10).decode().upper()
    
    # Bemenet ellenőrzése a jelszint skáladinamikához
    while True:
        stdscr.addstr(8, 0, "Adj meg minimum és maximum jelszint értéket (pl. -100 0): ")
        stdscr.refresh()
        input_str = stdscr.getstr(9, 0, 20).decode().strip()
        
        if input_str:
            min_max_vals = input_str.split()
            if len(min_max_vals) == 2:
                try:
                    min_strength, max_strength = float(min_max_vals[0]), float(min_max_vals[1])
                    break
                except ValueError:
                    pass  # Hibás bevitel, újra kérjük
        else:
            min_strength, max_strength = -100, 0  # Alapértelmezett értékek
            break
        
        stdscr.addstr(10, 0, "Hibás bemenet! Próbáld újra.")
        stdscr.refresh()
        time.sleep(1)
    
    curses.noecho()

    # Beállítjuk a GQRX frekvenciáját és modulációját
    set_gqrx_frequency(freq)
    set_gqrx_mode(mode)
    
    angle = 0
    max_angle = 359
    min_angle = 0

    while True:
        stdscr.clear()
        stdscr.addstr(0, 0, f"Nyilakkal állítsd be a szöget ({min_angle}-{max_angle}), Enter: mérés, Q: kilépés")
        stdscr.addstr(1, 0, f"Jelenlegi szög: {angle} fok")
        stdscr.refresh()
        
        key = stdscr.getch()
        if key == curses.KEY_UP and angle < max_angle:
            angle += 1
        elif key == curses.KEY_DOWN and angle > min_angle:
            angle -= 1
        elif key == 10:  # Enter
            signal_values = [get_signal_strength() for _ in range(samples)]
            avg_signal = sum(signal_values) / samples
            timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
            data[angle] = [timestamp, freq, angle, avg_signal]
            stdscr.addstr(3, 0, f"Mért jelszint (átlagolt {samples} mintából): {avg_signal:.2f} dB")
            stdscr.refresh()
            time.sleep(1)
        elif key in [ord('q'), ord('Q')]:  # Kilépés és fájlba írás
            df = pd.DataFrame.from_dict(data, orient='index', columns=["Timestamp", "Frequency", "Angle", "Signal Strength"])
            df.to_excel(filename, index=False)
            plot_polar_chart(data, min_strength, max_strength)
            break

if __name__ == "__main__":
    curses.wrapper(main)
