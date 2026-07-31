import sqlite3
import os
DB_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH =  os.path.join(DB_DIR,"Interaction.db")

with sqlite3.connect(DB_PATH) as connection:


    cursor = connection.cursor()

    create_userinteraction_table_query = '''
    CREATE TABLE IF NOT EXISTS UserInteraction (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faceId TEXT NOT NULL,
    type TEXT NOT NULL CHECK (type IN ('robot', 'user')),
    createdDateTimeUtc TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    text TEXT NOT NULL
);
    '''

    create_chatsummary_table_query = '''
    CREATE TABLE IF NOT EXISTS ChatSummary(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    faceId TEXT NOT NULL,
    summary TEXT NOT NULL,
    createdDateTimeUtc TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now')),
    updatedDateTimeUtc TEXT NOT NULL DEFAULT (STRFTIME('%Y-%m-%dT%H:%M:%fZ', 'now'))
    );
    '''


    cursor.execute(create_userinteraction_table_query)
    cursor.execute(create_chatsummary_table_query)
    connection.commit()

    print("Database and table created and connected successfully !")