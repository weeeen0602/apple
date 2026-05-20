import os
import sys

# 解決 Windows 控制台編碼問題
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def generate_data():
    # 1. 建立測試文字資料 (Raw Text)
    raw_text = """
    班級: 6班, 座號: 15, 姓名: 王小明, 攤位名稱: 綠色再生站
    分工內容: 我們今天負責收集廢棄塑膠瓶，並將其清洗乾淨後，準備製作成盆栽吊飾。
    挑戰: 塑膠瓶清洗的過程非常耗時，且需要大量的水資源，我們必須注意節水。
    收穫: 學會了如何分辨不同類型的塑膠材質，並理解了資源循環的重要性。
    """

    # 2. 建立綠色行動關鍵字 (Keywords)
    keywords = ["回收", "改造", "循環", "租借", "二手", "環保", "再生", "修補", "綠色", "有機", "清洗", "節水"]

    # 3. 建立影像描述清單 (Image Captions)
    image_captions = [
        "學生正在清洗塑膠瓶的特寫畫面",
        "完成後的盆栽吊飾展示圖",
        "小組討論如何分配清洗任務的側拍"
    ]

    # 建立資料夾
    base_dir = 'green-market-registrar/references'
    if not os.path.exists(base_dir):
        os.makedirs(base_dir)
    
    os.makedirs('green-market-registrar/output', exist_ok=True)
    
    # 寫入檔案
    with open(os.path.join(base_dir, 'raw_data.txt'), 'w', encoding='utf-8') as f:
        f.write(raw_text)
    
    with open(os.path.join(base_dir, 'keywords.txt'), 'w', encoding='utf-8') as f:
        f.write(",".join(keywords))
        
    with open(os.path.join(base_dir, 'image_captions.txt'), 'w', encoding='utf-8') as f:
        f.write("\n".join(image_captions))

    print("[SUCCESS] Test data generation completed!")
    print(f"- {base_dir}/raw_data.txt")
    print(f"- {base_dir}/keywords.txt")
    print(f"- {base_dir}/image_captions.txt")

if __name__ == "__main__":
    generate_data()
