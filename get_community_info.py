from bs4 import BeautifulSoup
import json
from datetime import datetime

def extract_community_info():
    # 读取HTML文件
    with open('pageLennar.html', 'r', encoding='utf-8') as f:
        html_content = f.read()
    
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # 提取社区信息
    community_info = {
        'timestamp': datetime.now().isoformat(),
        'name': soup.find('h1').text.strip() if soup.find('h1') else None,
        'status': None,
        'price_from': None,
        'address': None,
        'phone': None,
        'description': None
    }
    
    # 提取状态和价格信息
    status_price = soup.find_all('span', class_='bodycopySmallNew')
    for span in status_price:
        text = span.text.strip()
        if 'Actively selling' in text:
            community_info['status'] = 'Actively selling'
        elif 'From the upper' in text:
            community_info['price_from'] = text
    
    # 提取地址
    address_div = soup.find('div', {'data-testid': 'community-address'})
    if address_div:
        community_info['address'] = address_div.text.strip()
    
    # 提取电话号码
    phone_link = soup.find('a', href=lambda x: x and 'tel:' in x)
    if phone_link:
        community_info['phone'] = phone_link.text.strip()
    
    # 提取描述
    description = soup.find('p', class_='bodycopyLargeNew')
    if description:
        community_info['description'] = description.text.strip()
    
    # 保存到JSON文件
    with open('data/community_info.json', 'w', encoding='utf-8') as f:
        json.dump(community_info, f, indent=2, ensure_ascii=False)
    
    print("社区信息已保存到 data/community_info.json")
    return community_info

if __name__ == "__main__":
    info = extract_community_info()
    print("\n提取的社区信息:")
    for key, value in info.items():
        print(f"{key}: {value}")
