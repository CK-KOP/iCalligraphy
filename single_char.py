import logging
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup

# 配置日志
logging.basicConfig(level=logging.INFO)

async def search_character(char):
    """
    根据指定的字符搜索毛笔字矢量图和信息，返回结果列表。

    参数:
        char (str): 需要搜索的单个字符

    返回值:
        list[dict]: 包含 SVG 内容和相关信息的字典列表
    """
    url = f'http://jimei.shufaziti.com/?char={char}&font=%E5%85%A8%E9%83%A8&size=160&forecolor=%23000000&backcolor=%23ffffff'

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)  # 启动浏览器
        page = await browser.new_page()  # 新建页面
        
        try:
            # 禁用不必要的资源
            await page.route("**/*", lambda route, request: route.abort() 
                             if request.resource_type in ["image", "stylesheet", "font", "media"] else route.continue_())
            
            # 加载目标页面
            logging.info(f"正在搜索字符: {char}")
            await page.goto(url)

            # 等待 SVG 元素渲染并确保可见
            await page.wait_for_selector('svg', state='visible', timeout=30000)  # 等待内容加载

            # 获取页面内容
            html_content = await page.content()
            soup = BeautifulSoup(html_content, 'html.parser')

            # 解析并提取相关信息
            results = []
            for index, dl in enumerate(soup.find_all('dl')):
                svg = dl.find('dt').find('svg')
                dd = dl.find('dd')

                if svg and dd:
                    results.append({
                        "svgContent": str(svg),  # SVG 图形内容
                        "vectorId": str(index + 1),  # 矢量图唯一标识
                        "info": dd.text.strip()  # 相关信息
                    })

            # 输出找到的结果数量
            logging.info(f"共找到 {len(results)} 个结果")
            return results

        except Exception as e:
            logging.error(f"搜索字符 '{char}' 时出错: {e}")
            return []

        finally:
            # 关闭浏览器
            await browser.close()
            logging.info("浏览器已关闭")

# # 示例调用
# async def main():
#     char = '一'  # 你要搜索的字符
#     results = await search_character(char)
#     if results:
#         for result in results:
#             print(f"矢量图 ID: {result['vectorId']}, 信息: {result['info']}")
#     else:
#         print(f"没有找到字符 '{char}' 的相关结果。")

# # 运行主函数
# import asyncio
# asyncio.run(main())
