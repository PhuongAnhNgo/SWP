import math, re, os, gzip, glob, pandas as pd, json, s2, time, requests
from Database import Database

from io import StringIO
from csv import writer 
from typing import Optional, List
from msgspec import Struct
from msgspec.json import decode

REGEX_HTMLTAG = re.compile("(<([^>]+)>)|\\r|\\n|\\t|\\b|\\u2218|\\u2019")
REGEX_MULTIPLE_WHITESPACES = re.compile('\s{2,}') 
REGEX_ORCID= re.compile('^(\d{4}-){3}\d{3}(\d|X)$')
REGEX_AFTER_BACKSHLASH = re.compile(r"\s+")
REGEX_LATEX = re.compile('(\$+)(?:(?!\1)[\s\S])*\1') # within $$ ... $$

DB = './crossref.db'

pd.set_option('display.max_rows', None)

pd.options.mode.chained_assignment = None  # default='warn'

def find_files_in_folder(folder, extension):
    return glob.glob(folder + '/*.'+extension)

# # set DB Settings
# with Database(DB) as db:
#     db.execute('VACUUM')

# with Database(DB) as db:
#     db.execute('PRAGMA auto_vacuum = FULL')
#     db.execute('PRAGMA journal_mode = wal')
#     db.execute('PRAGMA synchronous = normal')
#     db.execute('PRAGMA foreign_keys = off')

def get_tupleList_from_df(df):
    return list(df.itertuples(index=False, name=None))

def get_doi_from_dxdoi_url(self):
    doi_split = self._urlToDxDOI.split("dx.doi.org/")
    if len(doi_split) > 1:
        return doi_split[1]

def get_orcid_from_orcid_url(orcid_url):
    split = orcid_url.split("orcid.org/")
    if len(split) > 1:
        if REGEX_ORCID.fullmatch(split[1]) is not None:
            return split[1]
        else:
            return 'missing'
    else:
        return 'missing'

def get_date_from_date_parts(date_parts):
    if len(date_parts[0]) == 3:
        return str(date_parts[0][0])+'-'+f'{(date_parts[0][1]):02}'+'-'+f'{(date_parts[0][2]):02}'
    elif len(date_parts[0]) == 2:
        return  str(date_parts[0][0])+'-'+f'{(date_parts[0][1]):02}'+'-00'
    elif len(date_parts[0]) == 1:
        return str(date_parts[0][0])+'-00'+'-00'

def kebap(name: str) -> str:
    import re
    return re.sub(r'_', '-', name)

def crossref_jsons_2_own_json():

    class Url(Struct):
        URL: Optional[str] = 'missing'

    class Primary(Struct):
        primary: Optional[Url] = 'missing'

    class Date(Struct, rename=kebap):
        date_parts: Optional[list[list[int]]] = 'missing'

    class Conference(Struct, rename=kebap):
        name: Optional[str] = 'missing'
        theme: Optional[str] = 'missing'
        location: Optional[str] = 'missing'
        acronym: Optional[str] = 'missing'
        number: Optional[str] = 'missing'
        start: Optional[Date] = 'missing'
        end: Optional[Date] = 'missing'

    class Reference(Struct, rename=kebap):
        DOI: Optional[str] = 'missing'
        first_page: Optional[str] = 'missing'
        key: Optional[str] = 'missing'

    class ISSN_TYP(Struct):
        type: Optional[str] = 'missing'
        value: Optional[str] = 'missing'

    class Author(Struct):
        ORCID: Optional[str] = 'missing'
        given: Optional[str] = 'missing'
        family: Optional[str] = 'missing'

    class item(Struct, rename=kebap):
        URL: Optional[str] = 'missing'
        title: Optional[list[str]] = 'missing'
        abstract: Optional[str] = 'missing'
        ISSN: Optional[list[str]] = 'missing'
        issn_type: Optional[list[ISSN_TYP]] = 'missing'
        container_title: Optional[list[str]] = 'missing'
        issue: Optional[str] = 'missing'
        volume: Optional[str] = 'missing'
        publisher: Optional[str] = 'missing'
        author: Optional[list[Author]] = 'missing'
        DOI: Optional[str] = 'missing'
        type: Optional[str] = 'missing'
        page: Optional[str] = 'missing'
        subject: Optional[list[str]] = 'missing'
        reference: Optional[list[Reference]] = 'missing'
        published: Optional[Date] = 'missing'
        event: Optional[Conference] = 'missing'
        resource: Optional[Primary] = 'missing'

    class bla(Struct):
       items: list[item]   

    PATH_TO_CROSSREF_JSONS = './input/crossref/April 2022 Public Data File from Crossref/data/'

    files_to_parse = find_files_in_folder(PATH_TO_CROSSREF_JSONS,'gz')
    with Database(DB) as db:
        doi_whitelist = {doi[0] for doi in db.query('SELECT doi FROM doi_whitelist')}
    for file in files_to_parse:
        filename = os.path.basename(file)
        with gzip.open(file, 'rb') as f:
            data = decode(f.read(), type=bla)
            blubb = [
                    {
                        'crossref_json': filename,
                        'doi':record.DOI, 
                        'title':re.sub(REGEX_HTMLTAG, '', re.sub(REGEX_MULTIPLE_WHITESPACES, '',  record.title[0])) if record.title != 'missing' else 'missing', 
                        'abstract':re.sub(REGEX_HTMLTAG, '', re.sub(REGEX_MULTIPLE_WHITESPACES, '',   re.sub(REGEX_LATEX, '', record.abstract))) if record.abstract != 'missing' else 'missing', 
                        'issue': record.issue, 
                        'volume': record.volume, 
                        'pages': record.page, 
                        'type':record.type,
                        'url': record.resource.primary.URL if (record.resource != 'missing' and record.resource.primary != 'missing') else 'missing',
                        'published_date': get_date_from_date_parts(record.published.date_parts) if record.published != 'missing' and record.published.date_parts != 'missing' else '0000-00-00',
                        'authors': [
                            {
                                'orcid': get_orcid_from_orcid_url(author.ORCID), 
                                'given': author.given, 
                                'family': author.family, 
                                'name': author.given+' '+author.family
                            } for author in record.author if record.author!='missing'
                        ],
                        'references': [
                            {
                                'doi': reference.DOI, 
                                'first_page': reference.first_page, 
                                'key': reference.key
                            } for reference in record.reference if record.reference!='missing'
                        ],
                        'keywords': [keyword for keyword in record.subject if record.subject!='missing'],
                        'journal': {
                                'issn_defined': [{issn.type : issn.value} for issn in record.issn_type if record.issn_type!= 'missing'], 
                                'issn_undefined':[issn for issn in record.ISSN if record.ISSN != 'missing'] ,
                                'title': record.container_title[0], 
                                'publisher': record.publisher
                            },
                        'conference': {
                            'name': record.event.name if record.event != 'missing' else 'missing',
                            'theme': record.event.theme if record.event != 'missing' else 'missing',
                            'location': record.event.location if record.event != 'missing' else 'missing',
                            'acronym': record.event.acronym if record.event != 'missing' else 'missing',
                            'start': get_date_from_date_parts(record.event.start.date_parts) if record.event != 'missing' and record.event.start != 'missing' and record.event.start.date_parts != 'missing' else '0000-00-00',
                            'end': get_date_from_date_parts(record.event.end.date_parts) if record.event != 'missing' and record.event.end != 'missing' and record.event.end.date_parts != 'missing' else '0000-00-00' 
                        }
                    }
                for record in data.items if record.DOI in doi_whitelist]
            f.close()
            print(file+' done') 
        with open('./output/crossref/parsed_jsons_neu/raw/'+filename+'_parsed.json', 'w') as f:
            json.dump(blubb, f)
            f.close()
             
    # merge jsons
    infiles = find_files_in_folder('./output/crossref/parsed_jsons_neu/raw/','json') 

    number_of_files = len(infiles)
    NUMBER_OF_JSONS_PER_ZIP = 200 #merge 200 jsons into one file (fewer i/o in further proceeding) 

    number_of_runs = math.ceil(number_of_files/NUMBER_OF_JSONS_PER_ZIP)

    for k in range(1,number_of_runs+1):
        last_index = k * NUMBER_OF_JSONS_PER_ZIP -1
        last_index_last = last_index if last_index < number_of_files else number_of_files - 1
        last_index_first = (k - 1) * NUMBER_OF_JSONS_PER_ZIP
        outfile_json = './output/crossref/parsed_jsons_neu/zipped/combined_json_'+str(k)+'.json'
        with open(outfile_json,'w') as o:
            o.write('[')
            for infile in infiles[last_index_first:last_index]: # loop over all files except the last one
                with open(infile,'r') as i:
                    o.write(i.read().strip() + ',\n')
                    i.close()
            with open(infiles[last_index_last]) as i: # special treatement for last file
                o.write(i.read().strip() + ']\n')
                i.close()
            o.close()
        outfile_gz = './output/crossref/parsed_jsons_neu/zipped/combined_json_'+str(k)+'.json.gz'
        with open(outfile_json, 'rb') as src, gzip.open(outfile_gz, 'wb') as dst:
            dst.writelines(src)
            src.close()
            dst.close()
            os.remove(outfile_json)
                
    for infile in infiles:
        os.remove(infile) 

def crossref_own_json_to_db():
    # initialize DB
    with Database(DB) as db:
        db.deleteTableData('documents')
        db.deleteTableData('keywords')
        db.deleteTableData('keywords_2_articles')
        db.deleteTableData('references_')
        db.deleteTableData('references_2_articles')
        db.deleteTableData('authors')
        db.deleteTableData('authors_2_articles')
        db.deleteTableData('conferences')
        db.deleteTableData('articles_2_conferences')
        db.deleteTableData('journals')
        db.deleteTableData('articles_2_journals')
    
    #############################################################
    # journals 
    #############################################################
    class journal_(Struct):
        title: str
        publisher: str
        issn_undefined: List[str]
        issn_defined: List[object]

    list_journals_df = []
    #############################################################
    # conferences 
    #############################################################
    class conference_(Struct):
        name: str
        theme: str
        location: str
        acronym: str
        start: str
        end: str
    list_conferences_df = []
    #############################################################
    # references 
    #############################################################
    class reference(Struct):
        doi: str
        first_page: str
        key: str
    list_references_df = []
    #############################################################
    # keywords 
    #############################################################
    list_keywords_df = []
    #############################################################
    # authors 
    #############################################################
    class author(Struct):
        orcid: str
        given: str
        family: str
        name: str
    list_authors_df = []
    #############################################################
    # articles 
    #############################################################
    class article(Struct):
        doi: str
        title: str
        abstract: str
        crossref_json: str
        issue: str
        volume: str
        pages: str
        type: str
        url: str
        journal: journal_
        published_date: str
        keywords: List[str]
        references: List[reference]
        authors: List[author]
        conference: conference_
    list_articles_df = []
    
    article_id = 0
    
    files = find_files_in_folder('./output/crossref/parsed_jsons_neu/zipped/','gz')
    for file in files:
        output_article = StringIO()
        csv_writer_article = writer(output_article)

        output_authors = StringIO()
        csv_writer_authors = writer(output_authors)

        output_keywords = StringIO()
        csv_writer_keywords = writer(output_keywords)

        output_conferences= StringIO()
        csv_writer_conferences = writer(output_conferences)

        output_journals= StringIO()
        csv_writer_journals = writer(output_journals)

        output_references = StringIO()
        csv_writer_references = writer(output_references)

        with gzip.open(file, 'rb') as f:
            data = decode(f.read(), type=List[List[article]]) 
            for row_outer in data:
                for row_inner in row_outer:
                    article_id += 1
                    csv_writer_article.writerow((article_id, row_inner.doi, row_inner.title, row_inner.abstract, row_inner.crossref_json, row_inner.issue, row_inner.volume, row_inner.pages, row_inner.type, row_inner.url, row_inner.published_date))
                    # keywords
                    for keyword in row_inner.keywords:
                        csv_writer_keywords.writerow((article_id, keyword))
                    # references
                    for reference_ in row_inner.references:
                        csv_writer_references.writerow((article_id, reference_.doi, reference_.first_page, reference_.key))
                    # authors
                    for author_ in row_inner.authors:
                        csv_writer_authors.writerow((article_id, author_.orcid, author_.given, author_.family, author_.name))
                    if row_inner.type == 'journal-article':
                        # journals
                        issn_print = 'missing'
                        issn_electronic = 'missing'
                        issn_undefined = 'missing'
                        for issn_defined in row_inner.journal.issn_defined:
                            if 'print' in issn_defined.keys():
                                if issn_defined['print'] != 'missing':
                                    issn_print = issn_defined['print']
                            if 'electronic' in issn_defined.keys():
                                if issn_defined['electronic'] != 'missing':
                                    issn_electronic = issn_defined['electronic']
                        issn_undefined = ','.join(row_inner.journal.issn_undefined)
                        csv_writer_journals.writerow((article_id, row_inner.journal.title, row_inner.journal.publisher, issn_print, issn_electronic, issn_undefined))
                    elif row_inner.type == 'proceedings-article':
                        # conference
                        csv_writer_conferences.writerow((article_id, row_inner.conference.name, row_inner.conference.theme, row_inner.conference.location, row_inner.conference.acronym, row_inner.conference.start, row_inner.conference.end))
        
            # now all buffers have data --> go to beginning of each data and parse to dataframe --> finally append dataframe to list of dataframes

            #############################################################
            # articles 
            #############################################################
            output_article.seek(0)
            df_articles_temp = pd.read_csv(output_article, names=['article_id','doi', 'title','abstract','crossref_file','issue','volume','pages','typ','url','published_date'])
            list_articles_df.append(df_articles_temp)
            #############################################################
            # keywords 
            #############################################################
            output_keywords.seek(0)
            df_keywords_temp = pd.read_csv(output_keywords, names=['article_id','keyword'])
            list_keywords_df.append(df_keywords_temp)
            #############################################################
            # references 
            #############################################################
            output_references.seek(0)
            df_references_temp = pd.read_csv(output_references, names=['article_id','doi','first_page','key'])
            list_references_df.append(df_references_temp)
            #############################################################
            # authors 
            #############################################################
            output_authors.seek(0)
            df_authors_temp = pd.read_csv(output_authors, names=['article_id','orcid','given','family','name'])
            list_authors_df.append(df_authors_temp)
            #############################################################
            # conference 
            #############################################################
            output_conferences.seek(0)
            df_conference_temp = pd.read_csv(output_conferences, names=['article_id','name','theme','location','acronym','start','end'])
            list_conferences_df.append(df_conference_temp)
            #############################################################
            # journal 
            #############################################################
            output_journals.seek(0)
            df_journals_temp = pd.read_csv(output_journals, names=['article_id','title','publisher','issn_print','issn_electronic','issn_undefined'])
            list_journals_df.append(df_journals_temp)

            f.close()
    # concat all dataframes: much more efficient then appending rows in loop...
    #############################################################
    # articles 
    df_articles = pd.concat(list_articles_df)
    with Database(DB) as db:
        db.executemany('INSERT INTO documents (id, doi, title, abstract, crossref_file, issue, volume, pages, typ, url,published_date) VALUES(?,?,?,?,?,?,?,?,?,?,?)', df_articles.to_records(index=False))
    # prepare dataframes for inserting in DB
    #############################################################
    # references 
    # hash for doi and key --> sort by hash --> remove duplicates --> set id for remaining --> merge with df with article 
    ############################################################# 
    df_references = pd.concat(list_references_df)
    df_references_without_article_id = pd.DataFrame()
    df_references_without_article_id = df_references[['doi','key']]
    df_references_without_article_id['hash'] = (df_references_without_article_id['doi']+df_references_without_article_id['key']).apply(hash)
    df_references_without_article_id.sort_values(by=['hash'], inplace=True)
    df_references_without_article_id['reference_id'] = (df_references_without_article_id['hash'] != df_references_without_article_id['hash'].shift(1)).cumsum()
    df_references_without_article_id.drop_duplicates(inplace=True, keep="first")
    df_references_without_article_id = df_references_without_article_id[['doi','key','reference_id']]
    df_references_2_article = pd.merge(df_references, df_references_without_article_id, on=['doi','key'], how="left")
    df_references_2_article = df_references_2_article[['article_id','reference_id','first_page']]
    df_references_2_article.drop_duplicates(inplace=True, keep="first")
    with Database(DB) as db:
        db.executemany('INSERT INTO references_ (doi, key, id) VALUES(?,?,?)', df_references_without_article_id.to_records(index=False))
        db.executemany('INSERT INTO references_2_articles (article_id, reference_id, first_page) VALUES(?,?,?)',df_references_2_article.to_records(index=False))
    #############################################################
    # authors 
    #############################################################
    df_authors = pd.concat(list_authors_df)    
    df_authors_without_article_id = pd.DataFrame()
    df_authors_without_article_id = df_authors[['orcid','given','family','name']]
    df_authors_without_article_id['hash'] = (df_authors_without_article_id['orcid']+df_authors_without_article_id['name']).apply(hash)
    df_authors_without_article_id.sort_values(by=['hash'], inplace=True)

    df_authors_without_article_id['name_equal_but_orcid_differs'] = ((df_authors_without_article_id['orcid'] != df_authors_without_article_id['orcid'].shift(1)) & ((df_authors_without_article_id['orcid'] != 'missing') & (df_authors_without_article_id['orcid'].shift(1) != 'missing'))) & ((df_authors_without_article_id['name'] == df_authors_without_article_id['name'].shift(1)) & (df_authors_without_article_id['name'] != 'missing'))
    df_authors_without_article_id['orcid_equal_but_name_differs'] = ((df_authors_without_article_id['orcid'] == df_authors_without_article_id['orcid'].shift(1)) & (df_authors_without_article_id['orcid'] != 'missing')) & ((df_authors_without_article_id['name'] != df_authors_without_article_id['name'].shift(1)) & ((df_authors_without_article_id['name'] != 'missing') & df_authors_without_article_id['name'].shift(1) != 'missing'))

    print('check authors: number of non equal orcid by equal name: '+str((df_authors_without_article_id['name_equal_but_orcid_differs'] == True).sum()))
    print('check authors: number of non equal name by equal orcid: '+str((df_authors_without_article_id['orcid_equal_but_name_differs'] == True).sum()))

    df_authors_without_article_id['author_id'] = (df_authors_without_article_id['hash'] != df_authors_without_article_id['hash'].shift(1)).cumsum()
    df_authors_without_article_id.drop_duplicates(inplace=True, keep="first")
    df_authors_without_article_id = df_authors_without_article_id[['author_id','orcid','given','family','name']]
    df_authors_2_article = pd.merge(df_authors, df_authors_without_article_id, on=['orcid','name'], how="left")
    df_authors_2_article = df_authors_2_article[['article_id','author_id']]
    df_authors_2_article.drop_duplicates(inplace=True, keep="first")
    with Database(DB) as db:
        db.executemany('INSERT INTO authors (id, orcid, name_given, name_family, name) VALUES(?,?,?,?,?)', df_authors_without_article_id.to_records(index=False))
        db.executemany('INSERT INTO authors_2_articles (article_id, author_id) VALUES(?,?)',df_authors_2_article.to_records(index=False))
    #############################################################
    # keywords 
    # remove duplicates --> sort asc --> set id for remaining --> merge with df with article
    #############################################################
    df_keywords = pd.concat(list_keywords_df)
    df_keywords_without_article_id = pd.DataFrame()
    df_keywords_without_article_id['keyword'] = df_keywords[['keyword']]['keyword'].unique()
    df_keywords_without_article_id.sort_values(by=['keyword'], inplace=True)
    df_keywords_without_article_id['keyword_id'] = df_keywords_without_article_id.reset_index().index + 1
    df_keyword_2_article = pd.merge(df_keywords, df_keywords_without_article_id, on='keyword', how="left")
    df_keyword_2_article = df_keyword_2_article[['article_id','keyword_id']]
    df_keyword_2_article.drop_duplicates(inplace=True, keep="first")
    with Database(DB) as db:
        db.executemany('INSERT INTO keywords (keyword, id) VALUES(?,?)', df_keywords_without_article_id.to_records(index=False))
        db.executemany('INSERT INTO keywords_2_articles (article_id, keyword_id) VALUES(?,?)',df_keyword_2_article.to_records(index=False))
    #############################################################
    # conference 
    # remove duplicates --> sort asc --> set id for remaining --> merge with df with article
    #############################################################
    df_conference = pd.concat(list_conferences_df)
    df_conference_without_article_id = pd.DataFrame()
    df_conference_without_article_id = df_conference[['name','theme','location','acronym','start','end']]
    df_conference_without_article_id.sort_values(by=['name'], inplace=True)
    df_conference_without_article_id['conference_id'] = (df_conference_without_article_id['name'] != df_conference_without_article_id['name'].shift(1)).cumsum()
    df_conference_without_article_id.drop_duplicates(inplace=True, keep="first")
    df_conference_2_article = pd.merge(df_conference, df_conference_without_article_id, on='name', how="left")
    df_conference_2_article = df_conference_2_article[['article_id','conference_id']]
    df_conference_2_article.drop_duplicates(inplace=True, keep="first")
    with Database(DB) as db:
        db.executemany('INSERT INTO conferences (name, theme, location, acronym, start, end,id) VALUES(?,?,?,?,?,?,?)', df_conference_without_article_id.to_records(index=False))
        db.executemany('INSERT INTO articles_2_conferences (article_id, conference_id) VALUES(?,?)',df_conference_2_article.to_records(index=False))
    #############################################################
    # journals 
    # remove duplicates --> sort asc --> set id for remaining --> merge with df with article
    #############################################################
    df_journal = pd.concat(list_journals_df)
    df_journal.drop_duplicates(inplace=True, keep="first")
    df_journal.sort_values(by=['title','publisher','issn_print','issn_electronic'], inplace=True)
    
    df_journal['hash'] = (df_journal['title']+df_journal['publisher']).apply(hash)
    df_journal_without_article_id = pd.DataFrame()
    df_journal_without_article_id = df_journal[['title','publisher','issn_print','issn_electronic','issn_undefined','hash']]
    df_journal_without_article_id.drop_duplicates(inplace=True, keep="first")

    df_journal_without_article_id['issn_complete'] = ((df_journal_without_article_id['issn_print'] != 'missing') & (df_journal_without_article_id['issn_electronic'] != 'missing'))
    df_journal_without_article_id['title_and_publisher_equal'] = (
        (df_journal_without_article_id['title'] != 'missing') & (df_journal_without_article_id['title'].shift(1) != 'missing') & (df_journal_without_article_id['title'] == df_journal_without_article_id['title'].shift(1)) & 
        (df_journal_without_article_id['publisher'] != 'missing') & (df_journal_without_article_id['publisher'].shift(1) != 'missing') & (df_journal_without_article_id['publisher'] == df_journal_without_article_id['publisher'].shift(1))) 
    df_journal_without_article_id = df_journal_without_article_id.loc[df_journal_without_article_id['title_and_publisher_equal'] == False]

    df_journal_without_article_id.drop_duplicates(inplace=True, keep="first")
    df_journal_without_article_id = df_journal_without_article_id.reset_index()
    df_journal_without_article_id = df_journal_without_article_id.rename(columns={"index":"journal_id"})
    df_journal_without_article_id['journal_id'] = df_journal_without_article_id.index + 1

    df_journal_2_article = pd.merge(df_journal, df_journal_without_article_id, on='hash', how="left")
    df_journal_without_article_id = df_journal_without_article_id[['title','publisher','issn_print','issn_electronic','issn_undefined','journal_id']]
    df_journal_2_article = df_journal_2_article[['article_id','journal_id']]
    df_journal_2_article.drop_duplicates(inplace=True, keep="first")
    with Database(DB) as db:
        db.executemany('INSERT INTO journals (title, publisher, issn_print, issn_electronic, issn_undefined, id) VALUES(?,?,?,?,?,?)', df_journal_without_article_id.to_records(index=False))
        db.executemany('INSERT INTO articles_2_journals (article_id, journal_id) VALUES(?,?)',df_journal_2_article.to_records(index=False))


def semantic_scholar_get_abstracts_v1():
    API_KEY = 'OZ3hs3lXKr9UsHYKCG2pK85WRu0ARVRr2QptiN2K'

    with Database(DB) as db:
        query = db.query('SELECT doi FROM documents WHERE doi != ? and abstract = ?', ['missing', 'missing'])

    for article in query:
        doi = article[0]
        try:
            paper = s2.api.get_paper(paperId=doi, api_key=API_KEY)
            if paper.abstract != None and paper.abstract != '':
                abstract = paper.abstract 
                with Database(DB) as db:
                    db.execute('UPDATE documents SET abstract=?, flag_abstractFoundAtSemanticScholar = ? WHERE doi=?',[abstract, 1, doi])
                    print(doi+' abstract found')
            else:
                with Database(DB) as db:
                    db.execute('UPDATE documents SET flag_abstractFoundAtSemanticScholar = ? WHERE doi=?',[0, doi])
                    print(doi+' abstract not found')
        except:
            continue
        
        #time.sleep(1)

def scimago_get_journal_rankings():
    PATH_TO_SCIMAGOJR_RANKING_CSV = 'input/journal_ranking_scimagojr.csv'
    ################################################################################################
    # Download Data: area = 1700 <=>  computer science, different years (year=) are avaiable
    url = 'https://www.scimagojr.com/journalrank.php?area=1700&type=j&order=h&ord=desc&out=xls'
    req = requests.get(url)
    with open(PATH_TO_SCIMAGOJR_RANKING_CSV, 'wb') as f:
        f.write(req.content)

    ################################################################################################
    # csv --> dataframe
    df_online = pd.read_csv(PATH_TO_SCIMAGOJR_RANKING_CSV, sep = ';', usecols = ['Title','Issn','SJR','H index'])
    
    ######################################
    # clean: column Issn - remove whitespaces, title - remove leading, trailing whitespaces
    df_online['Issn'] = df_online['Issn'].str.replace(" ","")
    df_online['Title'] = df_online['Title'].str.strip()
    ################################################################################################
    # get local journals
    with Database(DB) as db:
        result = db.query('SELECT id as journalId, title, (REPLACE(issn_electronic,"-","") || "," || REPLACE(issn_print,"-","")) as issns FROM journals')
    df_local = pd.DataFrame.from_records(data=result, columns=['journalId','Title','issn_local'])
    ######################################
    # clean: column title - remove leading, trailing whitespaces
    df_local['Title'] = df_local['Title'].str.strip()
    ################################################################################################
    # merge on title
    df_merged = pd.merge(df_local, df_online, on=['Title'], how='left').dropna()
    ######################################
    # validate merge with issn
    def check_issns(row):
        issn_local_list  = row['issn_local'].split()
        issn_online_list = row['Issn'].split()
        return set(issn_local_list).isdisjoint(issn_online_list)
    df_merged['issn_match'] = df_merged.apply(lambda x: check_issns(x), axis=1)
    # select only rows, where issn match is true and only columns needed for updating journalId in db
    df_final = df_merged[df_merged['issn_match'] == True][['SJR','H index','journalId']]

    ################################################################################################
    # update journal id in db
    list_of_tuples = list(df_final.itertuples(index=False, name=None))
    with Database(DB) as db:
        db.executemany('UPDATE journals SET rating_scimagojr_SJR = ?, rating_scimagojr_HINDEX = ? WHERE id = ?',list_of_tuples)


def researchbite_get_topics():
    import pandas as pd
    from bs4 import BeautifulSoup

    from lxml.html.soupparser import fromstring
    from lxml.etree import tostring
    import lxml.html.soupparser
    from lxml import etree

    PATH_TO_HTML_FILES = './input/researchbite/'

    ######################################################################################################
    # extraction is really a pain. Most of the elements in the downladed htmls are within table data and for some reason not directly accessable with beautifulsoup or other parser
    # thererfore: iterarte over alle td, find relevant td by length an extract data at speicific position; since the information is in different td, a global structure for staring these information is needed
    files = find_files_in_folder(PATH_TO_HTML_FILES,'html')
    hugeList = []
    for file in files:
        #print(file)
        with open(file) as fp:
            soup = BeautifulSoup(fp, "html.parser")
            test = soup.find_all('td',class_ = 'line-content')
            for td in test:
                if td is not None:
                    content = td.contents
                    if content[0] in ['The rank of this journal',] or 'is a' in content[0] or 'as follows' in content[0]: 
                        if len(td.contents) == 13:
                            title = td.contents[0]
                            topics = td.contents[10]  
                            if title != '' and title is not None:  
                                hugeList.append(title.strip().replace(' is a',''))
                            if topics != '' and topics is not None:  
                                hugeList.append(topics.strip())
                        if len(td.contents) == 5:
                            issn = td.contents[2]
                            if issn != '' and issn is not None:
                                if issn != '':
                                    hugeList.append(issn)

    # organize huge list into desired categories (=lists)
    journalTitles = []
    journalTopics = []
    journalIssns = []

    for index, item in enumerate(hugeList):

        if index % 3 == 0:
            journalTitles.append(item)
        if index % 3 == 1:
            journalTopics.append(item)
        if index % 3 == 2:
            journalIssns.append(item)

    # create dataframe 
    df = pd.DataFrame(list(zip(journalTitles, journalTopics,journalIssns)),
                columns =['title', 'topics','issns'])
    df_without_duplicates = df.drop_duplicates(keep='first')

    # get avaiable journals 
    with Database(DB) as db:
        result = db.query('SELECT id, title, (REPLACE(issn_electronic,"-","") || "," || REPLACE(issn_print,"-","")) as issns FROM journals')
    df_local = pd.DataFrame.from_records(data=result, columns=['journalId','title','issn_local'])

    # merge these journals with the journals from researchbite by title
    df_merged = pd.merge(df_without_duplicates, df_local, on=['title'], how='left').dropna()

    # cast journal id to int
    df_merged['journalId'] = df_merged['journalId'].astype(int)



    df_final = df_merged[['topics','journalId']]

    # sind there are multiple values in a column, a split at ',' is needed
    df_final['topics1'] = df_final['topics'].str.split(',')
    df = df_final.explode('topics1').reset_index(drop=True)
    cols = list(df.columns)
    cols.append(cols.pop(cols.index('topics1')))
    df = df[cols]

    df1 = df[df['topics1'] != ' etc']
    # df1['topics1'] = df1['topics1']

    topics = df[df['topics1'] != ' etc']['topics1'].unique()

    topicList = []
    for topic in topics:
        topic1 = topic.strip()
        if topic1 not in topicList:
            topicList.append((topic1,))

    unique_topics = [t for t in (set(tuple(i) for i in topicList))]
    df2 = df1[['journalId','topics1']]
    #strip all whitespaces!!!!!!!!!!!!!!!
    df2 = df2.applymap(lambda x: x.strip() if isinstance(x, str) else x)

    # topicList ready for insert in DB 
    with Database(DB) as db:
        db.deleteTableData('journal_topics')
        db.executemany('INSERT INTO journal_topics (topic) VALUES(?)',unique_topics)

    # now every topic has an id and can be merged 
    with Database(DB) as db:
        query_topics = db.query('SELECT id, topic FROM journal_topics')
        df_topics = pd.DataFrame.from_records(data=query_topics, columns=['topicId1','topics1'])
        df_merged3 = pd.merge(df2, df_topics, on=['topics1'], how='left')
        
    df_final = df_merged3[['journalId','topicId1']]
    list_with_tuples = get_tupleList_from_df(df_final)
    with Database(DB) as db:
        db.deleteTableData('topics_2_journals')
        db.executemany('INSERT INTO topics_2_journals (article_id,topic_id) VALUES(?,?) ',list_with_tuples)

#researchbite_get_topics()
#scimago_get_journal_rankings()
#semantic_scholar_get_abstracts_v1()
#crossref_jsons_2_own_json()
#crossref_own_json_to_db()
