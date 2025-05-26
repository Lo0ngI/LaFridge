import cv2
import sqlite3
import csv
import os
from datetime import datetime
import time
from ultralytics import YOLO
import tkinter as tk
from tkinter import filedialog, messagebox, scrolledtext
from PIL import Image, ImageTk
import numpy as np
import google.generativeai as genai
import pyttsx3
import speech_recognition as sr

class FoodDetectionApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Food Detection App (Fridge Camera)")
        self.root.geometry("700x800")
        self.root.minsize(700, 800)

        self.model = YOLO("best.pt")
        self.is_webcam_running = False
        self.cap = None
        self.last_save_time = 0
        self.save_interval = 10

        self.conn = sqlite3.connect("food_detections.db")
        self.create_db()

        self.gemini_api_key = "AIzaSyCVEXKbvSl2MKxSz1cIQ6EpQnFwIDshvG8"
        genai.configure(api_key=self.gemini_api_key)
        self.gemini_model = genai.GenerativeModel("gemini-1.5-flash")

        # Initialize text-to-speech engine with configurations
        self.tts_engine = pyttsx3.init()
        # Set speech rate to 150 (default is 200, lower is slower, higher is faster)
        self.tts_engine.setProperty('rate', 150)
        # Select a different voice if available
        voices = self.tts_engine.getProperty('voices')
        if len(voices) > 1:
            # Use the second voice if it exists
            self.tts_engine.setProperty('voice', voices[1].id)
        else:
            # Fallback to default voice if only one voice is available
            self.tts_engine.setProperty('voice', voices[0].id)

        # Initialize speech recognition
        self.recognizer = sr.Recognizer()

        self.main_display_frame = tk.Frame(root)
        self.main_display_frame.pack(pady=10)

        self.canvas = tk.Canvas(self.main_display_frame, width=480, height=360)
        self.canvas.grid(row=0, column=0, padx=5, pady=5)

        self.indicator_frame = tk.Frame(self.main_display_frame)
        self.indicator_frame.grid(row=0, column=1, padx=5, pady=5, sticky=tk.N)

        self.indicator_canvas = tk.Canvas(self.indicator_frame, width=20, height=20)
        self.indicator_canvas.pack(pady=2)
        self.indicator = self.indicator_canvas.create_rectangle(0, 0, 20, 20, fill="green")

        self.indicator_label = tk.Label(self.indicator_frame, text="Ready to save")
        self.indicator_label.pack(pady=2)

        self.control_frame = tk.Frame(root)
        self.control_frame.pack(pady=5)
        self.control_frame.config(borderwidth=1, relief="solid", bg="#f0f0f0")

        self.btn_webcam = tk.Button(self.control_frame, text="Start Webcam", command=self.toggle_webcam)
        self.btn_webcam.pack(side=tk.LEFT, padx=5)

        self.btn_upload = tk.Button(self.control_frame, text="Upload Image", command=self.upload_image)
        self.btn_upload.pack(side=tk.LEFT, padx=5)

        self.btn_export = tk.Button(self.control_frame, text="Export to CSV", command=self.export_to_csv)
        self.btn_export.pack(side=tk.LEFT, padx=5)

        self.btn_delete_db = tk.Button(self.control_frame, text="Delete Database", command=self.delete_database)
        self.btn_delete_db.pack(side=tk.LEFT, padx=5)

        self.btn_voice = tk.Button(self.control_frame, text="Voice Command", command=self.listen_to_voice)
        self.btn_voice.pack(side=tk.LEFT, padx=5)

        self.label_status = tk.Label(root, text="Status: Idle")
        self.label_status.pack(pady=5)

        self.chat_wrapper = tk.Frame(root)
        self.chat_wrapper.pack(pady=10, fill=tk.X, expand=True)

        self.chat_frame = tk.Frame(self.chat_wrapper)
        self.chat_frame.pack(anchor=tk.CENTER)
        self.chat_frame.config(borderwidth=2, relief="solid", bg="#f0f0f0")

        self.chat_label = tk.Label(self.chat_frame, text="Ask Gemini about your fridge contents:")
        self.chat_label.grid(row=0, column=0, columnspan=2, sticky=tk.W, pady=5)

        self.chat_display = scrolledtext.ScrolledText(self.chat_frame, width=70, height=15, wrap=tk.WORD, state='disabled')
        self.chat_display.grid(row=2, column=0, columnspan=2, pady=5, sticky=tk.EW)

        self.chat_entry = tk.Entry(self.chat_frame, width=50, state='normal')
        self.chat_entry.grid(row=1, column=0, pady=5, sticky=tk.EW)
        self.chat_entry.bind("<Return>", self.send_gemini_query)

        self.btn_send = tk.Button(self.chat_frame, text="Send to Gemini", command=self.send_gemini_query)
        self.btn_send.grid(row=1, column=1, pady=5, padx=5, sticky=tk.E)

        self.bottom_padding = tk.Frame(root, height=40)
        self.bottom_padding.pack(pady=20)

        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_db(self):
        cursor = self.conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS detections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                food_item TEXT,
                confidence REAL,
                timestamp TEXT,
                image_path TEXT
            )
        ''')
        self.conn.commit()

    def save_to_db(self, food_item, confidence, image_path):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        cursor = self.conn.cursor()
        cursor.execute('''
            INSERT INTO detections (food_item, confidence, timestamp, image_path)
            VALUES (?, ?, ?, ?)
        ''', (food_item, confidence, timestamp, image_path))
        self.conn.commit()

    def remove_ingredients(self, ingredients):
        cursor = self.conn.cursor()
        removed_items = []
        for ingredient in ingredients:
            cursor.execute("SELECT COUNT(*) FROM detections WHERE food_item = ?", (ingredient,))
            count = cursor.fetchone()[0]
            if count > 0:
                cursor.execute("DELETE FROM detections WHERE food_item = ?", (ingredient,))
                removed_items.append(ingredient)
        self.conn.commit()
        if removed_items:
            self.chat_display.config(state='normal')
            self.chat_display.insert(tk.END, f"Gemini: Removed {', '.join(removed_items)} from the database.\n\n")
            self.chat_display.config(state='disabled')
            self.chat_display.see(tk.END)
        else:
            self.chat_display.config(state='normal')
            self.chat_display.insert(tk.END, f"Gemini: No matching items found in the database to remove.\n\n")
            self.chat_display.config(state='disabled')
            self.chat_display.see(tk.END)

    def speak_text(self, text):
        self.tts_engine.say(text)
        self.tts_engine.runAndWait()

    def listen_to_voice(self):
        with sr.Microphone() as source:
            self.chat_display.config(state='normal')
            self.chat_display.insert(tk.END, "Listening for your voice command...\n")
            self.chat_display.config(state='disabled')
            self.chat_display.see(tk.END)

            # Adjust for ambient noise and listen
            self.recognizer.adjust_for_ambient_noise(source)
            try:
                audio = self.recognizer.listen(source, timeout=5, phrase_time_limit=20)
                query = self.recognizer.recognize_google(audio)
                self.chat_display.config(state='normal')
                self.chat_display.insert(tk.END, f"Voice Command: {query}\n")
                self.chat_display.config(state='disabled')
                self.chat_display.see(tk.END)

                # Send the recognized query to Gemini
                self.chat_entry.delete(0, tk.END)
                self.chat_entry.insert(0, query)
                self.send_gemini_query()

            except sr.WaitTimeoutError:
                self.chat_display.config(state='normal')
                self.chat_display.insert(tk.END, "No speech detected within the timeout period.\n\n")
                self.chat_display.config(state='disabled')
                self.chat_display.see(tk.END)
            except sr.UnknownValueError:
                self.chat_display.config(state='normal')
                self.chat_display.insert(tk.END, "Could not understand the audio.\n\n")
                self.chat_display.config(state='disabled')
                self.chat_display.see(tk.END)
            except sr.RequestError as e:
                self.chat_display.config(state='normal')
                self.chat_display.insert(tk.END, f"Speech recognition error: {e}\n\n")
                self.chat_display.config(state='disabled')
                self.chat_display.see(tk.END)

    def export_to_csv(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM detections")
        rows = cursor.fetchall()
        
        with open("food_detections.csv", "w", newline="") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["ID", "Food Item", "Confidence", "Timestamp", "Image Path"])
            writer.writerows(rows)
        
        messagebox.showinfo("Success", "Data exported to food_detections.csv")

    def delete_database(self):
        if messagebox.askyesno("Confirm Delete", "Are you sure you want to delete all database entries? This cannot be undone."):
            try:
                cursor = self.conn.cursor()
                cursor.execute("DELETE FROM detections")
                self.conn.commit()
                messagebox.showinfo("Success", "All database entries have been deleted.")
            except sqlite3.Error as e:
                messagebox.showerror("Error", f"Failed to delete database entries: {e}")

    def get_database_summary(self):
        cursor = self.conn.cursor()
        cursor.execute("SELECT food_item, timestamp FROM detections")
        rows = cursor.fetchall()
        if not rows:
            return "The database is empty."
        summary = "Database contents:\n"
        for row in rows:
            summary += f"- {row[0]} (detected on {row[1]})\n"
        return summary

    def send_gemini_query(self, event=None):
        query = self.chat_entry.get().strip()
        if not query:
            messagebox.showwarning("Warning", "Please enter a query.")
            return

        if query.lower().startswith("remove "):
            try:
                items_part = query[6:].strip()
                if not items_part:
                    messagebox.showwarning("Warning", "Please specify items to remove (e.g., 'remove black beans, potatoes').")
                    return
                ingredients = [ing.strip() for ing in items_part.split(",") if ing.strip()]
                if not ingredients:
                    messagebox.showwarning("Warning", "No valid items specified to remove.")
                    return
                self.remove_ingredients(ingredients)
                self.chat_entry.delete(0, tk.END)
                return
            except Exception as e:
                messagebox.showerror("Error", f"Failed to process remove command: {e}")
                self.chat_entry.delete(0, tk.END)
                return

        db_summary = self.get_database_summary()
        prompt = f"""
        You are Gemini, an AI assistant. I have a database of food items detected in a fridge. Here is the current contents:
        {db_summary}

        Please answer the following query based on this data: {query}
        If asked to suggest a dish, include a simple recipe with ingredients from the database and mention that the user can remove used ingredients by saying 'remove [ing1, ing2, ...]'. Don't write any special symbols in your answers
        """

        try:
            response = self.gemini_model.generate_content(prompt)
            gemini_response = response.text

            self.chat_display.config(state='normal')
            self.chat_display.insert(tk.END, f"You: {query}\n")
            self.chat_display.insert(tk.END, f"Gemini: {gemini_response}\n\n")
            self.chat_display.config(state='disabled')
            self.chat_display.see(tk.END)
            self.chat_entry.delete(0, tk.END)

            self.speak_text(gemini_response)

        except Exception as e:
            messagebox.showerror("Error", f"Failed to connect to Gemini API: {e}")
            self.chat_display.config(state='normal')
            self.chat_display.insert(tk.END, f"Error: Failed to connect to Gemini API\n\n")
            self.chat_display.config(state='disabled')
            self.chat_display.see(tk.END)

    def process_frame(self, frame):
        results = self.model(frame)[0]
        max_conf = 0
        detected_food = "Unknown"
        save_path = ""

        for box in results.boxes:
            conf = box.conf.item()
            cls = int(box.cls.item())
            label = self.model.names[cls]
            if conf > max_conf:
                max_conf = conf
                detected_food = label

            x1, y1, x2, y2 = map(int, box.xyxy[0])
            cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 255, 0), 2)
            cv2.putText(frame, f"{label} {conf:.2f}", (x1, y1-10),
                       cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)

        current_time = time.time()
        if max_conf > 0.5 and (current_time - self.last_save_time) >= self.save_interval:
            save_path = f"detections/{detected_food}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.jpg"
            os.makedirs("detections", exist_ok=True)
            cv2.imwrite(save_path, frame)
            self.save_to_db(detected_food, max_conf, save_path)
            self.last_save_time = current_time

        if (current_time - self.last_save_time) < self.save_interval:
            self.indicator_canvas.itemconfig(self.indicator, fill="red")
            self.indicator_label.config(text="Waiting to save")
        else:
            self.indicator_canvas.itemconfig(self.indicator, fill="green")
            self.indicator_label.config(text="Ready to save")

        return frame, detected_food, max_conf

    def update_webcam(self):
        if self.is_webcam_running:
            ret, frame = self.cap.read()
            if ret:
                frame, food, conf = self.process_frame(frame)
                frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                frame = cv2.resize(frame, (480, 360))
                photo = ImageTk.PhotoImage(image=Image.fromarray(frame))
                self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
                self.canvas.image = photo
                self.label_status.config(text=f"Status: Detected {food} ({conf:.2f})")
            self.root.after(10, self.update_webcam)

    def toggle_webcam(self):
        if not self.is_webcam_running:
            self.cap = cv2.VideoCapture(1)
            if not self.cap.isOpened():
                messagebox.showerror("Error", "Cannot open webcam")
                return
            self.is_webcam_running = True
            self.btn_webcam.config(text="Stop Webcam")
            self.last_save_time = time.time()
            self.update_webcam()
        else:
            self.is_webcam_running = False
            self.btn_webcam.config(text="Start Webcam")
            self.cap.release()
            self.label_status.config(text="Status: Idle")
            self.indicator_canvas.itemconfig(self.indicator, fill="green")
            self.indicator_label.config(text="Ready to save")

    def upload_image(self):
        file_path = filedialog.askopenfilename(filetypes=[("Image files", "*.jpg *.jpeg *.png")])
        if file_path:
            image = cv2.imread(file_path)
            if image is None:
                messagebox.showerror("Error", "Cannot load image")
                return
            image, food, conf = self.process_frame(image)
            image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
            image = cv2.resize(image, (480, 360))
            photo = ImageTk.PhotoImage(image=Image.fromarray(image))
            self.canvas.create_image(0, 0, image=photo, anchor=tk.NW)
            self.canvas.image = photo
            self.label_status.config(text=f"Status: Detected {food} ({conf:.2f})")

    def on_closing(self):
        if self.is_webcam_running:
            self.is_webcam_running = False
            self.cap.release()
        self.conn.close()
        self.tts_engine.stop()
        self.root.destroy()

if __name__ == "__main__":
    root = tk.Tk()
    app = FoodDetectionApp(root)
    root.mainloop()