import os
import sqlite3
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
from datetime import datetime


class DatabaseManager:
    def __init__(self, db_path):
        self.db_path = db_path
        self.init_database()

    def init_database(self):
        """Initialize the database tables and relationships based on the entity models."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Main PDF files table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS pdf_files (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    file_path TEXT UNIQUE,
                    file_name TEXT,
                    folder_name TEXT,
		            cover BLOB,
                    file_type TEXT DEFAULT 'pdf',
                    language TEXT,
                    last_modified TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Tags table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS tags (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # Authors table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS authors (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT UNIQUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')

            # File-Tag relationship table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_tags (
                    file_id INTEGER,
                    tag_id INTEGER,
                    FOREIGN KEY (file_id) REFERENCES pdf_files (id) ON DELETE CASCADE,
                    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE,
                    PRIMARY KEY (file_id, tag_id)
                )
            ''')

            # File-Author relationship table
            cursor.execute('''
                CREATE TABLE IF NOT EXISTS file_authors (
                    file_id INTEGER,
                    author_id INTEGER,
                    FOREIGN KEY (file_id) REFERENCES pdf_files (id) ON DELETE CASCADE,
                    FOREIGN KEY (author_id) REFERENCES authors (id) ON DELETE CASCADE,
                    PRIMARY KEY (file_id, author_id)
                )
            ''')
            conn.commit()

    def add_file(self, file_path, file_name, folder_name, last_modified, tags=None, authors=None):
        """Add or update a PDF file in the database and handle tags and authors."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Insert or replace file record
            cursor.execute('''
                INSERT OR REPLACE INTO pdf_files (file_path, file_name, folder_name, last_modified)
                VALUES (?, ?, ?, ?)
            ''', (file_path, file_name, folder_name, last_modified))

            # Retrieve the file ID
            cursor.execute('SELECT id FROM pdf_files WHERE file_path = ?', (file_path,))
            file_id = cursor.fetchone()[0]

            # Handle tags
            if tags:
                for tag in tags:
                    cursor.execute('INSERT OR IGNORE INTO tags (name) VALUES (?)', (tag,))
                    cursor.execute('SELECT id FROM tags WHERE name = ?', (tag,))
                    tag_id = cursor.fetchone()[0]
                    cursor.execute('INSERT OR IGNORE INTO file_tags (file_id, tag_id) VALUES (?, ?)', (file_id, tag_id))

            # Handle authors
            if authors:
                for author in authors:
                    cursor.execute('INSERT OR IGNORE INTO authors (name) VALUES (?)', (author,))
                    cursor.execute('SELECT id FROM authors WHERE name = ?', (author,))
                    author_id = cursor.fetchone()[0]
                    cursor.execute('INSERT OR IGNORE INTO file_authors (file_id, author_id) VALUES (?, ?)', (file_id, author_id))

            conn.commit()

    def remove_file(self, file_path):
        """Remove a PDF file and its relationships from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('DELETE FROM pdf_files WHERE file_path = ?', (file_path,))
            conn.commit()

    def get_all_files(self):
        """Retrieve all files and their associated tags and authors from the database."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT * FROM pdf_files')
            return cursor.fetchall()


class PDFFileHandler(FileSystemEventHandler):
    def __init__(self, db_manager):
        self.db_manager = db_manager

    def on_created(self, event):
        if event.is_directory or not event.src_path.lower().endswith('.pdf'):
            return
        self._process_file(event.src_path)

    def on_modified(self, event):
        if event.is_directory or not event.src_path.lower().endswith('.pdf'):
            return
        self._process_file(event.src_path)

    def on_deleted(self, event):
        if event.is_directory or not event.src_path.lower().endswith('.pdf'):
            return
        self.db_manager.remove_file(event.src_path)

    def _process_file(self, file_path):
        file_name = os.path.basename(file_path)
        folder_name = os.path.basename(os.path.dirname(file_path))
        last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))

        # Example tags and authors (adjust this to dynamically retrieve actual tags/authors if necessary)
        tags = ["example_tag"]
        authors = ["example_author"]

        self.db_manager.add_file(file_path, file_name, folder_name, last_modified, tags, authors)


def initial_scan(root_path, db_manager):
    """Perform initial scan of the directory and add all PDF files to the database."""
    for folder_path, _, files in os.walk(root_path):
        for file in files:
            if file.lower().endswith('.pdf'):
                file_path = os.path.join(folder_path, file)
                file_name = os.path.basename(file_path)
                folder_name = os.path.basename(folder_path)
                last_modified = datetime.fromtimestamp(os.path.getmtime(file_path))

                # Example tags and authors (adjust as necessary)
                tags = ["example_tag"]
                authors = ["example_author"]

                db_manager.add_file(file_path, file_name, folder_name, last_modified, tags, authors)


def main(root_path, db_path):
    # Initialize database manager
    db_manager = DatabaseManager(db_path)

    # Perform initial scan
    print("Performing initial scan...")
    initial_scan(root_path, db_manager)

    # Set up file system observer
    event_handler = PDFFileHandler(db_manager)
    observer = Observer()
    observer.schedule(event_handler, root_path, recursive=True)
    observer.start()

    print(f"Monitoring PDF files in {root_path}")
    print("Press Ctrl+C to stop...")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\nStopping file monitor...")
    observer.join()


if __name__ == "__main__":
    # Replace these paths with your actual paths
    ROOT_DIR = "E:\\Downs\\kat\\kath"
    DB_PATH = "pdf_files.db"
    main(ROOT_DIR, DB_PATH)
