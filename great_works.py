# 一次性全部爬取
# from playwright.sync_api import sync_playwright
# import time
# import requests
# import os

# # 保存图片的函数
# def save_image(url, filename):
#     response = requests.get(url)
#     if response.status_code == 200:
#         with open(filename, 'wb') as f:
#             f.write(response.content)

# # 启动 Playwright
# with sync_playwright() as p:
#     browser = p.chromium.launch(headless=True)
#     page = browser.new_page()

#     # 访问目标网站
#     page.goto('https://www.ltfc.net/search?keyword=%E7%8E%8B%E7%BE%B2%E4%B9%8B&curTab=SUHA&sortBy=matching')  # 替换成目标网址

#     # 滚动页面，确保所有目标元素加载完成
#     previous_height = 0
#     while True:
#         page.evaluate("window.scrollTo(0, document.body.scrollHeight)")  # 滚动到底部
#         time.sleep(2)  # 等待加载
#         current_height = page.evaluate("document.body.scrollHeight")
#         if current_height == previous_height:  # 如果页面高度未变化，说明滚动加载完成
#             break
#         previous_height = current_height

#     # 提取所有图片的 URL
#     divs = page.query_selector_all('.card_image___3yEH7')

#     # 创建保存图片的文件夹
#     if not os.path.exists('images'):
#         os.makedirs('images')

#     for i, div in enumerate(divs):
#         style = div.get_attribute('style')
#         url = style.split('url(')[1].split(')')[0].replace('"', '')
#         save_image(url, f'images/image_{i+1}.jpg')

#     # 关闭浏览器
#     browser.close()


#异步爬取
# -*- coding: utf-8 -*-
# import asyncio
# import os
# from playwright.async_api import async_playwright
# import aiohttp

# async def save_image(session, url, filename):
#     """下载图片"""
#     try:
#         async with session.get(url) as response:
#             if response.status == 200:
#                 with open(filename, 'wb') as f:
#                     f.write(await response.read())
#                 print(f"已下载: {filename}")
#             else:
#                 print(f"下载失败: {url}")
#     except Exception as e:
#         print(f"下载异常: {url}，错误: {e}")

# async def fetch_images():
#     async with async_playwright() as p:
#         browser = await p.chromium.launch(headless=True)
#         page = await browser.new_page()

#         # 访问目标网站
#         await page.goto('https://www.ltfc.net/search?keyword=%E7%8E%8B%E7%BE%B2%E4%B9%8B&curTab=SUHA&sortBy=matching')  # 替换成目标网址

#         # 创建文件夹
#         if not os.path.exists('images'):
#             os.makedirs('images')

#         # 优先获取前几张图片
#         visible_divs = await page.query_selector_all('.card_image___3yEH7')
#         initial_urls = []
#         for i, div in enumerate(visible_divs[:5]):  # 提取前5张
#             style = await div.get_attribute('style')
#             url = style.split('url(')[1].split(')')[0].replace('"', '')
#             initial_urls.append(url)

#         # 下载前几张图片
#         async with aiohttp.ClientSession() as session:
#             tasks = []
#             for i, url in enumerate(initial_urls):
#                 filename = f'images/image_{i+1}.jpg'
#                 tasks.append(save_image(session, url, filename))
#             await asyncio.gather(*tasks)  # 优先完成前几张图片的下载

#         print("首批图片下载完成，开始加载更多图片...")

#         # 滚动加载剩余图片
#         all_urls = initial_urls[:]
#         previous_height = 0
#         batch_size = 10
#         batch_counter = 1

#         while True:
#             # 滚动到页面底部
#             await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
#             await asyncio.sleep(2)  # 等待页面加载

#             # 检查页面高度是否还在变化
#             current_height = await page.evaluate("document.body.scrollHeight")
#             if current_height == previous_height:
#                 break
#             previous_height = current_height

#             # 获取新加载的图片
#             divs = await page.query_selector_all('.card_image___3yEH7')
#             batch_urls = []
#             for div in divs[len(all_urls):]:  # 只提取新出现的图片
#                 style = await div.get_attribute('style')
#                 url = style.split('url(')[1].split(')')[0].replace('"', '')
#                 batch_urls.append(url)

#             # 合并到总 URL 列表中
#             all_urls.extend(batch_urls)

#             # 下载该批次图片
#             if batch_urls:
#                 print(f"开始下载第 {batch_counter} 批图片...")
#                 async with aiohttp.ClientSession() as session:
#                     tasks = []
#                     for i, url in enumerate(batch_urls):
#                         filename = f'images/image_{len(all_urls) - len(batch_urls) + i + 1}.jpg'
#                         tasks.append(save_image(session, url, filename))
#                     await asyncio.gather(*tasks)
#                 print(f"第 {batch_counter} 批图片下载完成")
#                 batch_counter += 1

#         await browser.close()
#         print(f"全部图片下载完成，共 {len(all_urls)} 张图片")

# # 运行异步任务
# asyncio.run(fetch_images())



# from playwright.sync_api import sync_playwright
# import os
# import json

# def scrape_images_and_info(url, output_folder):
#     with sync_playwright() as p:
#         browser = p.chromium.launch(headless=True)
#         page = browser.new_page()

#         # 访问目标网站
#         page.goto(url)
#         page.wait_for_selector('.suha_card___3f_k8', timeout=30000)

#         # 确保输出文件夹存在
#         os.makedirs(output_folder, exist_ok=True)

#         # 获取所有包含图片和信息的父容器
#         containers = page.query_selector_all('.suha_card___3f_k8')

#         data = []
#         for index, container in enumerate(containers):
#             try:
#                 # 获取图片 URL
#                 image_div = container.query_selector('.card_image___3yEH7')
#                 background_image = image_div.get_attribute('style')
#                 image_url = background_image.split('url("')[1].split('")')[0]

#                 # 获取作品名称
#                 name_div = container.query_selector('.name___10uio')
#                 name = name_div.inner_text().strip() if name_div else '未知'

#                 # 获取作者和朝代
#                 author_div = container.query_selector('.author_age___aswT-')
#                 author_age = author_div.inner_text().strip() if author_div else '未知'

#                 # 获取存放地址
#                 owner_div = container.query_selector('.owner___qnvl0')
#                 owner = owner_div.inner_text().strip() if owner_div else '未知'

#                 # 下载图片
#                 image_filename = f"{index + 1}.jpg"
#                 image_path = os.path.join(output_folder, image_filename)
#                 image_div.screenshot(path=image_path)

#                 # 保存数据
#                 data.append({
#                     'image': image_filename,
#                     'image_url': image_url,
#                     'name': name,
#                     'author_age': author_age,
#                     'owner': owner
#                 })

#                 print(f"成功提取第 {index + 1} 张图片及信息")

#             except Exception as e:
#                 print(f"提取第 {index + 1} 项数据时出错: {e}")

#         # 保存 JSON 文件
#         json_path = os.path.join(output_folder, 'data.json')
#         with open(json_path, 'w', encoding='utf-8') as f:
#             json.dump(data, f, ensure_ascii=False, indent=4)

#         browser.close()

# # 使用示例
# scrape_images_and_info(
#     url='https://www.ltfc.net/search?keyword=%E7%8E%8B%E7%BE%B2%E4%B9%8B&curTab=SUHA&sortBy=matching',  # 替换为实际网址
#     output_folder='./output_works'
# )



import asyncio
from playwright.async_api import async_playwright

async def search_artworks(keyword):
    """
    根据关键字搜索书法作品，并返回图片及相关信息的列表。

    Args:
        keyword (str): 查询关键字

    Returns:
        list[dict]: 格式化的书法作品数据
    """
    async def fetch_images_and_info(page):
        """从页面提取图片及作品相关信息"""
        data = []
        containers = await page.query_selector_all('.suha_card___3f_k8')

        for container in containers:
            # 获取图片 URL
            image_url, name, author, owner = None, None, None, None
            image_div = await container.query_selector('.card_image___3yEH7')
            if image_div:
                style = await image_div.get_attribute('style')
                if style:
                    image_url = style.split('background-image: url("')[1].split('");')[0]

            # 获取作品名称
            name_div = await container.query_selector('.name___10uio')
            if name_div:
                name = await name_div.inner_text()

            # 获取作者和朝代
            author_div = await container.query_selector('.author_age___aswT-')
            if author_div:
                author = await author_div.inner_text()

            # 获取存放地址
            owner_div = await container.query_selector('.owner___qnvl0')
            if owner_div:
                owner = await owner_div.inner_text()

            if image_url and name and author and owner:
                data.append({
                    'imageUrl': image_url,
                    'title': name,
                    'artist': author.split(" ")[1],  # 分离作者姓名（假设格式为 "朝代 作者"）
                    'dynasty': author.split(" ")[0] if " " in author else "未知",
                    'location': owner
                })

        return data

    async def scroll_and_load(page):
        """滚动加载页面并获取所有数据"""
        previous_height = 0
        current_height = -1
        total_data = []

        while current_height != previous_height:
            previous_height = await page.evaluate('document.body.scrollHeight')
            
            # 滚动页面
            await page.evaluate('window.scrollBy(0, document.body.scrollHeight)')
            await asyncio.sleep(2)  # 等待内容加载
            
            current_height = await page.evaluate('document.body.scrollHeight')

            # 提取当前页面的数据
            data = await fetch_images_and_info(page)
            if data:
                total_data.extend(data)

            # 停止加载条件（可根据需求调整）
            if len(total_data) >= 50:
                break

        return total_data

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        
        # 动态设置 URL
        search_url = f"https://www.ltfc.net/search?keyword={keyword}&curTab=SUHA&sortBy=matching"
        await page.goto(search_url)

        # 滚动加载页面并获取数据
        try:
            artworks = await scroll_and_load(page)
        finally:
            await browser.close()

        return artworks


