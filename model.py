from sqlalchemy import Column, ForeignKey, Integer, String, Text, DateTime
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime


Base = declarative_base()


class User(Base):
    __tablename__ = "user"

    id = Column(Integer, primary_key=True)
    email = Column(String(80), nullable=True)
    name = Column(String(30), nullable=True)

    @property
    def jsonlize(self):
        return {
            "id": self.id,
            "email": self.email,
            "name": self.name,
        }


class Post(Base):
    __tablename__ = "post"

    id = Column(Integer, primary_key=True)
    title = Column(String(30), nullable=True)
    body = Column(Text, nullable=True)
    catalog = Column(Integer, nullable=True)
    author = Column(Integer, ForeignKey("user.id"))
    create_at = Column(DateTime, default=datetime.utcnow, autoincrement=True)

    @property
    def jsonlize(self):
        return {
            "id": self.id,
            "title": self.title,
            "body": self.body,
            "catalog": self.catalog,
            "author": self.author,
            "create_at": self.create_at.strftime("%Y/ %m/ %d %H:%M"),
        }


if __name__ == "__main__":
    from sqlalchemy import create_engine

    engine = create_engine("sqlite:///website.db")
    Base.metadata.create_all(engine)
