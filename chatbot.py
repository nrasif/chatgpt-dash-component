from dash import Dash, html, dcc, Input, Output, dash_table, callback, State
from dash.exceptions import PreventUpdate

import dash_mantine_components as dmc
from dash_iconify import DashIconify

import pandas as pd

from pandasai import SmartDataframe
from pandasai.llm import OpenAI


openai_api_key = OPEN_AI_API_KEY
llm = OpenAI(api_token=openai_api_key)

data = pd.read_csv("./aceh_production_data_daily_ed.csv")
calculations = [["original", "Original"], ["GOR", "GOR"]]


def generate_data_multiselect(values):
    return [{"label": value, "value": value} for value in values]


app = Dash(
    __name__,
    suppress_callback_exceptions=True,
    meta_tags=[{"name": "viewport", "content": "width=device-width, initial-scale=1"}],
)

app.title = "Aceh Block Information (Dummy)"
app.layout = html.Section(
    [
        dcc.Store(id="memory-output"),
        html.Div(
            className="filter_div",
            children=[
                dmc.MultiSelect(
                    id="well-multiselect",
                    label="Select Well",
                    placeholder="Select Well",
                    data=generate_data_multiselect(
                        data["WELL_BORE_CODE"].unique().tolist()
                    ),
                    value=data["WELL_BORE_CODE"].unique().tolist(),
                ),
                dmc.RadioGroup(
                    [dmc.Radio(i, value=k) for k, i in calculations],
                    id="radio-calculation",
                    label="Select Calculation",
                    size="sm",
                    mt=10,
                    value="Original",
                ),
            ],
        ),
        html.Div(
            className="result_div",
            children=[
                dash_table.DataTable(
                    id="memory-table",
                    columns=[
                        {"name": i, "id": i} for i in data.columns
                    ],  # Add the new columns
                    data=data.to_dict("records"),  # Initialize with all data
                )
            ],
        ),
        html.Div(
            className="chat-gpt",
            children=[
                dmc.Card(
                    children=[
                        html.Br(),
                        dmc.Textarea(
                            id='PromptArea',
                            placeholder='Write your prompt...',
                            style={'width':800},
                            autosize=True,
                            minRows=2,
                            maxRows=4
                        ),
                    
                        dmc.Button('Send Prompt', variant='outline', id='SendButton'),
                        html.Br(),
                        
                        dmc.Text(id='OutputHuman', children=''),
                        dmc.Text(id='OutputChatbot', children='')
                    ],
                    withBorder=True,
                    shadow="sm",
                    radius="md",
                    style={"width": 1000}
                )
            ]
        )
    ])

@callback(
    [Output("memory-output", "data"), Output("memory-table", "columns")],
    [Input("well-multiselect", "value"), Input("radio-calculation", "value")],
)
def filter_well(well_selected, calculation_selected):
    if calculation_selected == "GOR":
        data["WATER_CUT_DAILY"] = (
            data["BORE_WAT_VOL"]
            / (data["BORE_OIL_VOL"] + data["BORE_GAS_VOL"] + data["BORE_WAT_VOL"])
        ) * 100
        data["GAS_OIL_RATIO"] = data["BORE_GAS_VOL"] / data["BORE_OIL_VOL"]
        data_selected = data[data["WELL_BORE_CODE"].isin(well_selected)]

        pivot = data_selected.pivot_table(
            values=["WATER_CUT_DAILY", "GAS_OIL_RATIO"],
            index=data_selected["DATEPRD"],
            aggfunc="mean",
            dropna=True,
        )

        pivot_data = pivot.reset_index().to_dict("records")

        columns = [
            {"name": "DATEPRD", "id": "DATEPRD"},
            {"name": "WATER_CUT_DAILY", "id": "WATER_CUT_DAILY"},
            {"name": "GAS_OIL_RATIO", "id": "GAS_OIL_RATIO"},
        ]

        return pivot_data, columns

    filtered = data[data["WELL_BORE_CODE"].isin(well_selected)]
    filtered_data = filtered.to_dict("records")

    original_columns = [
        {"name": i, "id": i}
        for i in data.columns
        if i not in ["WATER_CUT_DAILY", "GAS_OIL_RATIO"]
    ]

    return filtered_data, original_columns


@callback(Output("memory-table", "data"), Input("memory-output", "data"))
def table_dataset(dataset):
    if dataset is None:
        raise PreventUpdate

    return dataset

@callback(
    Output('OutputHuman', 'children'),
    Output('OutputChatbot', 'children'),
    Input('SendButton','n_clicks'),
    State('PromptArea','value'),
    Input('memory-output','data')
)

def call_openaiAPI(n, human_prompt, data_chosen):
    if n is None and data_chosen is not None:
        return None,None

    else:
        call_API = SmartDataframe(data_chosen, config={'llm':llm, 'conversation':True})
        chatbot_resp = call_API.chat(human_prompt)
        
        human_output =  f"Human : {human_prompt}"
        chatbot_output = f"Zara : {chatbot_resp}"
        
        return human_output, chatbot_output

if __name__ == "__main__":
    app.run_server(debug=True, port=8100)

