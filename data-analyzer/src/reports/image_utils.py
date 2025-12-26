"""
Image Utilities - 圖片處理工具

職責：
1. 將圖片轉換為 base64 編碼
2. 嵌入圖片到 HTML
3. 優化圖片大小
"""
from typing import Optional
from pathlib import Path
import base64
from loguru import logger


def image_to_base64(image_path: Path) -> Optional[str]:
    """
    將圖片轉換為 base64 編碼

    Args:
        image_path: 圖片路徑

    Returns:
        base64 編碼字串，失敗返回 None
    """
    try:
        with open(image_path, 'rb') as f:
            image_data = f.read()
            base64_data = base64.b64encode(image_data).decode('utf-8')

        # 判斷圖片格式
        suffix = image_path.suffix.lower()
        if suffix == '.png':
            mime_type = 'image/png'
        elif suffix in ['.jpg', '.jpeg']:
            mime_type = 'image/jpeg'
        elif suffix == '.gif':
            mime_type = 'image/gif'
        elif suffix == '.svg':
            mime_type = 'image/svg+xml'
        else:
            mime_type = 'image/png'  # 預設

        return f"data:{mime_type};base64,{base64_data}"

    except Exception as e:
        logger.error(f"圖片轉換失敗：{image_path}，錯誤：{e}")
        return None


def create_embedded_image_html(
    image_path: Path,
    alt_text: str = "",
    width: Optional[str] = None,
    css_class: str = ""
) -> str:
    """
    創建嵌入式圖片的 HTML

    Args:
        image_path: 圖片路徑
        alt_text: 替代文字
        width: 寬度（如 '100%', '500px'）
        css_class: CSS 類別

    Returns:
        HTML 字串
    """
    base64_data = image_to_base64(image_path)

    if not base64_data:
        return f'<p class="error">圖片載入失敗：{image_path.name}</p>'

    style = f'width: {width};' if width else ''
    class_attr = f'class="{css_class}"' if css_class else ''

    return f'<img src="{base64_data}" alt="{alt_text}" style="{style}" {class_attr}>'


def collect_backtest_images(strategy_dir: Path) -> dict:
    """
    收集回測結果的所有圖片

    Args:
        strategy_dir: 策略目錄

    Returns:
        圖片字典 {image_type: base64_data}
    """
    images = {}

    # 定義圖片類型與檔案名模式
    image_patterns = {
        'equity_curve': ['equity_curve.png', 'equity.png'],
        'drawdown': ['drawdown.png'],
        'signals': ['signals.png', 'signal.png'],
        'metrics': ['metrics.png', 'performance.png'],
    }

    for image_type, patterns in image_patterns.items():
        for pattern in patterns:
            image_files = list(strategy_dir.glob(f"*{pattern}"))
            if image_files:
                base64_data = image_to_base64(image_files[0])
                if base64_data:
                    images[image_type] = base64_data
                    logger.debug(f"✓ 載入圖片：{image_type} from {image_files[0].name}")
                break

    return images


# 範例用法
if __name__ == "__main__":
    from pathlib import Path

    # 測試圖片轉換
    test_image = Path("results/backtest_reports/RSI/RSI_equity_curve.png")

    if test_image.exists():
        base64_str = image_to_base64(test_image)
        if base64_str:
            print(f"✓ 圖片轉換成功，base64 長度：{len(base64_str)}")

            # 生成 HTML
            html = create_embedded_image_html(
                test_image,
                alt_text="Equity Curve",
                width="100%"
            )
            print(f"✓ HTML 生成成功，長度：{len(html)}")
    else:
        print(f"❌ 測試圖片不存在：{test_image}")
