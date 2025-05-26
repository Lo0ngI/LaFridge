import sqlite3

def add_track_id_column():
    try:
        # Connect to the database
        conn = sqlite3.connect("food_detections.db")
        cursor = conn.cursor()

        # Add the track_id column
        cursor.execute("ALTER TABLE detections ADD COLUMN track_id INTEGER")

        # Commit the changes
        conn.commit()
        print("Successfully added track_id column to detections table.")

    except sqlite3.Error as e:
        print(f"Error: {e}")
        if "duplicate column name" in str(e):
            print("The track_id column already exists in the table.")

    finally:
        conn.close()

if __name__ == "__main__":
    add_track_id_column()