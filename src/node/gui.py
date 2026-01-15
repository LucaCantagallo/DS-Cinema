import tkinter as tk
from tkinter import messagebox
from functools import partial

class CinemaGUI:
    def __init__(self, node_id, total_seats=25, on_seat_click=None):
        self.node_id = node_id
        self.total_seats = total_seats
        self.on_seat_click = on_seat_click
        
        self.root = tk.Tk()
        self.root.title(f"DS-Cinema Node: {node_id}")
        self.root.geometry("400x500")
        
        self.buttons = {}
        self._setup_ui()

    def _setup_ui(self):
        main_frame = tk.Frame(self.root, padx=20, pady=20)
        main_frame.pack(expand=True, fill="both")
        
        tk.Label(main_frame, text=f"Node: {self.node_id}", font=("Arial", 14, "bold")).pack(pady=10)
        
        grid_frame = tk.Frame(main_frame)
        grid_frame.pack()
        
        rows = 5
        cols = 5
        
        for i in range(self.total_seats):
            r = i // cols
            c = i % cols
            
            btn = tk.Button(
                grid_frame,
                text=f"S{i}",
                width=6,
                height=3,
                bg="#90EE90",
                command=partial(self._handle_click, i)
            )
            btn.grid(row=r, column=c, padx=2, pady=2)
            self.buttons[i] = btn

        self.log_text = tk.Text(main_frame, height=8, state='disabled')
        self.log_text.pack(pady=20, fill="x")

    def _handle_click(self, seat_id):
        if self.on_seat_click:
            self.on_seat_click(seat_id)

    def update_seat_color(self, seat_id, color):
        self.root.after(0, lambda: self._update_seat_color_safe(seat_id, color))

    def _update_seat_color_safe(self, seat_id, color):
        if seat_id in self.buttons:
            self.buttons[seat_id].configure(bg=color)

    def log(self, message):
        self.root.after(0, lambda: self._log_safe(message))

    def _log_safe(self, message):
        self.log_text.configure(state='normal')
        self.log_text.insert("1.0", message + "\n")
        self.log_text.configure(state='disabled')

    def start(self):
        self.root.mainloop()