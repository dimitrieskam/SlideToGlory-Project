# Import SQLAlchemy core components for defining tables and connecting to the DB
from sqlalchemy import Column, Integer, String, create_engine
# Import ORM helpers: base class generator and session factory
from sqlalchemy.orm import declarative_base, sessionmaker

# Create a base class for ORM models
# All database models (tables) will inherit from this Base
Base = declarative_base()

# Create a database engine
# "sqlite:///snake_ladder.db" → SQLite file named snake_ladder.db in current folder
# connect_args={"check_same_thread": False} → allow connections across threads
engine = create_engine("sqlite:///snake_ladder.db", connect_args={"check_same_thread": False})

# Create a session factory (used to interact with the DB)
# - bind=engine → sessions will use our engine
# - autoflush=False → changes won’t be automatically flushed to DB before queries
# - autocommit=False → we must explicitly call commit() to save changes
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# Define the User model → this maps to a "users" table in the database
class User(Base):
    __tablename__ = "users"  # Table name in the database

    # Primary key column (unique identifier for each row)
    id = Column(Integer, primary_key=True, index=True)

    # Username column
    # - unique=True → no duplicate usernames allowed
    # - index=True → indexed for faster searches
    # - nullable=False → must always have a value
    username = Column(String, unique=True, index=True, nullable=False)

    # Password column (⚠ should store hashed passwords, not plain text!)
    password = Column(String, nullable=False)

    # Avatar column, defaults to 🙂 if not provided
    avatar = Column(String, default="🙂")

    # Wins counter, starts at 0
    wins = Column(Integer, default=0)

    # Losses counter, starts at 0
    losses = Column(Integer, default=0)

    # Fastest win time in seconds
    # Default is 9999 (acts like "not set")
    fastest_win_seconds = Column(Integer, default=9999)


# Function to create the database and tables (if they don’t exist yet)
def create_db():
    # Create all tables defined on Base (currently just "users")
    # Does nothing if tables already exist
    Base.metadata.create_all(bind=engine)
