import sqlite3
from datetime import datetime

def connect_db():
    """Connect to the SQLite database."""
    conn = sqlite3.connect("food_detections.db")
    cursor = conn.cursor()
    return conn, cursor

def close_db(conn):
    """Close the database connection."""
    conn.close()

def query_all_detections():
    """Query all detections from the database."""
    conn, cursor = connect_db()
    cursor.execute("SELECT * FROM detections")
    rows = cursor.fetchall()
    print("\nAll Detections:")
    print("ID | Food Item | Confidence | Timestamp | Image Path")
    for row in rows:
        print(f"{row[0]} | {row[1]} | {row[2]:.2f} | {row[3]} | {row[4]}")
    close_db(conn)

def query_by_food_item(food_item):
    """Query detections for a specific food item."""
    conn, cursor = connect_db()
    cursor.execute("SELECT * FROM detections WHERE food_item = ?", (food_item,))
    rows = cursor.fetchall()
    print(f"\nDetections for {food_item}:")
    print("ID | Food Item | Confidence | Timestamp | Image Path")
    for row in rows:
        print(f"{row[0]} | {row[1]} | {row[2]:.2f} | {row[3]} | {row[4]}")
    close_db(conn)

def query_by_date_range(start_date, end_date):
    """Query detections within a date range."""
    conn, cursor = connect_db()
    cursor.execute(
        "SELECT * FROM detections WHERE timestamp BETWEEN ? AND ?",
        (start_date, end_date)
    )
    rows = cursor.fetchall()
    print(f"\nDetections from {start_date} to {end_date}:")
    print("ID | Food Item | Confidence | Timestamp | Image Path")
    for row in rows:
        print(f"{row[0]} | {row[1]} | {row[2]:.2f} | {row[3]} | {row[4]}")
    close_db(conn)

def query_high_confidence(threshold=0.8):
    """Query detections with confidence above a threshold."""
    conn, cursor = connect_db()
    cursor.execute("SELECT * FROM detections WHERE confidence > ?", (threshold,))
    rows = cursor.fetchall()
    print(f"\nDetections with confidence > {threshold}:")
    print("ID | Food Item | Confidence | Timestamp | Image Path")
    for row in rows:
        print(f"{row[0]} | {row[1]} | {row[2]:.2f} | {row[3]} | {row[4]}")
    close_db(conn)

def query_food_item_counts():
    """Query count of detections for each food item."""
    conn, cursor = connect_db()
    cursor.execute("SELECT food_item, COUNT(*) as count FROM detections GROUP BY food_item")
    rows = cursor.fetchall()
    print("\nCount of Detections by Food Item:")
    print("Food Item | Count")
    for row in rows:
        print(f"{row[0]} | {row[1]}")
    close_db(conn)

def query_oldest_items(limit=3):
    """Query the oldest detections (default: 3)."""
    conn, cursor = connect_db()
    cursor.execute("SELECT * FROM detections ORDER BY timestamp ASC LIMIT ?", (limit,))
    rows = cursor.fetchall()
    print(f"\n{limit} Oldest Detections:")
    print("ID | Food Item | Confidence | Timestamp | Image Path")
    for row in rows:
        print(f"{row[0]} | {row[1]} | {row[2]:.2f} | {row[3]} | {row[4]}")
    close_db(conn)

def delete_all_detections():
    """Delete all detections from the database."""
    conn, cursor = connect_db()
    cursor.execute("DELETE FROM detections")
    conn.commit()
    print("\nAll detections have been deleted from the database.")
    close_db(conn)

if __name__ == "__main__":
    # Example usage of queries
    query_all_detections()  # Get all detections

    #query_by_food_item("pizza")  # Replace 'pizza' with your food item

    # Query by date range (format: 'YYYY-MM-DD HH:MM:SS')
    #start_date = "2025-05-01 00:00:00"
    #end_date = "2025-05-26 23:59:59"
    #query_by_date_range(start_date, end_date)

    #query_high_confidence(0.8)  # Get detections with confidence > 0.8

    query_food_item_counts()  # Count detections by food item

    query_oldest_items(3)  # Get the 3 oldest detections

    #delete_all_detections()  # Uncomment to delete all detections