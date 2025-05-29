import requests
import json
import logging
import os

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def fetch_api_data():
    """从API获取数据"""
    url = "https://www.drhorton.com/coveo/rest/search/v2"
    
    # 设置请求头
    headers = {
        "Accept": "application/json, text/plain, */*",
        "Accept-Language": "en-US,en;q=0.9",
        "Content-Type": "application/json",
        "Origin": "https://www.drhorton.com",
        "Referer": "https://www.drhorton.com/florida",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
    }

    # 设置请求体
    payload = {
        "actionsHistory": [],
        "referrer": "https://www.drhorton.com/florida",
        "analytics": {
            "clientId": "d5e8ca30-409c-0df0-07e8-d3f83de1c009",
            "documentLocation": "https://www.drhorton.com/florida",
            "documentReferrer": "https://www.drhorton.com/florida",
            "pageId": ""
        },
        "visitorId": "d5e8ca30-409c-0df0-07e8-d3f83de1c009",
        "isGuestUser": False,
        "aq": "(@fz95xtemplatename67549==\"Community Landing\") (@fid67549<>\"\") ($qf(function:'dist(@fcoordinatesz32xlatitude67549, @fcoordinatesz32xlongitude67549, 27.90688, -84.07391)', fieldName: 'distance')) (@distance<450000)",
        "cq": "(@source==\"Coveo_web_index - 93DrHortonProd\") (@fcoordinatesz32xlatitude67549) (@fz95xlanguage67549==en) (@fz95xlatestversion67549==1)",
        "queryFunctions": [],
        "numberOfResults": 5000,
        "fieldsToInclude": [
            "@fcommunitythumbnail67549",
            "@factivationstate67549",
            "@factivationstatehez120x67549",
            "@faddress167549",
            "@famenitylist67549",
            "@famenitylistfordisplay67549",
            "@fbrand67549",
            "@fbrandlogo67549",
            "@fbrandlogoalt67549",
            "@fcallforprice67549",
            "@fcity67549",
            "fcoordinatesz32xlatitude67549",
            "@fcoordinatesz32xlongitude67549",
            "@fid67549",
            "@fismultigen67549",
            "@fmarketingname67549",
            "@fnumberofavailablehomes67549",
            "@fnumberofbathroomsmaz120x67549",
            "@fnumberofbathroomsmin67549",
            "@fnumberofbedroomsmaz120x67549",
            "@fnumberofbedroomsmin67549",
            "@fnumberofgaragesmaz120x67549",
            "@fnumberofgaragesmin67549",
            "@fnumberofstoriesmaz120x67549",
            "@fnumberofstoriesmin67549",
            "@fpricemin67549",
            "@flongprice67549",
            "@fpropertytype67549",
            "fsqftmaz120x67549",
            "@fsqftmin67549",
            "@fstate67549",
            "@fsysuri67549",
            "@furllink67549",
            "@fz122xip67549",
            "@fsalesofficephone67549",
            "fnumberofbathroomsmin67549",
            "@source",
            "@collection",
            "@urihash"
        ],
        "pipeline": "allresults",
        "searchHub": "Florida",
        "term": ""
    }
    
    try:
        # 发送POST请求
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()  # 检查响应状态
        
        # 解析JSON响应
        data = response.json()
        
        # 提取链接
        links = []
        if 'results' in data:
            for result in data['results']:
                if 'raw' in result:
                    # 查找furllink67549字段
                    url_link = result['raw'].get('furllink67549')
                    if url_link:
                        full_url = f"https://www.drhorton.com{url_link}"
                        links.append(full_url)
                        logger.info(f"Found Florida link: {full_url}")
        
        # 去重
        unique_links = list(set(links))
        
        # 保存结果到JSON文件
        os.makedirs('data/drhorton', exist_ok=True)
        output_file = 'data/drhorton/florida_links.json'
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(unique_links, f, indent=2, ensure_ascii=False)
        
        logger.info(f"已提取 {len(unique_links)} 个Florida链接并保存到 {output_file}")
        
        return unique_links
        
    except requests.exceptions.RequestException as e:
        logger.error(f"API请求失败: {str(e)}")
        return []
    except json.JSONDecodeError as e:
        logger.error(f"JSON解析失败: {str(e)}")
        return []
    except Exception as e:
        logger.error(f"发生未知错误: {str(e)}")
        return []

def main():
    """主函数"""
    try:
        # 获取并处理API数据
        links = fetch_api_data()
        
        if links:
            logger.info("成功获取Florida链接列表")
            logger.info(f"总共获取到 {len(links)} 个Florida链接")
        else:
            logger.warning("未能获取到任何Florida链接")
        
    except Exception as e:
        logger.error(f"主程序执行错误: {str(e)}")

if __name__ == "__main__":
    main() 