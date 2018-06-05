#!/usr/bin/env python

from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy import BINARY
from sqlalchemy import LargeBinary
from sqlalchemy import String
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.sql import func

Base = declarative_base()

class Token(Base):
    __tablename__ = 'tokens'

    hash = Column(BINARY(32), primary_key=True)
    created = Column(DateTime, default=func.now())  # default=datetime.datetime.utcnow)
    by = Column(String(16))
    sig = Column(LargeBinary())


if __name__ == "__main__":
    from sqlalchemy import create_engine
    from settings import DB_URI
    engine = create_engine(DB_URI)
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
