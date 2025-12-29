"""
交易信號頁面

顯示各策略的交易信號和統計
"""
import dash
from dash import html, dcc, callback, Input, Output
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
            html.H2("🎯 Trading Signals", className="mb-4"),
        ], width=8),
        dbc.Col([
            dbc.Select(
                id='signals-symbol-selector',
                options=[
                    {'label': 'BTC/USDT', 'value': 'BTC/USDT'},
                    {'label': 'ETH/USDT', 'value': 'ETH/USDT'},
                    {'label': 'ETH/BTC', 'value': 'ETH/BTC'},
                ],
                value='ETH/USDT',
                className="mb-3"
            )
        ], width=4)
    ]),

    # 信號統計卡片
    dbc.Row(id='signal-stats-cards', className="mb-4"),

    # 信號圖表
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Trading Signals Timeline"),
                dbc.CardBody([
                    dcc.Graph(id='signals-chart', config={'displayModeBar': True})
                ])
            ])
        ], width=12)
    ], className="mb-4"),

    # 信號詳細列表
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Recent Signals"),
                dbc.CardBody([
                    html.Div(id='signals-table')
                ])
            ])
        ], width=12)
    ])
], fluid=True)


@callback(
    Output('signal-stats-cards', 'children'),
    [Input('signals-symbol-selector', 'value'),
     Input('interval-fast', 'n_intervals')]  # 使用快速刷新
)
def update_signal_stats(symbol, n):
    """更新信號統計卡片"""
    signals_dict = data_loader.get_strategy_signals('binance', symbol)

    if not signals_dict:
        return [dbc.Col([
            dbc.Alert("No signal data available", color="warning")
        ], width=12)]

    cards = []

    for strategy_name, signals in signals_dict.items():
        # 計算統計
        buy_count = (signals == 1).sum()
        sell_count = (signals == -1).sum()
        total_signals = buy_count + sell_count

        # 最新信號
        non_none = signals[signals.notna()]
        if not non_none.empty:
            latest_signal = int(non_none.iloc[-1])
            signal_map = {1: ("BUY", "success"), -1: ("SELL", "danger"), 0: ("EXIT", "warning")}
            signal_text, signal_color = signal_map.get(latest_signal, ("HOLD", "secondary"))
        else:
            signal_text, signal_color = "NO SIGNAL", "secondary"

        card = dbc.Col([
            dbc.Card([
                dbc.CardBody([
                    html.H5(strategy_name, className="card-title"),
                    html.Hr(),
                    html.Div([
                        dbc.Badge(signal_text, color=signal_color, className="mb-3", pill=True)
                    ]),
                    html.Div([
                        html.Small("Total Signals: ", className="text-muted"),
                        html.Span(f"{total_signals}", className="fw-bold"),
                    ], className="mb-2"),
                    html.Div([
                        html.Span(f"🟢 Buy: {buy_count}", className="me-3"),
                        html.Span(f"🔴 Sell: {sell_count}"),
                    ], className="small"),
                ])
            ], className="h-100")
        ], width=12, md=6, lg=4, className="mb-3")

        cards.append(card)

    return cards


@callback(
    Output('signals-chart', 'figure'),
    [Input('signals-symbol-selector', 'value'),
     Input('interval-fast', 'n_intervals')]  # 使用快速刷新
)
def update_signals_chart(symbol, n):
    """更新信號圖表"""
    df = data_loader.get_ohlcv_with_indicators('binance', symbol, limit=200)
    signals_dict = data_loader.get_strategy_signals('binance', symbol)

    if df.empty or not signals_dict:
        return go.Figure().add_annotation(
            text="No data available",
            showarrow=False,
            font=dict(size=20, color="gray")
        )

    # 建立子圖
    n_strategies = len(signals_dict)
    fig = make_subplots(
        rows=n_strategies + 1, cols=1,
        row_heights=[0.5] + [0.5/n_strategies] * n_strategies,
        subplot_titles=(['Price'] + list(signals_dict.keys())),
        vertical_spacing=0.05
    )

    # 價格線
    fig.add_trace(go.Scatter(
        x=df['timestamp'],
        y=df['close'],
        mode='lines',
        name='Price',
        line=dict(color='#2196F3', width=2)
    ), row=1, col=1)

    # 各策略信號
    row_idx = 2
    for strategy_name, signals in signals_dict.items():
        # 買入信號
        buy_signals = signals[signals == 1]
        if not buy_signals.empty:
            buy_prices = df.loc[buy_signals.index, 'close'] if not df.empty else []
            fig.add_trace(go.Scatter(
                x=buy_signals.index,
                y=buy_prices,
                mode='markers',
                name=f'{strategy_name} BUY',
                marker=dict(
                    symbol='triangle-up',
                    size=12,
                    color='#26a69a',
                    line=dict(width=1, color='white')
                ),
                showlegend=False
            ), row=1, col=1)

        # 賣出信號
        sell_signals = signals[signals == -1]
        if not sell_signals.empty:
            sell_prices = df.loc[sell_signals.index, 'close'] if not df.empty else []
            fig.add_trace(go.Scatter(
                x=sell_signals.index,
                y=sell_prices,
                mode='markers',
                name=f'{strategy_name} SELL',
                marker=dict(
                    symbol='triangle-down',
                    size=12,
                    color='#ef5350',
                    line=dict(width=1, color='white')
                ),
                showlegend=False
            ), row=1, col=1)

        # 信號時間軸
        signal_values = signals.replace({1: 1, -1: -1}).fillna(0)
        colors = ['#26a69a' if x > 0 else '#ef5350' if x < 0 else 'gray' for x in signal_values]

        fig.add_trace(go.Bar(
            x=df['timestamp'],
            y=signal_values,
            name=strategy_name,
            marker_color=colors,
            showlegend=False
        ), row=row_idx, col=1)

        fig.update_yaxes(range=[-1.5, 1.5], row=row_idx, col=1)

        row_idx += 1

    fig.update_layout(
        template='plotly_dark',
        height=400 + n_strategies * 100,
        showlegend=False,
        margin=dict(l=50, r=50, t=60, b=40),
        hovermode='x unified'
    )

    fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(255,255,255,0.1)')

    return fig


@callback(
    Output('signals-table', 'children'),
    [Input('signals-symbol-selector', 'value'),
     Input('interval-fast', 'n_intervals')]  # 使用快速刷新
)
def update_signals_table(symbol, n):
    """更新信號列表"""
    signals_dict = data_loader.get_strategy_signals('binance', symbol)

    if not signals_dict:
        return html.P("No signals available", className="text-muted")

    all_signals = []

    for strategy_name, signals in signals_dict.items():
        non_none = signals[signals.notna()]

        for idx, value in non_none.tail(10).items():
            signal_map = {1: ("BUY", "success"), -1: ("SELL", "danger"), 0: ("EXIT", "warning")}
            signal_text, signal_color = signal_map.get(int(value), ("HOLD", "secondary"))

            all_signals.append({
                'time': idx,
                'strategy': strategy_name,
                'signal': signal_text,
                'color': signal_color
            })

    # 按時間排序
    all_signals.sort(key=lambda x: x['time'], reverse=True)

    rows = []
    for sig in all_signals[:20]:  # 最多顯示 20 個
        row = dbc.Row([
            dbc.Col(html.Small(str(sig['time'])), width=4),
            dbc.Col(html.Span(sig['strategy']), width=4),
            dbc.Col(
                dbc.Badge(sig['signal'], color=sig['color'], pill=True),
                width=4
            ),
        ], className="mb-2 pb-2 border-bottom")
        rows.append(row)

    return rows if rows else html.P("No recent signals", className="text-muted")
