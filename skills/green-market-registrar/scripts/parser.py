import os
import re
import sys

# 嘗試安裝 reportlab (如果環境中沒有)
try:
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfgen import canvas
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
    from reportlab.lib.units import cm
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

def parse_raw_data(file_path):
    """解析原始文字資料"""
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    data = {}
    # 使用 Regex 提取資訊
    patterns = {
        'class': r'班級:\s*([^,]+)',
        'id': r'座號:\s*(\d+)',
        'name': r'姓名:\s*([^,]+)',
        'booth': r'攤位名稱:\s*([^,]+)',
        'task': r'分工內容:\s*(.*?)(?=挑戰:|$)',
        'challenge': r'挑戰:\s*(.*?)(?=收穫:|$)',
        'achievement': r'收穫:\s*(.*)'
    }
    
    for key, pattern in patterns.items():
        match = re.search(pattern, content, re.DOTALL)
        data[key] = match.group(1).strip() if match else "N/A"
    
    return data

def check_green_status(task_text, keywords_file):
    """檢查綠色行動關鍵字"""
    with open(keywords_file, 'r', encoding='utf-8') as f:
        keywords = f.read().split(',')
    
    found_keywords = [kw.strip() for kw in keywords if kw.strip() in task_text]
    
    if not found_keywords:
        return "⚠️ 需加強環保意識", []
    elif len(found_keywords) >= 2:
        return "✅ 綠色行動達標", found_keywords
    else:
        return "⚠️ 具備初步環保意識", found_keywords

def generate_pdf(data, status_info, captions, output_path):
    """生成 PDF 報告"""
    if not REPORTLAB_AVAILABLE:
        raise Exception("ReportLab is not installed. Please run 'pip install reportlab'.")

    doc = SimpleDocTemplate(output_path, pagesize=A4)
    styles = getSampleStyleSheet()
    # 注意：ReportLab 預設不支援中文，這裡在練習環境中，我們模擬結構
    # 實際開發需處理中文字型註冊 (如: Heiti)
    
    elements = []
    
    # Title
    elements.append(Paragraph("Green Market Activity Report", styles['Title']))
    elements.append(Spacer(1, 12))
    
    # Booth Info Table
    table_data = [
        ["Field", "Details"],
        ["Class", data['class']],
        ["ID", data['id']],
        ["Name", data['name']],
        ["Booth Name", data['booth']],
        ["Green Status", status_info[0]]
    ]
    
    t = Table(table_data, colWidths=[3*cm, 10*cm])
    t.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('PADDING', (0, 0), (-1, -1), 6),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))
    
    # Task, Challenge, Achievement
    elements.append(Paragraph(f"<b>Task:</b> {data['task']}", styles['Normal']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Challenge:</b> {data['challenge']}", styles['Normal']))
    elements.append(Spacer(1, 10))
    elements.append(Paragraph(f"<b>Achievement:</b> {data['achievement']}", styles['Normal']))
    elements.append(Spacer(1, 20))
    
    # Visuals Section
    elements.append(Paragraph("Visual Narratives (Image Placeholders)", styles['Heading2']))
    for cap in captions:
        elements.append(Paragraph(f"• [Image: {cap}]", styles['Normal']))
        elements.append(Spacer(1, 5))

    doc.build(elements)

def main():
    # 路徑設定 (自動偵測腳本所在目錄的上一層作為根目錄)
    script_dir = os.path.dirname(os.path.abspath(__file__))
    base_dir = os.path.dirname(script_dir)
    ref_dir = os.path.join(base_dir, 'references')
    out_dir = os.path.join(base_dir, 'output')
    
    raw_data_path = os.path.join(ref_dir, 'raw_data.txt')
    keywords_path = os.path.join(ref_dir, 'keywords.txt')
    captions_path = os.path.join(ref_dir, 'image_captions.txt')
    output_pdf = os.path.join(out_dir, 'report.pdf')


    # 1. Parse
    print("[1/4] Parsing raw data...")
    data = parse_raw_data(raw_data_path)
    
    # 2. Check Status
    print("[2/4] Checking green status...")
    status_info = check_green_status(data['task'], keywords_path)
    
    # 3. Load Captions
    print("[3/4] Loading captions...")
    with open(captions_path, 'r', encoding='utf-8') as f:
        captions = f.read().split('\n')
    
    # 4. Generate PDF
    print("[4/4] Generating PDF...")
    try:
        generate_pdf(data, status_info, captions, output_pdf)
        
        # 5. Size Check
        file_size_mb = os.path.getsize(output_pdf) / (1024 * 1024)
        print(f"\n[SUCCESS] Report generated: {output_pdf}")
        print(f"File Size: {file_size_mb:.4f} MB")
        
        if file_size_mb > 4:
            print("[WARNING] PDF size exceeds 4MB limit!")
        else:
            print("[OK] PDF size is within limits.")
            
    except Exception as e:
        print(f"\n[ERROR] Failed to generate PDF: {e}")

if __name__ == "__main__":
    main()
