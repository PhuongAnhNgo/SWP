from flask import Flask

from .db_models import db
from .anetz import *
from .PWS import SQL

from .CoAuthorNetwork import create_co_author_network_dash_app
from .ArticleNetwork import create_article_network_dash_app

def create_app():
    """Create and configure an instance of the Flask application."""

    app = Flask(__name__, instance_relative_config=True)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = 'mssql+pyodbc://'+ SQL()[2]+':'+ SQL()[3]+'@'+ SQL()[0]+'/'+ SQL()[1]+'?driver=ODBC Driver 17 for SQL Server'

    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key= b'\xf3\xf5\xf8\x98' #ZU ÄNDERN!!!!!!!!

    db.init_app(app)

    create_co_author_network_dash_app(app)
    create_article_network_dash_app(app)

    app.register_blueprint(anetz.bp)

    app.add_url_rule("/", endpoint="anetz.index")
    return app
