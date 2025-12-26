"""
技術分析頁面

顯示 K 線圖 + 技術指標（MACD, MA, Williams Fractal）
"""
import dash
from dash import html, dcc, callback, Input, Output, State
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from data_loader import DataLoader

data_loader = DataLoader()

# 頁面佈局
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("📊 Technical Analysis", className="mb-4"),
        ], width=8),
        dbc.Col([
            dbc.Select(
                id='symbol-selector',
                options=[
                    {'label': 'BTC/USDT', 'value': 'BTC/USDT'},
                    {'label': 'ETH/USDT', 'value': 'ETH/USDT'},
                    {'label': 'ETH/BTC', 'value': 'ETH/BTC'},
                ],
                value='BTC/USDT',
                className="mb-3"
            )
        ], width=4)
    ]),

    # K線圖
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Candlestick Chart with Moving Averages & Fractals"),
                dbc.CardBody([
                    dcc.Graph(id='candlestick-chart', config={'displayModeBar': True})
                ])
            ])
        ], width=12)
    ], className="mb-4"),

    # MACD 指標
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("MACD Indicator"),
                dbc.CardBody([
                    dcc.Graph(id='macd-chart', config={'displayModeBar': False})
                ])
            ])
        ], width=12)
    ], className="mb-4"),

    # 技術指標統計
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Technical Indicators Values"),
                dbc.CardBody([
                    html.Div(id='indicator-stats')
                ])
            ])
        ], width=12)
    ])
], fluid=True)


@callback(
    Output('candlestick-chart', 'figure'),
    [Input('symbol-selector', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_candlestick(symbol, n):
    """更新 K 線圖"""
    df = data_loader.get_ohlcv_with_indicators('binance', symbol, limit=200)

    if df.empty:
        return go.Figure().add_annotation(
            text="No data available",
            showarrow=False,
            font=dict(size=20, color="gray")
        )

    # 建立圖表
    fig = go.Figure()

    # K 線圖
    fig.add_trace(go.Candlestick(
        x=df['timestamp'],
        open=df['open'],
        high=df['high'],
        low=df['low'],
        close=df['close'],
        name='Price',
        increasing_line_color='#26a69a',
        decreasing_line_color='#ef5350'
    ))

    # 移動平均線
    if 'ma_20' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['ma_20'],
            mode='lines',
            name='MA 20',
            line=dict(color='#2196F3', width=1)
        ))

    if 'ma_60' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['ma_60'],
            mode='lines',
            name='MA 60',
            line=dict(color='#FF9800', width=1)
        ))

    if 'ma_200' in df.columns:
        fig.add_trace(go.Scatter(
            x=df['timestamp'],
            y=df['ma_200'],
            mode='lines',
            name='MA 200',
            line=dict(color='#F44336', width=1)
        ))

    # 威廉分形標記
    if 'fractal_up' in df.columns:
        fractals_up = df[df['fractal_up']]
        if not fractals_up.empty:
            fig.add_trace(go.Scatter(
                x=fractals_up['timestamp'],
                y=fractals_up['high'],
                mode='markers',
                name='Fractal Up',
                marker=dict(
                    symbol='triangle-down',
                    size=10,
                    color='#26a69a',
                    line=dict(width=1, color='white')
                )
            ))

    if 'fractal_down' in df.columns:
        fractals_down = df[df['fractal_down']]
        if not fractals_down.empty:
            fig.add_trace(go.Scatter(
                x=fractals_down['timestamp'],
                y=fractals_down['low'],
                mode='markers',
                name='Fractal Down',
                marker=dict(
                    symbol='triangle-up',
                    size=10,
                    color='#ef5350',
                    line=dict(width=1, color='white')
                )
            ))

    fig.update_layout(
        template='plotly_dark',
        height=500,
        xaxis_title='Time',
        yaxis_title='Price (USD)',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        xaxis=dict(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='rgba(255,255,255,0.1)'
        ),
        yaxis=dict(
            showgrid=True,
            gridwidth=0.5,
            gridcolor='rgba(255,255,255,0.1)'
        ),
        margin=dict(l=50, r=50, t=40, b=50)
    )

    return fig


@callback(
    Output('macd-chart', 'figure'),
    [Input('symbol-selector', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_macd(symbol, n):
    """更新 MACD 圖表"""
    df = data_loader.get_ohlcv_with_indicators('binance', symbol, limit=200)

    if df.empty or 'macd' not in df.columns:
        return go.Figure().add_annotation(
            text="No MACD data available",
            showarrow=False,
            font=dict(size=16, color="gray")
        )

    fig = make_subplots(
        rows=2, cols=1,
        row_heights=[0.7, 0.3],
        subplot_titles=('MACD', 'Histogram'),
        vertical_spacing=0.1
    )

    # MACD 線和信號線
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['macd'],
        mode='lines',
        name='MACD',
        line=dict(color='#2196F3', width=2)
    ), row=1, col=1)

    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['macd_signal'],
        mode='lines',
        name='Signal',
        line=dict(color='#FF9800', width=2)
    ), row=1, col=1)

    # 柱狀圖
    colors = ['#26a69a' if x >= 0 else '#ef5350' for x in df['macd_histogram']]
    fig.add_trace(go.Bar(
        x=df['timestamp'],
        y=df['macd_histogram'],
        name='Histogram',
        marker_color=colors
    ), row=2, col=1)

    # 零線
    fig.add_hline(y=0, line_dash="dash", line_color="gray", row=1, col=1)

    fig.update_layout(
        template='plotly_dark',
        height=400,
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=60, b=40)
    )

    fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(255,255,255,0.1)')

    return fig


@callback(
    Output('indicator-stats', 'children'),
    [Input('symbol-selector', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_indicator_stats(symbol, n):
    """更新技術指標統計"""
    summary = data_loader.get_market_summary('binance', symbol)

    if not summary:
        return html.P("No data available", className="text-muted")

    stats_data = [
        ("Latest Price", f"${summary['latest_price']:,.2f}", ""),
        ("MACD", f"{summary['macd']:.4f}" if summary['macd'] else "N/A",
         "🟢 Bullish" if summary['macd'] and summary['macd_signal'] and summary['macd'] > summary['macd_signal'] else "🔴 Bearish"),
        ("MACD Signal", f"{summary['macd_signal']:.4f}" if summary['macd_signal'] else "N/A", ""),
        ("MA 20", f"${summary['ma_20']:,.2f}" if summary['ma_20'] else "N/A",
         f"{((summary['latest_price'] / summary['ma_20'] - 1) * 100):+.2f}%" if summary['ma_20'] else ""),
        ("MA 60", f"${summary['ma_60']:,.2f}" if summary['ma_60'] else "N/A",
         f"{((summary['latest_price'] / summary['ma_60'] - 1) * 100):+.2f}%" if summary['ma_60'] else ""),
    ]

    rows = []
    for label, value, extra in stats_data:
        row = dbc.Row([
            dbc.Col(html.Strong(label), width=3),
            dbc.Col(html.Span(value, className="text-info"), width=4),
            dbc.Col(html.Span(extra), width=5),
        ], className="mb-2 pb-2 border-bottom")
        rows.append(row)

    return rows
