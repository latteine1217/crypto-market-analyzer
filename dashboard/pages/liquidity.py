"""
流動性分析頁面

顯示訂單簿熱力圖和流動性分布
"""
import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
import numpy as np
from data_loader import DataLoader

data_loader = DataLoader()

# 頁面佈局
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("💧 Liquidity Analysis", className="mb-4"),
        ], width=8),
        dbc.Col([
            dbc.Select(
                id='liquidity-symbol-selector',
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

    # 訂單簿快照統計
    dbc.Row(id='orderbook-stats', className="mb-4"),

    # 流動性剖面圖
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Order Book Depth Profile"),
                dbc.CardBody([
                    dcc.Graph(id='liquidity-profile', config={'displayModeBar': True})
                ])
            ])
        ], width=12)
    ], className="mb-4"),

    # 買賣壓力比
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Bid/Ask Pressure"),
                dbc.CardBody([
                    dcc.Graph(id='bid-ask-pressure', config={'displayModeBar': False})
                ])
            ])
        ], width=6),
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Spread Analysis"),
                dbc.CardBody([
                    html.Div(id='spread-analysis')
                ])
            ])
        ], width=6)
    ])
], fluid=True)


@callback(
    Output('orderbook-stats', 'children'),
    [Input('liquidity-symbol-selector', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_orderbook_stats(symbol, n):
    """更新訂單簿統計"""
    df = data_loader.get_orderbook_snapshots('binance', symbol, limit=10)

    if df.empty:
        return [dbc.Col([
            dbc.Alert(
                "⚠️ No order book data available. Please ensure the collector is running with orderbook collection enabled.",
                color="warning"
            )
        ], width=12)]

    # 最新訂單簿
    latest = df.iloc[0]
    bids = latest['bids']
    asks = latest['asks']

    # 計算統計
    total_bid_volume = sum([float(b[1]) for b in bids]) if bids else 0
    total_ask_volume = sum([float(a[1]) for a in asks]) if asks else 0
    best_bid = float(bids[0][0]) if bids else 0
    best_ask = float(asks[0][0]) if asks else 0
    spread = best_ask - best_bid
    spread_pct = (spread / best_bid * 100) if best_bid > 0 else 0

    cards = [
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Order Book Snapshots", className="text-muted mb-2"),
                    html.H4(f"{len(df)}", className="mb-0")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Best Bid / Ask", className="text-muted mb-2"),
                    html.H5(f"${best_bid:,.2f} / ${best_ask:,.2f}", className="mb-0")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Spread", className="text-muted mb-2"),
                    html.H5(f"${spread:.2f} ({spread_pct:.4f}%)", className="mb-0")
                ])
            ])
        ], width=3),
        dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H6("Total Volume (Bid/Ask)", className="text-muted mb-2"),
                    html.H5(f"{total_bid_volume:.2f} / {total_ask_volume:.2f}", className="mb-0")
                ])
            ])
        ], width=3),
    ]

    return cards


@callback(
    Output('liquidity-profile', 'figure'),
    [Input('liquidity-symbol-selector', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_liquidity_profile(symbol, n):
    """更新流動性剖面圖"""
    df = data_loader.get_orderbook_snapshots('binance', symbol, limit=10)

    if df.empty:
        return go.Figure().add_annotation(
            text="No order book data available",
            showarrow=False,
            font=dict(size=20, color="gray")
        )

    # 聚合所有訂單簿數據
    all_bids = []
    all_asks = []

    for _, row in df.iterrows():
        for price, volume in row['bids']:
            all_bids.append({'price': float(price), 'volume': float(volume)})
        for price, volume in row['asks']:
            all_asks.append({'price': float(price), 'volume': float(volume)})

    bids_df = pd.DataFrame(all_bids)
    asks_df = pd.DataFrame(all_asks)

    if bids_df.empty and asks_df.empty:
        return go.Figure().add_annotation(
            text="No order book data to display",
            showarrow=False
        )

    # 按價格聚合
    if not bids_df.empty:
        bids_agg = bids_df.groupby('price')['volume'].sum().reset_index()
        bids_agg = bids_agg.sort_values('price', ascending=False)
    else:
        bids_agg = pd.DataFrame(columns=['price', 'volume'])

    if not asks_df.empty:
        asks_agg = asks_df.groupby('price')['volume'].sum().reset_index()
        asks_agg = asks_agg.sort_values('price')
    else:
        asks_agg = pd.DataFrame(columns=['price', 'volume'])

    # 建立圖表
    fig = go.Figure()

    # Bids (買單) - 綠色
    if not bids_agg.empty:
        fig.add_trace(go.Bar(
            x=bids_agg['price'],
            y=bids_agg['volume'],
            name='Bids',
            marker_color='rgba(38, 166, 154, 0.7)',
            orientation='v'
        ))

    # Asks (賣單) - 紅色
    if not asks_agg.empty:
        fig.add_trace(go.Bar(
            x=asks_agg['price'],
            y=asks_agg['volume'],
            name='Asks',
            marker_color='rgba(239, 83, 80, 0.7)',
            orientation='v'
        ))

    fig.update_layout(
        template='plotly_dark',
        height=400,
        xaxis_title='Price',
        yaxis_title='Cumulative Volume',
        hovermode='x unified',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        barmode='overlay',
        margin=dict(l=50, r=50, t=40, b=50)
    )

    fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(255,255,255,0.1)')

    return fig


@callback(
    Output('bid-ask-pressure', 'figure'),
    [Input('liquidity-symbol-selector', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_bid_ask_pressure(symbol, n):
    """更新買賣壓力圖"""
    df = data_loader.get_orderbook_snapshots('binance', symbol, limit=50)

    if df.empty:
        return go.Figure().add_annotation(
            text="No data",
            showarrow=False,
            font=dict(size=16, color="gray")
        )

    # 計算每個快照的買賣壓力
    timestamps = []
    bid_pressures = []
    ask_pressures = []

    for _, row in df.iterrows():
        timestamps.append(row['timestamp'])
        bid_vol = sum([float(b[1]) for b in row['bids']])
        ask_vol = sum([float(a[1]) for a in row['asks']])
        bid_pressures.append(bid_vol)
        ask_pressures.append(ask_vol)

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=bid_pressures,
        mode='lines+markers',
        name='Bid Pressure',
        line=dict(color='#26a69a', width=2),
        fill='tozeroy'
    ))

    fig.add_trace(go.Scatter(
        x=timestamps,
        y=ask_pressures,
        mode='lines+markers',
        name='Ask Pressure',
        line=dict(color='#ef5350', width=2),
        fill='tozeroy'
    ))

    fig.update_layout(
        template='plotly_dark',
        height=300,
        xaxis_title='Time',
        yaxis_title='Volume',
        showlegend=True,
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1
        ),
        margin=dict(l=50, r=50, t=20, b=50)
    )

    return fig


@callback(
    Output('spread-analysis', 'children'),
    [Input('liquidity-symbol-selector', 'value'),
     Input('interval-component', 'n_intervals')]
)
def update_spread_analysis(symbol, n):
    """更新 Spread 分析"""
    df = data_loader.get_orderbook_snapshots('binance', symbol, limit=50)

    if df.empty:
        return html.P("No data available", className="text-muted")

    spreads = []
    for _, row in df.iterrows():
        if row['bids'] and row['asks']:
            best_bid = float(row['bids'][0][0])
            best_ask = float(row['asks'][0][0])
            spread = best_ask - best_bid
            spread_pct = (spread / best_bid * 100) if best_bid > 0 else 0
            spreads.append(spread_pct)

    if not spreads:
        return html.P("No spread data", className="text-muted")

    avg_spread = np.mean(spreads)
    min_spread = np.min(spreads)
    max_spread = np.max(spreads)

    stats = [
        ("Average Spread", f"{avg_spread:.4f}%"),
        ("Min Spread", f"{min_spread:.4f}%"),
        ("Max Spread", f"{max_spread:.4f}%"),
        ("Samples", f"{len(spreads)}"),
    ]

    rows = []
    for label, value in stats:
        row = dbc.Row([
            dbc.Col(html.Strong(label), width=6),
            dbc.Col(html.Span(value, className="text-info"), width=6),
        ], className="mb-2 pb-2 border-bottom")
        rows.append(row)

    return rows
