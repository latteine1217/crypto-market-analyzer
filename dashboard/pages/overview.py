"""
首頁 - 市場概覽

顯示所有交易對的實時價格和關鍵指標
"""
import dash
from dash import html, dcc, callback, Input, Output
import dash_bootstrap_components as dbc
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from data_loader import DataLoader

# 初始化資料載入器
data_loader = DataLoader()

# 頁面佈局
layout = dbc.Container([
    dbc.Row([
        dbc.Col([
            html.H2("📈 Market Overview", className="mb-4"),
            html.P("Real-time cryptocurrency market data", className="text-muted")
        ])
    ]),

    # 市場統計卡片
    dbc.Row(id='market-cards', className="mb-4"),

    # 主要圖表區
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Price Charts"),
                dbc.CardBody([
                    dcc.Graph(id='overview-price-chart', config={'displayModeBar': False})
                ])
            ])
        ], width=12)
    ], className="mb-4"),

    # 技術指標摘要
    dbc.Row([
        dbc.Col([
            dbc.Card([
                dbc.CardHeader("Technical Indicators Summary"),
                dbc.CardBody([
                    html.Div(id='technical-summary')
                ])
            ])
        ], width=12)
    ])
], fluid=True)


@callback(
    Output('market-cards', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_market_cards(n):
    """更新市場統計卡片"""
    cards = []

    # 取得市場資料
    markets = [
        ('binance', 'BTC/USDT'),
        ('binance', 'ETH/USDT'),
        ('binance', 'ETH/BTC'),
    ]

    for exchange, symbol in markets:
        try:
            summary = data_loader.get_market_summary(exchange, symbol)

            if not summary:
                continue

            # 價格變化顏色
            change_color = "success" if summary['change_24h'] >= 0 else "danger"
            change_icon = "↑" if summary['change_24h'] >= 0 else "↓"

            card = dbc.Col([
                dbc.Card([
                    dbc.CardBody([
                        html.H5(f"{symbol}", className="card-title"),
                        html.P(exchange.upper(), className="text-muted small"),
                        html.H3(f"${summary['latest_price']:,.2f}", className="mb-2"),
                        html.P([
                            html.Span(
                                f"{change_icon} {abs(summary['change_24h']):.2f}%",
                                className=f"text-{change_color} fw-bold"
                            ),
                            html.Small(" 24h", className="text-muted ms-2")
                        ]),
                        html.Hr(),
                        html.Div([
                            html.Small("24h High: ", className="text-muted"),
                            html.Span(f"${summary['high_24h']:,.2f}", className="fw-bold"),
                        ], className="mb-1"),
                        html.Div([
                            html.Small("24h Low: ", className="text-muted"),
                            html.Span(f"${summary['low_24h']:,.2f}", className="fw-bold"),
                        ], className="mb-1"),
                        html.Div([
                            html.Small("Volume: ", className="text-muted"),
                            html.Span(f"{summary['volume_24h']:,.0f}", className="fw-bold"),
                        ])
                    ])
                ], className="h-100")
            ], width=12, md=6, lg=4, className="mb-3")

            cards.append(card)

        except Exception as e:
            print(f"Error loading {exchange} {symbol}: {e}")
            continue

    return cards


@callback(
    Output('overview-price-chart', 'figure'),
    Input('interval-component', 'n_intervals')
)
def update_price_chart(n):
    """更新價格圖表"""
    fig = make_subplots(
        rows=2, cols=2,
        subplot_titles=('BTC/USDT', 'ETH/USDT', 'ETH/BTC', 'Volume'),
        specs=[[{'type': 'scatter'}, {'type': 'scatter'}],
               [{'type': 'scatter'}, {'type': 'bar'}]],
        vertical_spacing=0.12,
        horizontal_spacing=0.1
    )

    markets = [
        ('binance', 'BTC/USDT', 1, 1),
        ('binance', 'ETH/USDT', 1, 2),
        ('binance', 'ETH/BTC', 2, 1),
    ]

    for exchange, symbol, row, col in markets:
        try:
            df = data_loader.get_ohlcv_data(exchange, symbol, limit=100)

            if df.empty:
                continue

            # 價格線
            fig.add_trace(
                go.Scatter(
                    x=df['timestamp'],
                    y=df['close'],
                    mode='lines',
                    name=symbol,
                    line=dict(width=2),
                    showlegend=False
                ),
                row=row, col=col
            )

        except Exception as e:
            print(f"Error plotting {symbol}: {e}")

    # 成交量
    try:
        df_vol = data_loader.get_ohlcv_data('binance', 'BTC/USDT', limit=100)
        if not df_vol.empty:
            fig.add_trace(
                go.Bar(
                    x=df_vol['timestamp'],
                    y=df_vol['volume'],
                    name='Volume',
                    marker_color='rgba(100, 150, 250, 0.5)',
                    showlegend=False
                ),
                row=2, col=2
            )
    except:
        pass

    fig.update_layout(
        height=600,
        template='plotly_dark',
        showlegend=False,
        margin=dict(l=40, r=40, t=60, b=40)
    )

    fig.update_xaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(255,255,255,0.1)')
    fig.update_yaxes(showgrid=True, gridwidth=0.5, gridcolor='rgba(255,255,255,0.1)')

    return fig


@callback(
    Output('technical-summary', 'children'),
    Input('interval-component', 'n_intervals')
)
def update_technical_summary(n):
    """更新技術指標摘要"""
    rows = []

    markets = [
        ('binance', 'BTC/USDT'),
        ('binance', 'ETH/USDT'),
        ('binance', 'ETH/BTC'),
    ]

    for exchange, symbol in markets:
        try:
            summary = data_loader.get_market_summary(exchange, symbol)

            if not summary:
                continue

            # MACD 狀態
            macd_status = "🔴 Bearish"
            if summary['macd'] and summary['macd_signal']:
                if summary['macd'] > summary['macd_signal']:
                    macd_status = "🟢 Bullish"

            # MA 趨勢
            ma_trend = "Neutral"
            if summary['ma_20'] and summary['latest_price']:
                if summary['latest_price'] > summary['ma_20']:
                    ma_trend = "🟢 Uptrend"
                else:
                    ma_trend = "🔴 Downtrend"

            # 最新信號
            latest_signal_text = "No signal"
            if summary['latest_signals']:
                for strategy, info in summary['latest_signals'].items():
                    signal_map = {1: "🟢 BUY", -1: "🔴 SELL", 0: "⚪ EXIT"}
                    latest_signal_text = f"{strategy}: {signal_map.get(info['signal'], 'HOLD')}"
                    break

            row = dbc.Row([
                dbc.Col(html.Strong(f"{symbol}"), width=2),
                dbc.Col(html.Span(f"MACD: {macd_status}"), width=3),
                dbc.Col(html.Span(f"Trend: {ma_trend}"), width=3),
                dbc.Col(html.Span(latest_signal_text), width=4),
            ], className="mb-2 pb-2 border-bottom")

            rows.append(row)

        except Exception as e:
            print(f"Error in technical summary for {symbol}: {e}")

    return rows if rows else html.P("No data available", className="text-muted")
