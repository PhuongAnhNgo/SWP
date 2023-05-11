import copy

import networkx as nx

from .db_models import author, isauthor, articlerelation, publication

# article network
import dash
import dash_cytoscape as cyto
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State

relation_type_to_name = {
    0: "quotes",
    1: "subclass",
    2: "applies",
    3: "extends",
    4: "generalizes",
    5: "implements",
    6: "improves",
    7: "mentions",
    8: "specializes",
    9: "tests",
    10: "theorizes"
}
legend_text = "\n\n\nArticle relationship types:\n\n"
legend_text += f'{"blank":>5}: quotes\n'
for t, t_name in relation_type_to_name.items():
    if t == 0:
        continue
    legend_text += f'{t:>5}: {t_name}\n'

article_network = nx.Graph()
preset_positions = {}
aid_to_name = {}
doi_to_info = {}
dash_app = None
nodes = []
edges = []

def create_article_network_dash_app(flask_app):
    global dash_app
    global edges
    global nodes

    dash_app = dash.Dash(__name__, server=flask_app, url_base_pathname="/ArticleNetwork/")
    cyto.load_extra_layouts()

    styles = {
        'pre': {
            # 'border': 'thin lightgrey solid',
            'width': '80%',
            'height': '500px',
            "overflow": "scroll"
        },
        'legend':{
            'width': '10%',
            'height': '500px'
        }
    }

    default_stylesheet = [
        {
            'selector': 'node',
            'style': {
                'background-color': '#BFD7B5',
                'label': 'data(name)'
            }
        },
        {
            'selector': 'edge',
            'style': {
                'source-arrow-shape': 'triangle',
                'curve-style': 'bezier',
                'label': 'data(types)'
            }
        },
        {
            'selector': '.chosen',
            'style': {
                'background-color': '#BFD7B5',
                'line-color': '#BFD7B5',
            }
        },
        {
            'selector': '.chosen_edge',
            'style': {
                'width': 6,
                'source-arrow-color': '#BFD7B5'
            }
        },
        {
            'selector': '.chosen_node',
            'style': {
                'height': 30,
                'width': 30
            }
        },
        {
            'selector': '.not_chosen',
            'style': {
                'background-color': 'lightgrey',
                'line-color': 'lightgrey',
                'source-arrow-color': 'lightgrey'
            }
        },
        {
            'selector': '.not_chosen_edge',
            'style': {
                'width': 2
            }
        },
        {
            'selector': '.not_chosen_node',
            'style': {
                'height': 20,
                'width': 20
            }
        },
    ]

    dash_app.layout = html.Div([
        html.Div([
            html.Div([
                html.Div(dcc.Input(id='input_doi_anet', type='text')),
                html.Div(id='submit_doi_anet_button_text', children='Enter a doi')
            ], style={'padding': 4, 'flex': 0}),
            html.Div([
                html.Div(dcc.Input(id='input_search_depth_anet', type='text')),
                html.Div(id='submit_search_depth_button_text_anet', children='search-depth')
            ], style={'padding': 4, 'flex': 0})
        ], style={'display': 'flex', 'flex-direction': 'row', 'textAlign': 'center'}),
        html.Div([
            html.Button('Submit', id='submit_doi_anet', n_clicks=0)
        ]),
        html.Div([
            html.Div([
                html.Pre(id='legend_anet', style=styles['legend'], children=legend_text),
            ]),
            html.Div([
                dcc.Dropdown(
                    id='layout_drpd_anet',
                    value='cose',
                    clearable=False,
                    options=[
                        {'label': name.capitalize(), 'value': name}
                        for name in ['preset', 'klay', 'spread', 'cose']  # 'breadthfirst' is not supported
                    ]
                ),
                cyto.Cytoscape(
                    id='article_net',
                    layout={'name': 'cose', "fit": False, 'directed': True},
                    elements=[],
                    stylesheet=default_stylesheet,
                    style={'height': '450px'},
                    maxZoom=1,
                    minZoom=0.2,
                )
            ], style={'padding': 10, 'flex': 1}),
            html.Div([
                html.Pre(id='output_text_anet', style=styles['pre']),
                # html.Div(dcc.Input(id='input_orcid', type='text')),
                # html.Button('Submit', id='submit_orcid', n_clicks=0),
                # html.Div(id='submit_orcid_button_text', children='Enter a orcID.')
            ], style={'padding': 10, 'flex': 1})
        ], style={'display': 'flex', 'flex-direction': 'row'})
    ])

    @dash_app.callback(
        [Output('output_text_anet', 'children'), Output('article_net', 'elements'), Output('article_net', 'layout')],
        [Input('article_net', 'tapNodeData'), Input('article_net', 'tapEdgeData'), Input('layout_drpd_anet', 'value'),
         Input('submit_doi_anet', 'n_clicks'), State('input_doi_anet', 'value'),
         State('input_search_depth_anet', 'value'), State('output_text_anet', 'children'),
         State('article_net', 'elements')],  # , Input('submit_orcid', 'n_clicks'), State('input_orcid', 'value')],
        prevent_initial_call=True
    )
    def callback(node_data, edge_data, layout_name, _, input_doi, input_search_depth, cur_output_text, elements):  # __, input_orcid):
        global nodes
        global edges

        cbc = dash.callback_context
        layout = {'name': layout_name}
        if layout_name == 'preset':
            layout['fit'] = False
        output_text = cur_output_text

        if cbc.triggered_id == 'article_net':
            if 'article_net.tapNodeData' in cbc.triggered_prop_ids:
                elements, output_text = node_click_event(node_data['id'], elements)
            elif 'article_net.tapEdgeData' in cbc.triggered_prop_ids:
                output_text = edge_click_event(edge_data, elements)
        elif cbc.triggered_id == 'layout_drpd_anet':
            drpd_event(layout_name, layout)
            elements = nodes + edges
        elif cbc.triggered_id == 'submit_doi_anet':
            elements, output_text = submit_doi_event(input_doi, input_search_depth)
        # elif cbc.triggered_id == 'submit_orcid':
        #     elements = submit_event_orcid(input_orcid, input_search_depth)
        return output_text, elements, layout

    def submit_doi_event(doi, search_depth):
        global nodes
        global edges
        global article_network
        global preset_positions
        global aid_to_name
        global doi_to_info

        root_article = publication.query.filter(publication.doi.like(f'%{doi}%')).first()
        if root_article is None:
            return nodes + edges

        nodes = []
        edges = []
        article_network = nx.DiGraph()
        preset_positions = {}
        aid_to_name = {}
        doi_to_info = {doi: {'info': root_article}}
        article_network.add_node(doi)

        isauthor_list = isauthor.query.filter(isauthor.doi_fk.like(f'%{doi}%')).all()
        doi_to_info[doi]['authorids'] = [isauthor_element.authorid_fk for isauthor_element in isauthor_list]
        for isauthor_element in isauthor_list:
            cur_author = author.query.filter(author.id == isauthor_element.authorid_fk).first()
            aid_to_name[isauthor_element.authorid_fk] = {'name': cur_author.name, 'orcid': cur_author.orchid}

        dois = [root_article.doi]
        visited_dois = []
        search_depth = 10000 if search_depth is None else int(search_depth)
        for i in range(search_depth):
            new_dois = []
            while dois:
                cur_doi = dois[0]
                del dois[0]
                article_relations = articlerelation.query.filter(
                    articlerelation.doi_1_fk.like(f'%{cur_doi}%') | articlerelation.doi_2_fk.like(f'%{cur_doi}%')
                )
                for article_relation in article_relations:
                    doi_1, doi_2 = article_relation.doi_1_fk, article_relation.doi_2_fk
                    if doi_1 in visited_dois or doi_2 in visited_dois:
                        continue

                    if article_network.has_edge(doi_1,  doi_2):
                        if article_relation.type != 0:
                            article_network[doi_1][doi_2]['types'].append(article_relation.type)
                    else:
                        article_network.add_edge(doi_1,  doi_2,
                                                 types=[article_relation.type] if article_relation.type != 0 else [])

                    new_doi = None
                    if doi_1 not in doi_to_info:
                        new_doi = doi_1
                    elif doi_2 not in doi_to_info:
                        new_doi = doi_2

                    if new_doi:
                        new_article = publication.query.filter(publication.doi.like(f'%{new_doi}%')).first()
                        new_isauthor_list = isauthor.query.filter(isauthor.doi_fk.like(f'%{new_doi}%')).all()

                        for isauthor_element in new_isauthor_list:
                            if author.id in aid_to_name:
                                continue
                            cur_author = author.query.filter(author.id == isauthor_element.authorid_fk).first()
                            aid_to_name[isauthor_element.authorid_fk] = {'name': cur_author.name,
                                                                         'orcid': cur_author.orchid}

                        doi_to_info[new_doi] = {
                            'info': new_article,
                            'authorids': [isauthor_element.authorid_fk for isauthor_element in new_isauthor_list]
                        }
                        new_dois.append(new_doi)

                visited_dois.append(cur_doi)
            dois = new_dois

        preset_positions = nx.spring_layout(article_network)
        preset_positions = nx.rescale_layout_dict(preset_positions, scale=100)
        copy_pos = copy.deepcopy(preset_positions)
        for cur_doi in article_network.nodes():
            nodes.append({
                'data': {
                    'id': cur_doi
                },
                'position': {
                    'x': copy_pos[cur_doi][0],
                    'y': copy_pos[cur_doi][1],
                }
            })

        for doi_1, doi_2 in article_network.edges():
            edges.append({
                'data': {
                    'id': doi_1 + doi_2,
                    'source': doi_2,  # for some reason source and
                    'target': doi_1,  # target have to be reversed
                    'types': article_network[doi_1][doi_2]['types']
                }
            })

        elements = nodes + edges
        elements, output_text = node_click_event(doi, elements)

        return elements, output_text

    def drpd_event(layout_name, layout):
        if layout_name == 'preset':
            layout['positions'] = {node['data']['id']: node['position'] for node in nodes}

    def node_click_event(doi, elements):
        global aid_to_name
        global doi_to_info

        output_text = create_article_output_text(doi)

        for i_element, element in enumerate(elements):
            if 'source' not in element['data']:
                if element['data']['id'] == doi:
                    element['classes'] = 'chosen chosen_node'
                    elements[i_element] = copy.deepcopy(element)
                else:
                    element['classes'] = 'not_chosen not_chosen_node'
            else:
                if element['data']['source'] == doi or element['data']['target'] == doi:
                    element['classes'] = 'chosen chosen_edge'
                else:
                    element['classes'] = 'not_chosen not_chosen_edge'

        return elements, output_text

    def edge_click_event(edge_data, elements):
        global aid_to_name
        global doi_to_info
        global relation_type_to_name

        types = []
        for element in elements:
            if 'source' not in element['data']:
                element['classes'] = 'not_chosen not_chosen_node'
            else:
                if element['data']['source'] == edge_data['source'] and element['data']['target'] == edge_data['target'] \
                        or element['data']['source'] == edge_data['target'] and element['data']['target'] == edge_data['source']:
                    element['classes'] = 'chosen chosen_edge'
                    types = element['data']['types']
                else:
                    element['classes'] = 'not_chosen not_chosen_edge'

        source_doi = edge_data['target']  # for some reason source and
        target_doi = edge_data['source']  # target are reversed

        output_text = f"Title: {doi_to_info[source_doi]['info'].title}\n" \
                      f"doi:   {source_doi}\n\n"

        for i, t in enumerate(types):
            output_text += relation_type_to_name[t]
            if i < len(types) - 1:
                output_text += ", "
            elif i == len(types) - 2:
                output_text += " and "

        if len(types) == 0:
            output_text += relation_type_to_name[0]  # quote

        output_text += f"\n\nTitle: {doi_to_info[target_doi]['info'].title}\n" \
                       f"doi:   {target_doi}"

        return output_text

def create_article_output_text(doi):
    infos = doi_to_info[doi]['info']
    output_text = f'Authors:'
    for author_id in doi_to_info[doi]['authorids']:
        output_text += f'\n\tname: {aid_to_name[int(author_id)]["name"]}\n\torcid: {aid_to_name[int(author_id)]["orcid"]}\n'
    output_text += f'\ndoi:\n\t{doi}' \
                   f'\nTitle:\n\t{infos.title}' \
                   f'\nYear:\n\t{infos.year}' \
                   f'\nVolume:\n\t{infos.volume}' \
                   f'\nIssue:\n\t{infos.issue}' \
                   f'\nPages:\n\t{infos.pages}' \
                   f'\nNumber:\n\t{infos.number}' \
                   f'\nurl:\n\t{infos.url}' \
                   f'\nAbstract:\n\n{infos.abstract}\n' \
                   f'\ntype:\n\t{infos.type}'
    return output_text