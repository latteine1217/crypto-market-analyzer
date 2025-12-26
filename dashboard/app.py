"""
Crypto Market Analyzer Dashboard

多頁面 Dash 應用：
1. 首頁 - 市場概覽
2. 技術分析 - K線圖 + 技術指標
3. 交易信號 - 策略信號展示
4. 流動性分析 - 訂單簿熱力圖
"""
import dash
from dash import Dash, html, dcc
import dash_bootstrap_components as dbc
from loguru import logger

# 初始化 Dash 應用
app = Dash(
    __name__,
    external_stylesheets=[dbc.themes.DARKLY],  # 使用深色主題
    suppress_callback_exceptions=True,
    title="Crypto Market Analyzer"
)

# 主佈局
app.layout = dbc.Container([
    # 頁首
    dbc.Navbar(
        dbc.Container([
            dbc.Row([
                dbc.Col([
                    html.Div([
                        html.H3("📊 Crypto Market Analyzer", className="text-white mb-0"),
                        html.Small("Real-time Trading Dashboard", className="text-muted")
                    ])
                ], width=8),
                dbc.Col([
                    dbc.Nav([
                        dbc.NavItem(dbc.NavLink("Overview", href="/", active="exact")),
                        dbc.NavItem(dbc.NavLink("Technical", href="/technical", active="exact")),
                        dbc.NavItem(dbc.NavLink("Signals", href="/signals", active="exact")),
                        dbc.NavItem(dbc.NavLink("Liquidity", href="/liquidity", active="exact")),
                    ], pills=True)
                ], width=4, className="d-flex justify-content-end align-items-center")
            ], className="w-100")
        ], fluid=True),
        color="dark",
        dark=True,
        className="mb-4"
    ),

    # 頁面內容
    dcc.Location(id='url', refresh=False),
    html.Div(id='page-content'),

    # 自動刷新
    dcc.Interval(
        id='interval-component',
        interval=60*1000,  # 每 60 秒更新一次
        n_intervals=0
    )
], fluid=True, className="p-4")

# 頁面路由
@app.callback(
    dash.dependencies.Output('page-content', 'children'),
    [dash.dependencies.Input('url', 'pathname')]
)
def display_page(pathname):
    """路由控制"""
    if pathname == '/technical':
        from pages import technical
        return technical.layout
    elif pathname == '/signals':
        from pages import signals
        return signals.layout
    elif pathname == '/liquidity':
        from pages import liquidity
        return liquidity.layout
    else:
        from pages import overview
        return overview.layout


if __name__ == '__main__':
    logger.info("Starting Crypto Market Analyzer Dashboard...")
    logger.info("Access at: http://localhost:8050")
    app.run_server(debug=True, host='0.0.0.0', port=8050)
