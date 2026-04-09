import os
import requests
from bs4 import BeautifulSoup
import time
import re

# 配置区域
html_file = "艾尔海森语音 - 原神WIKI_BWIKI_哔哩哔哩.html"  # 你上传的文件名
save_dir = "haisen_dataset"
os.makedirs(save_dir, exist_ok=True)

# 标注文件路径
list_file_path = os.path.join(save_dir, "haisen_annotation.list")

# 读取本地HTML
with open(html_file, 'r', encoding='utf-8') as f:
    content = f.read()

soup = BeautifulSoup(content, 'html.parser')

# BWiki的音频通常在带有 data-src 的 div.default-audio 中
# 我们先找到所有的行 tr
rows = soup.find_all('tr')
count = 0

print(f"开始解析本地文件: {html_file}...")

with open(list_file_path, "w", encoding="utf-8") as list_file:
    for row in rows:
        tds = row.find_all('td')
        # 索引 0 是播放器列，索引 5 或 -1 是文本列
        if len(tds) >= 2:
            # 1. 抓取音频 (你已经改对索引了，用 tds[0])
            audio_tag = tds[0].find(attrs={"data-src": True})
            if audio_tag:
                audio_url = audio_tag['data-src']
                if audio_url.startswith('//'):
                    audio_url = 'https:' + audio_url
                
                # 2. 抓取中文文本 (核心修改点)
                # 最后一列 tds[-1] 里包含多个语言的 div
                # 我们寻找那个只包含中文内容的 div
                text_td = tds[-1]
                
                # 策略：BWiki 默认中文文本通常在第一个 visible-md 类的 div 里
                # 或者直接找第一个 div
                target_div = text_td.find('div', class_='visible-md visible-sm visible-lg')
                target_div = target_div or text_td.find('voice_text_chs vt_active')  # 如果没有找到特定类的 div，就找第一个 div 
                if target_div:
                    clean_text = target_div.get_text(strip=True)
                else:
                    # 备选方案：如果没有 div，直接取 td 的文本
                    clean_text = text_td.get_text(strip=True)

                # 排除掉那些切换按钮本身的文本 (比如 "中 日 英 韩")
                if clean_text in ["中", "日", "英", "韩"] or len(clean_text) <= 1:
                    # 如果抓到的是控制按钮，尝试找同级下一个 div
                    all_divs = text_td.find_all('div')
                    for d in all_divs:
                        t = d.get_text(strip=True)
                        if t and t not in ["中", "日", "英", "韩"]:
                            clean_text = t
                            break

                # 3. 保存和写入
                file_name = f"haisen_{count:03d}.mp3"
                file_path = os.path.join(save_dir, file_name)
                
                print(f"下载 [{count+1}]: {clean_text[:20]}...")
                
                try:
                    r = requests.get(audio_url, timeout=10)
                    with open(file_path, 'wb') as f_audio:
                        f_audio.write(r.content)
                    
                    # 写入标注
                    list_file.write(f"./{save_dir}/{file_name}|haisen|ZH|{clean_text}\n")
                    count += 1
                except Exception as e:
                    print(f"下载失败: {e}")

print(f"\n✅ 处理完成！")
print(f"共计成功下载 {count} 条语音。")
print(f"标注文件已生成: {list_file_path}")