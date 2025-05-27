import pandas as pd
import sqlite3

def load_data(db_path="emotion_data.db"):
    conn = sqlite3.connect(db_path)
    df = pd.read_sql("""
        SELECT 
            e.timestamp,
            e.user_id,
            u.name,
            u.gender,
            e.hunger_before,
            e.satiety_after,
            e.emotion,
            e.sleep_hours,
            e.location,
            e.company,
            e.phone,
            e.cycle_day,
            e.binge_eating
        FROM entries e
        LEFT JOIN users u ON u.user_id = e.user_id
        ORDER BY e.timestamp DESC
    """, conn)
    conn.close()
    df["timestamp"] = pd.to_datetime(df["timestamp"])
    return df

if __name__ == "__main__":
    df = load_data()
    print(df.head(10))  # Показать первые 10 записей
