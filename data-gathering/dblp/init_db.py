from sqlalchemy import Column, ForeignKey, Table
from sqlalchemy import Integer, String, Boolean, Text, Float
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base

Base = declarative_base()


class Venue(Base):
    __tablename__ = 'venues'
    __table_args__ = {'schema': 'user_schema'}
    id = Column(Integer, primary_key=True)
    acronym = Column(String(20), nullable=False)
    name = Column(String(200))
    type = Column(String(20))

    def __init__(self, acronym, name, vtype):
        self.acronym = acronym
        self.name = name
        self.type = vtype

    def __repr__(self):
        return "<Venue('%s')>" % (self.acronym)


class Paper(Base):
    __tablename__ = 'papers'
    __table_args__ = {'schema': 'user_schema'}
    id = Column(Integer, primary_key=True)
    venue_id = Column(Integer, ForeignKey('user_schema.venues.id'))
    year = Column(Integer)
    ee = Column(String(500))
    doi = Column(Text)

    venue = relationship("Venue", backref="papers")

    def __init__(self, venue, year, ee, doi):
        self.venue = venue
        self.year = year
        self.ee = ee
        self.doi = doi

    def __repr__(self):
        return "<Paper('%d, %s')>" % (self.id, self.doi)


class URL(Base):
    __tablename__ = 'urls'
    __table_args__ = {'schema': 'user_schema'}
    id = Column(Integer, primary_key=True)
    url = Column(String(500), nullable=False)
    active = Column(Boolean)
    status_code = Column(Integer)
    network_error = Column(Integer)
    section = Column(String(500))


    def __init__(self, url, active, status_code, network_error=None):
        self.url = url
        self.active = active
        self.status_code = status_code
        self.network_error = network_error

    def __repr__(self):
        return "<URL('%s')>" % (self.url)


class PaperURL(Base):
    __tablename__ = 'paper_urls'
    __table_args__ = {'schema': 'user_schema'}
    paper_id = Column(Integer, ForeignKey('user_schema.papers.id'), primary_key=True)
    url_id = Column(Integer, ForeignKey('user_schema.urls.id'), primary_key=True)

    paper = relationship("Paper", backref="paper_urls")
    url = relationship("URL", backref="paper_urls")

    def __init__(self, paper, url):
        self.paper = paper
        self.url = url

    def __repr__(self):
        return "<PaperURL('%d, %d')>" % (self.paper_id, self.url_id)


def initDB(engine):
    Base.metadata.create_all(engine)
    print('Database structure created')


def cleanStart(engine):
    Base.metadata.drop_all(engine)
    print('Database structure reset')
