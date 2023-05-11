from flask import Flask, render_template, request, flash, url_for, redirect, \
    session, g, Blueprint, make_response, current_app

from flask_sqlalchemy import SQLAlchemy
from . import db_models as dbm
from .db_models import publication, db
import json
# from .coAuthorNetwork import fill_network

bp = Blueprint("anetz", __name__)

query = None
currentDoi = None


@bp.route('/', methods=['GET','POST'])
def index():
    if request.method == 'POST':
        if request.form['choice'] == "Author":
            return redirect('/CoAuthorNetwork/')
        elif request.form['choice'] == "ANet":
            return redirect('/ArticleNetwork/')
        elif request.form['choice'] == "Article":
            return redirect(url_for('anetz.Articles'))            
    return render_template('index.html', title='Homepage')

@bp.route('/ANetwork', methods=['GET','POST'])
def ANetwork():
    print("Article Network")
    return render_template('index.html', title='Article network')

@bp.route('/Co_Auth_ANetwork', methods=['GET','POST'])
def Co_Auth_ANetwork():
    print("Co-Author Network")
    return render_template('articleTable.html', title='Co-authorship network')
    # return redirect(url_for('/anetz.ANetwork/'))

@bp.route('/Articles', methods=['GET','POST'])
def Articles():
    global currentDoi
    global query  
    query = dbm.publication.query.limit(700)
    if request.method == 'POST':
        author = request.form['author']
        journal = request.form['journal']
        title = request.form['title']
        publisher = request.form['publisher']
        hvon = request.form['hvon']
        hbis = request.form['hbis']
        sjrvon = request.form['sjrvon']
        sjrbis = request.form['sjrbis']

        #ajax für table buttons
        output = request.get_json(silent=True)
        if output:
            result = json.loads(output) 
            if result[0]=="get_authors":
                currentDoi=result[1]
        query = articles_query(author,journal,title,publisher,hvon,hbis,sjrvon,sjrbis)
        return render_template('articleTable.html', title='Article Search')
    return render_template('articleTable.html', title='Article Search')


@bp.route('/api/data')  
def data():
    global query  

    if query is not None:
        total_filtered = query.count()

        # sorting
        order = []
        i = 0
        while True:
            col_index = request.args.get(f'order[{i}][column]')
            if col_index is None:
                break
            col_name = request.args.get(f'columns[{col_index}][data]')
            descending = request.args.get(f'order[{i}][dir]') == 'desc'
            col = getattr(dbm.publication, col_name)
            if descending:
                col = col.desc()
            order.append(col)
            i += 1
        if order:
            query = query.order_by(*order)

        # pagination
        start = request.args.get('start', type=int)
        length = request.args.get('length', type=int)
        query = query.offset(start).limit(length)
        #print (query)
        # response
        return {
            'data': [dt.to_dict() for dt in query],
            'recordsFiltered': total_filtered,
            'recordsTotal': dbm.publication.query.count(),
            'draw': request.args.get('draw', type=int),
        }
    else:
        return {
            'data': [],
            'recordsFiltered': 0,
            'recordsTotal': 0,
            'draw': request.args.get('draw', type=int),
        }


@bp.route('/api/get_authors')
def get_authors():  
    global currentDoi
    authors=db.session.query(dbm.isauthor.authorid_fk).filter(dbm.isauthor.doi_fk==currentDoi).all()
    authors = [author for a in authors for author in a]
    query = dbm.author.query.filter(dbm.author.id.in_(authors))
    print(query)
    if  query is not None :
        
        total_filtered = query.count()

        # sorting
        order = []
        i = 0
        while True:
            col_index = request.args.get(f'order[{i}][column]')
            if col_index is None:
                break
            col_name = request.args.get(f'columns[{col_index}][data]')
            descending = request.args.get(f'order[{i}][dir]') == 'desc'
            col = getattr(dbm.author, col_name)
            if descending:
                col = col.desc()
            order.append(col)
            i += 1
        if order:
            query = query.order_by(*order)

        # pagination
        start = request.args.get('start', type=int)
        length = request.args.get('length', type=int)
        query = query.offset(start).limit(length)
        #
        # print (query)
        # response
        return {
            'data': [user.to_dict() for user in query],
            'recordsFiltered': total_filtered,
            'recordsTotal': dbm.author.query.count(),
            'draw': request.args.get('draw', type=int),
        }
    else:
        return {
            'data': [],
            'recordsFiltered': 0,
            'recordsTotal': 0,
            'draw': request.args.get('draw', type=int),
        }


def articles_query(author,journal,title,publisher,hvon,hbis,sjrvon,sjrbis): ##publisher in SQL hinzufügen
    global query

    #author queries
    try:
        auth_id=dbm.author.query(dbm.author.id).filter(db.or_(dbm.author.orchid.like(f'%{author}%'),  #select all authors die den ensprechende orchid oder name haben
                                                             dbm.author.name.like(f'%{author}%')))
        auth_doi=db.session.query(dbm.isauthor.doi_fk).filter(dbm.isauthor.authorid_fk.in_(auth_id)).all()[:100]  # select die erste n ergebnisse-dois wo der author id ist in auth_id
        #auth_pub=.all()#[:100]   select die erste n ergebnisse-publikationen wo der doi in doi ist
        #db.session.query(dbm.Publication.doi_FK).filter(dbm.isAuthor.authorId_FK.in_(auth_id))  
    except:
        print("no author results")
        auth_doi=[]   

    auth_doi_lst=[]
    for i in range (len(auth_doi)):
        auth_doi_lst.append(auth_doi[i][0])    


    #journal queries
    if hvon and len(hvon):
        h_index_great=dbm.journal.hIndex >= (f'%{hvon}%')
    else:
        h_index_great=False
    if hbis and len(hbis):
        h_index_less=dbm.journal.hIndex <= (f'%{hvon}%')
    else:
        h_index_less=False

    if sjrvon and len(sjrvon):
        sjr_index_great=dbm.journal.hIndex >= (f'%{sjrvon}%')
    else:
        sjr_index_great=False
    if sjrbis and len(sjrbis):
        sjr_index_less=dbm.journal.hIndex <= (f'%{sjrbis}%')
    else:
        sjr_index_less=False

    try:
        journal_id=dbm.journal.query(dbm.journal.id).filter(db.or_(dbm.journal.title.like(f'%{journal}%'),
                                                            dbm.journal.issne.like(f'%{journal}%'),
                                                            dbm.journal.issnp.like(f'%{journal}%'),
                                                            h_index_less,
                                                            h_index_great,
                                                            sjr_index_less,
                                                            sjr_index_great
                                                            ))
        journal_doi=db.session.query(dbm.pubon.doi_fk).filter(dbm.pubon.venueid.in_(journal_id)).all()[:100]
    except:
        print("no journal results")
        journal_doi=[]   


    journal_doi_lst=[]
    for i in range (len(journal_doi)):
        journal_doi_lst.append(journal_doi[i][0])  


    #conference queries
    try:
        conference_id=dbm.conference.query(dbm.conference.id).filter(db.or_(dbm.conference.name.like(f'%{journal}%'),
                                                            dbm.conference.doi.like(f'%{journal}%')
                                                            ))
        conference_doi=db.session.query(dbm.pubon.doi_fk).filter(dbm.pubon.venueid.in_(conference_id)).all()[:100]
    except:
        print("no journal results")
        conference_doi=[]


    conference_doi_lst=[]
    for i in range (len(conference_doi)):
        conference_doi_lst.append(conference_doi[i][0])  




    query = dbm.publication.query.filter(db.or_(
        dbm.publication.doi.in_(auth_doi_lst),
        dbm.publication.doi.in_(journal_doi_lst),
        dbm.publication.doi.in_(conference_doi_lst),
        dbm.publication.title.like(f'% {title} %'),
    ))