"""
Reports Module - 報表生成模組

提供統一的報表生成功能，整合資料品質、回測結果與模型結果
"""
from .report_agent import ReportAgent
from .data_collector import ReportDataCollector
from .html_generator import HTMLReportGenerator
from .pdf_generator import PDFReportGenerator

__all__ = [
    'ReportAgent',
    'ReportDataCollector',
    'HTMLReportGenerator',
    'PDFReportGenerator',
]

__version__ = '1.0.0'
