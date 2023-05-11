from .db_models import author, isauthor, publication

# co author network
import dash
import dash_cytoscape as cyto
import dash_html_components as html
import dash_core_components as dcc
from dash.dependencies import Input, Output, State
import networkx as nx
import itertools
import copy

dash_app = None
edges = []
nodes = []
aid_to_info = {}
doi_to_info = {}
co_network = nx.Graph()
preset_positions = {}

def create_co_author_network_dash_app(flask_app):
    global dash_app
    global edges
    global nodes

    dash_app = dash.Dash(__name__, server=flask_app, url_base_pathname="/CoAuthorNetwork/")
    cyto.load_extra_layouts()

    styles = {
        'pre': {
            # 'border': 'thin lightgrey solid',
            'width': '70%',
            'height': '500px',
            "overflow": "scroll"
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
            'selector': '.chosen',
            'style': {
                'background-color': '#BFD7B5',
                'line-color': '#BFD7B5',
            }
        },
        {
            'selector': '.chosen_edge',
            'style': {
                'width': 6
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
                html.Div(dcc.Input(id='input_orcid', type='text')),
                html.Div(id='submit_orcid_button_text', children='Enter an orcID')
            ], style={'padding': 2, 'flex': 0}),
            html.Div([
                html.Div(dcc.Input(id='input_search_depth', type='text')),
                html.Div(id='submit_search_depth_button_text', children='search-depth')
            ], style={'padding': 2, 'flex': 0})
        ], style={'display': 'flex', 'flex-direction': 'row', 'textAlign': 'center'}),
        html.Div([
            html.Button('Submit', id='submit_orcid', n_clicks=0)
        ]),
        html.Div([
            html.Div([
                dcc.Dropdown(
                    id='layout_drpd',
                    value='spread',
                    clearable=False,
                    options=[
                        {'label': name.capitalize(), 'value': name}
                        for name in ['preset', 'klay', 'spread', 'cose']  # 'breadthfirst' is also supported
                    ]
                ),
                cyto.Cytoscape(
                    id='co_net',
                    layout={'name': 'spread', "fit": True},
                    elements=[],
                    stylesheet=default_stylesheet,
                    style={'height': '450px'},
                    maxZoom=1,
                    minZoom=0.2,
                )
            ], style={'padding': 10, 'flex': 1}),
            html.Div([
                html.Pre(id='dois', style=styles['pre']),
                html.Div(dcc.Input(id='input_doi', type='text')),
                html.Button('Submit', id='submit_doi', n_clicks=0),
                html.Div(id='submit_doi_button_text', children='Enter a doi.')
            ], style={'padding': 10, 'flex': 1})

        ], style={'display': 'flex', 'flex-direction': 'row'}),
        html.Div([
            html.Iframe(
                src="assets/articleTable.html",
                style={"height": "1067px", "width": "100%"}
            )
        ])
    ])

    @dash_app.callback(
        [Output('dois', 'children'), Output('co_net', 'elements'), Output('co_net', 'layout')],
        [Input('co_net', 'tapNodeData'), Input('co_net', 'tapEdgeData'), Input('layout_drpd', 'value'),
         Input('submit_doi', 'n_clicks'), Input('submit_orcid', 'n_clicks'), State('input_search_depth', 'value'),
         State('input_orcid', 'value'), State('co_net', 'elements'), State('input_doi', 'value')],
        prevent_initial_call=True
    )
    def callback(node_data, edge_data, layout_name, _, __, input_search_depth, input_orcid, elements, input_doi):
        cbc = dash.callback_context
        layout = {'name': layout_name}
        if layout_name == 'preset':
            layout['fit'] = False
        elif layout_name == 'breadthfirst':
            layout['root'] = f'[id = {node_data["id"]}]'
        output_text = ''

        if cbc.triggered_id == 'co_net':
            if 'co_net.tapNodeData' in cbc.triggered_prop_ids:
                output_text = node_click_event(int(node_data['id']), elements)
            elif 'co_net.tapEdgeData' in cbc.triggered_prop_ids:
                output_text = edge_click_event(edge_data, elements)
        elif cbc.triggered_id == 'layout_drpd':
            elements = drpd_event(layout_name, elements, layout)
        elif cbc.triggered_id == 'submit_doi':
            output_text = submit_doi_event(input_doi, elements)
        elif cbc.triggered_id == 'submit_orcid':
            elements, output_text = submit_orcid_event(input_orcid, input_search_depth)
        return output_text, elements, layout

    def submit_orcid_event(orcid, search_depth):
        global nodes
        global edges
        global co_network
        global preset_positions
        global aid_to_info
        global doi_to_info
        root_author = author.query.filter(author.orchid.like(f'%{orcid}%')).first()

        if root_author is None:
            return nodes + edges

        # initialize everything blank
        nodes = []
        edges = []
        co_network = nx.Graph()
        preset_positions = {}
        aid_to_info = {}
        doi_to_info = {}

        isauthor_list = isauthor.query.filter(isauthor.authorid_fk == int(root_author.id)).all()
        aid_to_info[root_author.id] = {}
        aid_to_info[root_author.id]['name'] = root_author.name
        aid_to_info[root_author.id]['orcid'] = root_author.orchid
        aid_to_info[root_author.id]['dois'] = set(isauthor_element.doi_fk for isauthor_element in isauthor_list)

        authors = [root_author]
        search_depth = 10000 if search_depth is None else int(search_depth)
        for i in range(search_depth):
            new_authors = []
            while authors:
                cur_author = authors[0]
                del authors[0]

                for doi in aid_to_info[cur_author.id]['dois']:
                    if doi in doi_to_info:
                        continue
                    current_isauthor_list = isauthor.query.filter(isauthor.doi_fk.like(f'%{doi}%')).all()
                    doi_to_info[doi] = {
                        'authorids': [isauthor_element.authorid_fk for isauthor_element in current_isauthor_list],
                        'infos': publication.query.filter(publication.doi.like(f'%{doi}%')).first()
                    }
                    for isauthor_element in current_isauthor_list:
                        if isauthor_element.authorid_fk in aid_to_info:
                            continue
                        new_author = author.query.filter(author.id == isauthor_element.authorid_fk).first()
                        new_authors.append(new_author)
                        new_isauthor_list = isauthor.query.filter(isauthor.authorid_fk == int(new_author.id)).all()
                        aid_to_info[new_author.id] = {}
                        aid_to_info[new_author.id]['name'] = new_author.name
                        aid_to_info[new_author.id]['orcid'] = new_author.orchid
                        aid_to_info[new_author.id]['dois'] = set(isauthor_element.doi_fk for isauthor_element in
                                                                  new_isauthor_list)
            authors = new_authors

        aid_to_node_pos = {}
        node_pos = 0
        for aid in aid_to_info:
            doi_list = list(aid_to_info[aid]['dois'])
            nodes.append(
                {
                    'data': {
                        'id': aid,
                        'orcid': aid_to_info[aid]['orcid'],
                        'dois': doi_list,
                        'name': aid_to_info[aid]['name']},
                    'position': {'x': None, 'y': None}
                }
            )

            aid_to_node_pos[aid] = node_pos
            node_pos += 1
            co_network.add_node(aid)

            # if not every author of a publication is represented the doi infos are missing
            for doi in doi_list:
                if doi in doi_to_info:
                    continue
                current_isauthor_list = isauthor.query.filter(isauthor.doi_fk.like(f'%{doi}%')).all()
                doi_to_info[doi] = {
                        'authorids': [isauthor_element.authorid_fk for isauthor_element in current_isauthor_list],
                        'infos': publication.query.filter(publication.doi.like(f'%{doi}%')).first()
                    }

        for doi in doi_to_info:
            relevant_author_ids = [aid for aid in doi_to_info[doi]['authorids'] if aid in aid_to_info]
            for aid_1, aid_2 in itertools.combinations(relevant_author_ids, 2):
                common_dois = aid_to_info[aid_1]['dois'].intersection(aid_to_info[aid_2]['dois'])
                edges.append({
                    'data': {'source': aid_1, 'target': aid_2, 'dois': list(common_dois)}
                })
                co_network.add_edge(aid_1, aid_2)

            irrelevant_author_ids = [aid for aid in doi_to_info[doi]['authorids'] if aid not in relevant_author_ids]
            for aid in irrelevant_author_ids:
                if aid in aid_to_info:
                    continue
                irrelevant_author = author.query.filter(author.id == aid).first()
                aid_to_info[aid] = {}
                aid_to_info[aid]['name'] = irrelevant_author.name

        preset_positions = nx.spring_layout(co_network)
        preset_positions = nx.rescale_layout_dict(preset_positions, scale=100)
        copy_pos = copy.deepcopy(preset_positions)
        for aid in aid_to_info:
            nodes[aid_to_node_pos[aid]]['position']['x'] = copy_pos[aid][0]
            nodes[aid_to_node_pos[aid]]['position']['y'] = copy_pos[aid][1]

        elements = nodes + edges
        output_text = node_click_event(root_author.id, elements)

        return elements, output_text

    def submit_doi_event(doi, elements):
        global aid_to_info
        global doi_to_info

        author_ids = []
        for element in elements:
            if doi in element['data']['dois']:
                if 'source' not in element['data']:
                    author_ids.append(element['data']['id'])
                    element['classes'] = 'chosen chosen_node'
                else:
                    element['classes'] = 'chosen chosen_edge'
            else:
                if 'source' not in element['data']:
                    element['classes'] = 'not_chosen not_chosen_node'
                else:
                    element['classes'] = 'not_chosen not_chosen_edge'

        infos = doi_to_info[doi]['infos']
        output_text = f'Authors:'
        for author_id in doi_to_info[doi]['authorids']:
            output_text += f'\n\t{aid_to_info[int(author_id)]["name"]}'
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

    def drpd_event(layout_name, elements, layout):
        if layout_name != 'breadthfirst':
            elements = nodes + edges
            if layout_name == 'preset':
                layout['positions'] = {node['data']['id']: node['position'] for node in nodes}
        return elements

    def edge_click_event(edge_data, elements):
        global aid_to_info
        global doi_to_info

        for element in elements:
            if 'source' not in element['data']:
                element['classes'] = 'not_chosen not_chosen_node'
            else:
                if element['data']['source'] == edge_data['source'] and element['data']['target'] == edge_data['target'] \
                        or element['data']['source'] == edge_data['target'] and element['data']['target'] == edge_data['source']:
                    element['classes'] = 'chosen chosen_edge'
                else:
                    element['classes'] = 'not_chosen not_chosen_edge'
        output_text = f'Authors:\n\t{aid_to_info[int(edge_data["source"])]["name"]}\n\t{aid_to_info[int(edge_data["target"])]["name"]}\n' \
                      f'\nArticles:\n'
        for current_doi in edge_data["dois"]:
            output_text += f'\tdoi:\t{current_doi}\n\tTitle:\t{doi_to_info[current_doi]["infos"].title}\n\n'
        return output_text

    def node_click_event(aid, elements):
        global aid_to_info

        author_name = aid_to_info[aid]["name"]
        output_text = f'Author: {author_name}\n'
        for current_doi in aid_to_info[aid]["dois"]:
            infos = doi_to_info[current_doi]['infos']
            output_text += f'\ndoi:\t{current_doi}' \
                           f'\nTitle:\t{infos.title}\n'

        for i_element, element in enumerate(elements):
            if 'source' not in element['data']:
                if int(element['data']['id']) == aid:
                    element['classes'] = 'chosen chosen_node'
                else:
                    element['classes'] = 'not_chosen not_chosen_node'
            else:
                if int(element['data']['source']) == aid or int(element['data']['target']) == aid:
                    element['classes'] = 'chosen chosen_edge'
                else:
                    element['classes'] = 'not_chosen not_chosen_edge'
        return output_text
