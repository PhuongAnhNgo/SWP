from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()


class author(db.Model):
    __tablename__ = "author"
    orchid = db.Column(db.String(19), nullable=True)
    name = db.Column(db.String, unique=True, nullable=True)
    id = db.Column(db.Integer, primary_key=True)

    def to_dict(self):
        return {
            'orchid': self.orchid,
            'name': self.name,
            'id': self.id,
        }


class isauthor(db.Model):
    __tablename__ = "isauthor"
    doi_fk = db.Column(db.ForeignKey('publication.doi'), primary_key=True)
    authorid_fk = db.Column(db.ForeignKey('author.id'), primary_key=True)

    def to_dict(self):
        return {
            'doi_fk': self.doi_FK,
            'authorid_fk': self.orchid_FK,
        }


class journal(db.Model):
    __tablename__ = "journal"
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String, nullable=False)
    issne = db.Column(db.String(50), unique=True)
    issnp = db.Column(db.String(50), unique=True)
    hindex = db.Column(db.Integer)
    sjrindex = db.Column(db.Float)

    def to_dict(self):
        return {
            'id': self.id,
            'title': self.title,
            'issne': self.issnE,
            'issnp': self.issnP,
            'hindex': self.hIndex,
            'sjrindex': self.sjrIndex,
        }


class publication(db.Model):
    __tablename__ = "publication"
    doi = db.Column(db.String(100), primary_key=True)
    title = db.Column(db.String, nullable=False)
    year = db.Column(db.SmallInteger)
    volume = db.Column(db.String)
    issue = db.Column(db.String)
    pages = db.Column(db.String)
    number = db.Column(db.String)
    url = db.Column(db.String)
    abstract = db.Column(db.Text)
    type = db.Column(db.String, nullable=False)

    def to_dict(self):
        return {
            'doi': self.doi,
            'title': self.title,
            'year': self.year,
            'volume': self.volume,
            'issue': self.issue,
            'pages': self.pages,
            'number': self.number,
            'url': self.url,
            'abstract': self.abstract,
            'type': self.type
        }


class topics(db.Model):
    __tablename__ = "topics"
    id = db.Column(db.Integer, primary_key=True)
    topic = db.Column(db.String, nullable=False)
    isbio = db.Column(db.Boolean, nullable=False)

    def to_dict(self):
        return {
            'isbio': self.isBio,
            'topic': self.topic,
            'id': self.id,
        }


class havetopic(db.Model):
    __tablename__ = "havetopic"
    journalid = db.Column(db.ForeignKey('journal.id'), primary_key=True)
    topicid = db.Column(db.ForeignKey('topics.id'), primary_key=True)

    def to_dict(self):
        return {
            'journalid': self.journalId,
            'topicid': self.topicId,
        }


class pubon(db.Model):
    __tablename__ = "pubon"
    venueid = db.Column(db.ForeignKey('venue.id'), primary_key=True)
    doi_fk = db.Column(db.ForeignKey('publication.doi'), primary_key=True)

    def to_dict(self):
        return {
            'venueid': self.venueId,
            'doi_fk': self.doi_FK,
        }


class keys(db.Model):
    __tablename__ = "keys"
    key_ = db.Column(db.String)
    id = db.Column(db.Integer, nullable=False, primary_key=True)

    def to_dict(self):
        return {
            'key_': self.key_,
            'id': self.id,
        }


class venue(db.Model):
    __tablename__ = "venue"
    id = db.Column(db.Integer, primary_key=True)
    publisher = db.Column(db.String, nullable=True)

    def to_dict(self):
        return {
            'id': self.id,
            'publisher': self.publisher,
        }


class conference(db.Model):
    __tablename__ = "conference"
    short = db.Column(db.String)
    name = db.Column(db.String)
    doi = db.Column(db.String, )
    id = db.Column(db.Integer, primary_key=True)
    date_start = db.Column(db.DateTime)
    date_end = db.Column(db.DateTime)
    location = db.Column(db.String)

    def to_dict(self):
        return {
            'short': self.short,
            'name': self.name,
            'doi': self.name,
            'id': self.id,
            'date_start': self.date_start,
            'date_end': self.date_end,
            'location': self.lacation,
        }


class iskey(db.Model):
    __tablename__ = "iskey"
    pubid = db.Column(db.ForeignKey('publication.doi'), primary_key=True)
    keyid = db.Column(db.ForeignKey('keys.id'), primary_key=True)

    def to_dict(self):
        return {
            'keyid': self.keyId,
        }


class articlerelation(db.Model):
    __tablename__ = "articlerelation"
    doi_1_fk = db.Column(db.String, primary_key=True)
    doi_2_fk = db.Column(db.String, primary_key=True)
    type = db.Column(db.Integer, primary_key=True)

    def to_dict(self):
        return {
            'doi_1_fk': self.doi_1_fk,
            'doi_2_fk': self.doi_2_fk,
            'type': self.type
        }
