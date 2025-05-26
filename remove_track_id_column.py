import sqlite3

def remove_track_id_column():
    try:
        # Connect to the database
        conn = sqlite3.connect("food_detections.db")
        cursor = conn.cursor()

        # Create a new table without track_id
        cursor.execute('''
            CREATE TABLE detections_new (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                food_item TEXT,
                confidence REAL,
                timestamp TEXT,
                image_path TEXT
            )
        ''')

        # Copy data from old table to new table, excluding track_id
        cursor.execute('''
            INSERT INTO detections_new (id, food_item, confidence, timestamp, image_path)
            SELECT id, food_item, confidence, timestamp, image_path
            FROM detections
        ''')

        # Drop the old table
        cursor.execute("DROP TABLE detections")

        # Rename the new table to detections
        cursor.execute("ALTER TABLE detections_new RENAME TO detections")

        # Commit changes
        conn.commit()
        print("Successfully removed track_id column from detections table.")

    except sqlite3.Error as e:
        print(f"Error: {e}")

    finally:
        conn.close()

if __name__ == "__main__":
    remove_track_id_column()