#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微博多功能助手 - 登录与发送一体化工具
作者：@小庄-Python办公
"""

import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import ttkbootstrap as ttk
import requests
import json
import os
import time
import threading
from datetime import datetime
from PIL import Image, ImageTk, ImageGrab
import io
import base64
import subprocess

# Selenium imports
try:
    from selenium import webdriver
    from selenium.webdriver.common.by import By
    from selenium.webdriver.chrome.options import Options
    try:
        from selenium.webdriver.chrome.service import Service
    except ImportError:
        Service = None
    SELENIUM_AVAILABLE = True
except ImportError:
    SELENIUM_AVAILABLE = False

class WeiboAssistantApp:
    def __init__(self, root):
        self.root = root
        self.root.title("微博多功能助手 作者：@小庄-Python办公")
        self.root.geometry("900x750")
        
        # 设置图标
        self.setup_icon()
        
        # 初始化变量
        self.init_variables()
        
        # 创建菜单
        self.setup_menu()
        
        # 创建主界面（使用Notebook选项卡）
        self.setup_notebook()
        
        # 初始加载
        self.load_cookies()

    def setup_icon(self):
        current_dir = os.path.dirname(os.path.abspath(__file__))
        icon_path = os.path.join(current_dir, "微博发送模板.ico")
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception as e:
                print(f"设置图标失败: {e}")

    def init_variables(self):
        # 通用变量
        self.cookies = {}
        self.cookie_file = os.path.join("cookie", "cookie.json")
        self.xsrf_token = ""
        
        # 发送器变量
        self.image_paths = []
        self.preview_photos = []
        self.tags_file = "tags.json"
        self.common_tags = []
        self.load_tags()
        
        # 登录器变量
        self.session = requests.Session()
        self.driver = None
        self.login_success = False
        self.qr_check_thread = None
        self.qr_check_running = False
        
        # 设置请求头
        self.headers = {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Connection": "keep-alive",
            "MWeibo-Pwa": "1",
            "Referer": "https://weibo.com/",
            "Sec-Fetch-Dest": "empty",
            "Sec-Fetch-Mode": "cors",
            "Sec-Fetch-Site": "same-origin",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0.0.0 Safari/537.36 Edg/140.0.0.0",
        }
        
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'Accept-Encoding': 'gzip, deflate, br',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1'
        })

    def setup_menu(self):
        menubar = tk.Menu(self.root)
        self.root.config(menu=menubar)
        
        # 主题菜单
        theme_menu = tk.Menu(menubar, tearoff=0)
        menubar.add_cascade(label="主题切换", menu=theme_menu)
        
        # 预设主题
        presets = [
            ("明亮白", "cosmo"),
            ("暗夜黑", "darkly"),
            ("护眼黄", "solar"),
            ("少女粉", "pulse"),
            ("淡雅蓝", "cerculean"),
            ("韵味紫", "vapor")
        ]
        
        for name, theme in presets:
            theme_menu.add_command(label=name, command=lambda t=theme: self.change_theme(t))
            
        theme_menu.add_separator()
        
        # 更多主题
        more_menu = tk.Menu(theme_menu, tearoff=0)
        theme_menu.add_cascade(label="更多主题", menu=more_menu)
        
        for theme in self.root.style.theme_names():
            more_menu.add_command(label=theme, command=lambda t=theme: self.change_theme(t))

    def change_theme(self, theme_name):
        self.root.style.theme_use(theme_name)

    def setup_notebook(self):
        self.notebook = ttk.Notebook(self.root)
        self.notebook.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)
        
        # 发送微博页面
        self.sender_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.sender_frame, text=" 发送微博 ")
        self.setup_sender_ui()
        
        # 扫码登录页面
        self.login_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.login_frame, text=" 扫码登录 ")
        self.setup_login_ui()
        
        # 绑定切换事件
        self.notebook.bind("<<NotebookTabChanged>>", self.on_tab_changed)

    def on_tab_changed(self, event):
        # 当切换到发送页面时，刷新cookie状态
        if self.notebook.index("current") == 0:
            self.load_cookies()

    # ==================== 发送器功能模块 ====================
    
    def load_tags(self):
        if os.path.exists(self.tags_file):
            try:
                with open(self.tags_file, 'r', encoding='utf-8') as f:
                    self.common_tags = json.load(f)
            except Exception as e:
                self.log_sender(f"加载标签失败: {str(e)}")
                self.common_tags = ["生活手记", "日常分享", "程序员日常", "python自动化办公", "程序员"]
        else:
            self.common_tags = ["生活手记", "日常分享", "程序员日常", "python自动化办公", "程序员"]

    def save_tags(self):
        try:
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump(self.common_tags, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log_sender(f"保存标签失败: {str(e)}")

    def setup_sender_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.sender_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 状态栏
        self.status_label = ttk.Label(main_frame, text="状态: 等待加载Cookies...", bootstyle="warning")
        self.status_label.pack(fill=tk.X, pady=(0, 5))
        
        # 内容输入区
        content_frame = ttk.Labelframe(main_frame, text="微博内容", padding="5")
        content_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        # 标签控制区
        tag_frame = ttk.Frame(content_frame)
        tag_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        # 图片预览区
        self.preview_container = ttk.Frame(content_frame)
        self.preview_container.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        self.image_label = ttk.Label(self.preview_container, text="未选择图片")
        self.image_label.pack(side=tk.LEFT)
        
        self.thumbs_frame = ttk.Frame(self.preview_container)
        self.thumbs_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.clear_img_btn = ttk.Button(self.preview_container, text="清空图片", command=self.clear_images, bootstyle="danger-outline")
        
        # 图片控制栏
        img_ctrl_frame = ttk.Frame(content_frame)
        img_ctrl_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        ttk.Button(img_ctrl_frame, text="选择图片", command=self.select_image, bootstyle="info-outline").pack(side=tk.LEFT, padx=5)
        ttk.Button(img_ctrl_frame, text="粘贴图片", command=self.paste_image, bootstyle="info-outline").pack(side=tk.LEFT, padx=5)
        ttk.Label(img_ctrl_frame, text="(支持多图/重复/剪贴板，最多18张)").pack(side=tk.LEFT, padx=5)

        # 第一行：手动添加标签
        input_frame = ttk.Frame(tag_frame)
        input_frame.pack(fill=tk.X, pady=(0, 5))
        
        ttk.Label(input_frame, text="添加标签:").pack(side=tk.LEFT)
        self.tag_entry = ttk.Entry(input_frame, width=15)
        self.tag_entry.pack(side=tk.LEFT, padx=5)
        self.tag_entry.bind('<Return>', lambda e: self.add_tag())
        ttk.Button(input_frame, text="添加", command=self.add_tag, bootstyle="primary-outline").pack(side=tk.LEFT, padx=(0, 10))
        
        # 第二行：常用标签
        self.common_frame = ttk.Frame(tag_frame)
        self.common_frame.pack(fill=tk.X)
        
        self.refresh_common_tags()
            
        # 文本框
        self.content_text = scrolledtext.ScrolledText(content_frame, height=10)
        self.content_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self.content_text.bind('<Control-v>', self.on_paste)
        
        # 底部控制栏
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)
        
        self.send_btn = ttk.Button(bottom_frame, text="发送微博", command=self.send_weibo, state="disabled", bootstyle="success")
        self.send_btn.pack(side=tk.RIGHT, padx=5)
        
        # 日志区
        log_frame = ttk.Labelframe(main_frame, text="发送日志", padding="5")
        log_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.sender_log_text = scrolledtext.ScrolledText(log_frame, height=6)
        self.sender_log_text.pack(fill=tk.X)

    def log_sender(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.sender_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.sender_log_text.see(tk.END)

    def add_tag(self, tag_text=None):
        if tag_text is None:
            tag_text = self.tag_entry.get().strip()
        
        if tag_text:
            if not tag_text.startswith("#"):
                tag_text = "#" + tag_text
            if not tag_text.endswith("#"):
                tag_text = tag_text + "#"
            
            self.content_text.insert(tk.INSERT, f"{tag_text} ")
            
            if tag_text == f"#{self.tag_entry.get().strip()}#":
                self.tag_entry.delete(0, tk.END)
                
            self.content_text.focus()

    def refresh_common_tags(self):
        for widget in self.common_frame.winfo_children():
            widget.destroy()
            
        ttk.Label(self.common_frame, text="常用:").pack(side=tk.LEFT)
        ttk.Button(self.common_frame, text="⚙", width=3, command=self.manage_tags, bootstyle="secondary-outline").pack(side=tk.LEFT, padx=2)
        
        for tag in self.common_tags:
            btn = ttk.Button(self.common_frame, text=tag, 
                           command=lambda t=tag: self.add_tag(t), bootstyle="secondary-outline")
            btn.pack(side=tk.LEFT, padx=2)

    def manage_tags(self):
        manage_win = ttk.Toplevel(self.root)
        manage_win.title("管理常用标签")
        
        window_width = 300
        window_height = 400
        self.root.update_idletasks()
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        pos_x = root_x + (root_width - window_width) // 2
        pos_y = root_y + (root_height - window_height) // 2
        manage_win.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
        
        manage_win.transient(self.root)
        manage_win.grab_set()
        
        list_frame = ttk.Frame(manage_win, padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tags_listbox = tk.Listbox(list_frame)
        self.tags_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tags_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tags_listbox.config(yscrollcommand=scrollbar.set)
        
        for tag in self.common_tags:
            self.tags_listbox.insert(tk.END, tag)
            
        ctrl_frame = ttk.Frame(manage_win, padding="5")
        ctrl_frame.pack(fill=tk.X)
        
        self.new_tag_var = tk.StringVar()
        entry = ttk.Entry(ctrl_frame, textvariable=self.new_tag_var)
        entry.pack(fill=tk.X, pady=5)
        entry.bind('<Return>', lambda e: self.add_tag_to_list(manage_win))
        
        btn_frame = ttk.Frame(ctrl_frame)
        btn_frame.pack(fill=tk.X)
        
        ttk.Button(btn_frame, text="添加", command=lambda: self.add_tag_to_list(manage_win), bootstyle="primary").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        ttk.Button(btn_frame, text="删除选中", command=self.delete_tag_from_list, bootstyle="danger").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=2)
        
    def add_tag_to_list(self, win):
        tag = self.new_tag_var.get().strip()
        if tag:
            if tag not in self.common_tags:
                self.common_tags.append(tag)
                self.tags_listbox.insert(tk.END, tag)
                self.new_tag_var.set("")
                self.save_tags()
                self.refresh_common_tags()
            else:
                messagebox.showwarning("提示", "标签已存在", parent=win)
                
    def delete_tag_from_list(self):
        selection = self.tags_listbox.curselection()
        if selection:
            idx = selection[0]
            tag = self.tags_listbox.get(idx)
            self.common_tags.remove(tag)
            self.tags_listbox.delete(idx)
            self.save_tags()
            self.refresh_common_tags()

    def load_cookies(self):
        if not os.path.exists(self.cookie_file):
            self.log_sender("Cookie文件不存在，请切换到'扫码登录'页进行登录")
            self.status_label.config(text="状态: Cookie文件缺失，请先扫码登录", bootstyle="danger")
            self.send_btn.config(state="disabled")
            return

        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'cookie_dict' in data:
                    self.cookies = data['cookie_dict']
                    self.xsrf_token = self.cookies.get('XSRF-TOKEN', '')
                    if not self.xsrf_token:
                        cookie_str = data.get('cookie_string', '')
                        if 'XSRF-TOKEN=' in cookie_str:
                            self.xsrf_token = cookie_str.split('XSRF-TOKEN=')[1].split(';')[0]
                    
                    if self.cookies:
                        self.status_label.config(text="状态: Cookies已加载", bootstyle="success")
                        self.send_btn.config(state="normal")
                        self.log_sender("Cookies加载成功")
                        
                        # 更新session cookie，以便发送使用
                        self.session.cookies.update(self.cookies)
                    else:
                        self.log_sender("Cookie数据为空")
                else:
                    self.log_sender("Cookie文件格式错误")
        except Exception as e:
            self.log_sender(f"加载Cookies失败: {str(e)}")

    def select_image(self):
        file_paths = filedialog.askopenfilenames(
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.gif *.bmp")]
        )
        if file_paths:
            self.add_images(file_paths)

    def paste_image(self):
        try:
            image = ImageGrab.grabclipboard()
            if isinstance(image, Image.Image):
                temp_dir = "temp"
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                temp_path = os.path.join(temp_dir, f"paste_{timestamp}.png")
                image.save(temp_path, "PNG")
                self.add_images([temp_path])
            else:
                messagebox.showinfo("提示", "剪贴板中没有图片")
        except Exception as e:
            self.log_sender(f"粘贴图片失败: {str(e)}")

    def on_paste(self, event):
        try:
            image = ImageGrab.grabclipboard()
            if isinstance(image, Image.Image):
                self.paste_image()
                return "break"
        except:
            pass
        return None

    def add_images(self, new_paths):
        current_count = len(self.image_paths)
        new_count = len(new_paths)
        
        if current_count + new_count > 18:
            messagebox.showwarning("提示", f"图片总数不能超过18张\n当前: {current_count}, 尝试添加: {new_count}")
            allowed_count = 18 - current_count
            if allowed_count > 0:
                self.image_paths.extend(new_paths[:allowed_count])
                self.log_sender(f"已添加前 {allowed_count} 张图片 (达到上限)")
        else:
            self.image_paths.extend(new_paths)
            self.log_sender(f"已添加 {new_count} 张图片")
            
        self.refresh_image_preview()

    def refresh_image_preview(self):
        for widget in self.thumbs_frame.winfo_children():
            widget.destroy()
        self.preview_photos.clear()
        
        if not self.image_paths:
            self.image_label.pack(side=tk.LEFT)
            self.clear_img_btn.pack_forget()
            return
            
        self.image_label.pack_forget()
        self.clear_img_btn.pack(side=tk.RIGHT, padx=5)
        
        for idx, path in enumerate(self.image_paths):
            try:
                img = Image.open(path)
                img.thumbnail((60, 60))
                photo = ImageTk.PhotoImage(img)
                self.preview_photos.append(photo)
                
                frame = ttk.Frame(self.thumbs_frame, borderwidth=1, relief="solid")
                frame.pack(side=tk.LEFT, padx=2, pady=2)
                
                lbl = ttk.Label(frame, image=photo)
                lbl.pack()
                
                if idx > 8:
                    if idx == 9:
                        ttk.Label(self.thumbs_frame, text=f"... (+{len(self.image_paths)-9})").pack(side=tk.LEFT, padx=5)
                    continue
                    
            except Exception as e:
                self.log_sender(f"预览失败: {os.path.basename(path)}")

    def clear_images(self):
        self.image_paths = []
        self.refresh_image_preview()
        self.log_sender("已清空所有图片")

    def get_mobile_stoken(self):
        try:
            url = "https://m.weibo.cn/api/config"
            headers = {
                "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
                "X-Requested-With": "XMLHttpRequest",
                "Referer": "https://m.weibo.cn/"
            }
            response = requests.get(url, headers=headers, cookies=self.cookies, timeout=10)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'st' in data['data']:
                    return data['data']['st']
        except Exception as e:
            self.log_sender(f"获取Mobile Token失败: {e}")
        return None

    def upload_single_image(self, file_path):
        try:
            # 1. 尝试使用 m.weibo.cn 移动端接口 (兼容移动端Cookie)
            stoken = self.get_mobile_stoken()
            if stoken:
                url = "https://m.weibo.cn/api/statuses/uploadPic"
                headers = {
                    "X-XSRF-TOKEN": stoken,
                    "Origin": "https://m.weibo.cn",
                    "Referer": "https://m.weibo.cn/compose",
                    "User-Agent": "Mozilla/5.0 (Linux; Android 11; Pixel 5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.91 Mobile Safari/537.36",
                    "X-Requested-With": "XMLHttpRequest"
                }
                
                with open(file_path, 'rb') as f:
                    img_data = f.read()
                
                files = {
                    'pic': (os.path.basename(file_path), img_data, 'image/jpeg')
                }
                data_post = {'st': stoken}
                
                response = requests.post(url, headers=headers, cookies=self.cookies, files=files, data=data_post, timeout=30)
                
                if response.status_code == 200:
                    try:
                        data = response.json()
                        if 'pic_id' in data:
                            return data['pic_id']
                    except:
                        pass
                else:
                    self.log_sender(f"移动端上传失败: {response.status_code} - {response.text[:50]}")

            # 2. 如果移动端失败，尝试使用 weibo.com 新版接口 (备用)
            url = "https://weibo.com/ajax/statuses/uploadPicture"
            
            headers = {
                "X-XSRF-TOKEN": self.xsrf_token,
                "Origin": "https://weibo.com",
                "Referer": "https://weibo.com/",
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "X-Requested-With": "XMLHttpRequest"
            }
            
            # 读取图片
            with open(file_path, 'rb') as f:
                img_data = f.read()
            
            # 构建 multipart/form-data
            # 注意：Weibo 接口通常只需要 'pic' 字段
            files = {
                'pic': (os.path.basename(file_path), img_data, 'image/jpeg')
            }
            
            # 增加 timeout 防止长时间挂起
            response = requests.post(url, headers=headers, cookies=self.cookies, files=files, timeout=30)
            
            if response.status_code == 200:
                # 尝试解析 JSON
                try:
                    data = response.json()
                    if 'pic_id' in data:
                        return data['pic_id']
                except:
                    pass
                    
                # 如果 JSON 解析失败，尝试正则提取
                import re
                content = response.text
                match = re.search(r'"pic_id"\s*:\s*"(\w+)"', content)
                if match:
                    return match.group(1)
            
            self.log_sender(f"图片上传失败 ({os.path.basename(file_path)}): {response.text[:100]}...")
            return None
            
        except Exception as e:
            self.log_sender(f"上传图片出错 ({os.path.basename(file_path)}): {str(e)}")
            return None

    def upload_images(self):
        if not self.image_paths:
            return []
            
        uploaded_ids = []
        total = len(self.image_paths)
        
        self.log_sender(f"开始上传 {total} 张图片...")
        
        for i, path in enumerate(self.image_paths):
            self.log_sender(f"正在上传第 {i+1}/{total} 张: {os.path.basename(path)}")
            pid = self.upload_single_image(path)
            if pid:
                uploaded_ids.append(pid)
            else:
                self.log_sender(f"第 {i+1} 张图片上传失败，已跳过")
                
        if not uploaded_ids:
            return []
            
        self.log_sender(f"成功上传 {len(uploaded_ids)}/{total} 张图片")
        return uploaded_ids

    def send_weibo(self):
        content = self.content_text.get("1.0", tk.END).strip()
        if not content and not self.image_paths:
            messagebox.showwarning("提示", "请输入微博内容或选择图片")
            return
            
        self.send_btn.config(state="disabled")
        threading.Thread(target=self._send_thread, args=(content,), daemon=True).start()

    def _send_thread(self, content):
        try:
            pic_id_data = ""
            if self.image_paths:
                uploaded_ids = self.upload_images()
                if not uploaded_ids and self.image_paths:
                    self.root.after(0, lambda: messagebox.showerror("错误", "图片上传失败，终止发送"))
                    self.root.after(0, lambda: self.send_btn.config(state="normal"))
                    return
                
                # 构建 pic_id JSON 结构
                # 格式参考: [{"type":"image/png","pid":"..."}]
                if uploaded_ids:
                    pic_list = []
                    for pid in uploaded_ids:
                        pic_list.append({
                            "type": "image/jpeg",  # 默认使用 jpeg，实际上传也是 jpeg MIME
                            "pid": pid
                        })
                    pic_id_data = json.dumps(pic_list)

            url = "https://www.weibo.com/ajax/statuses/update"
            
            headers = {
                "accept": "application/json, text/plain, */*",
                "content-type": "application/x-www-form-urlencoded",
                "origin": "https://www.weibo.com",
                "referer": "https://www.weibo.com",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "x-requested-with": "XMLHttpRequest",
                "x-xsrf-token": self.xsrf_token
            }
            
            data = {
                "content": content,
                "visible": "0",
                "share_id": "",
                "vote": "",
                "media": "",
                "pic_id": pic_id_data,
                "lat": "0",
                "long": "0",
                "pub_type": "0",
                "is_word": "0",
                "is_hot": "0"
            }
            
            response = requests.post(url, headers=headers, cookies=self.cookies, data=data)
            
            if response.status_code == 200:
                result = response.json()
                if 'id' in result or 'data' in result:
                    self.root.after(0, lambda: self.log_sender("发送成功！"))
                    self.root.after(0, lambda: messagebox.showinfo("成功", "微博发送成功！"))
                    self.root.after(0, lambda: self.content_text.delete("1.0", tk.END))
                    self.root.after(0, self.clear_images)
                else:
                    self.root.after(0, lambda: self.log_sender(f"发送失败: {result}"))
                    self.root.after(0, lambda: messagebox.showerror("失败", f"发送失败: {result}"))
            else:
                self.root.after(0, lambda: self.log_sender(f"请求失败: {response.status_code} - {response.text}"))
                self.root.after(0, lambda: messagebox.showerror("错误", f"请求失败: {response.status_code}"))
                
        except Exception as e:
            self.root.after(0, lambda: self.log_sender(f"发送出错: {str(e)}"))
            self.root.after(0, lambda: messagebox.showerror("错误", f"发送出错: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.send_btn.config(state="normal"))

    # ==================== 登录器功能模块 ====================

    def setup_login_ui(self):
        main_frame = ttk.Frame(self.login_frame, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # 左右分栏
        left_frame = ttk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 5))
        
        right_frame = ttk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=(5, 0))
        
        # 左侧控制区
        control_frame = ttk.Labelframe(left_frame, text="登录控制", padding="10")
        control_frame.pack(fill=tk.BOTH, expand=True, pady=(0, 10))
        
        self.login_btn = ttk.Button(control_frame, text="获取登录二维码", command=self.get_qr_code, bootstyle="info")
        self.login_btn.pack(fill=tk.X, pady=5)
        
        self.stop_btn = ttk.Button(control_frame, text="停止监控", command=self.stop_qr_check, state="disabled", bootstyle="warning")
        self.stop_btn.pack(fill=tk.X, pady=5)
        
        self.check_btn = ttk.Button(control_frame, text="手动检查登录", command=self.manual_check_login, state="disabled", bootstyle="secondary")
        self.check_btn.pack(fill=tk.X, pady=5)
        
        self.clear_cookies_btn = ttk.Button(control_frame, text="清除Cookies", command=self.clear_cookies, bootstyle="danger")
        self.clear_cookies_btn.pack(fill=tk.X, pady=5)
        
        # 状态显示
        status_frame = ttk.Labelframe(left_frame, text="登录状态", padding="5")
        status_frame.pack(fill=tk.X)
        
        self.login_status_label = ttk.Label(status_frame, text="未登录", bootstyle="danger")
        self.login_status_label.pack(pady=5)
        
        self.progress = ttk.Progressbar(status_frame, mode='indeterminate')
        self.progress.pack(fill=tk.X, pady=5)
        
        # 右侧二维码显示区
        qr_frame = ttk.Labelframe(right_frame, text="扫码区域", padding="10")
        qr_frame.pack(fill=tk.BOTH, expand=True)
        
        self.qr_label = ttk.Label(qr_frame, text="点击'获取登录二维码'开始\n\n请使用微博手机APP扫码", 
                                 anchor="center", justify="center")
        self.qr_label.pack(expand=True)
        
        # 底部日志区域 (共用)
        log_frame = ttk.Labelframe(self.login_frame, text="登录日志", padding="10")
        log_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=10, padx=10)
        
        self.login_log_text = scrolledtext.ScrolledText(log_frame, height=8)
        self.login_log_text.pack(fill=tk.X)
        
        if not SELENIUM_AVAILABLE:
            self.log_login("警告: 未检测到Selenium，将使用简化模式")

    def log_login(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.login_log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.login_log_text.see(tk.END)

    def get_qr_code(self):
        self.log_login("正在获取登录二维码...")
        self.login_btn.config(state="disabled")
        self.progress.start()
        threading.Thread(target=self._fetch_qr_code, daemon=True).start()

    def _fetch_qr_code(self):
        try:
            if SELENIUM_AVAILABLE:
                self._fetch_qr_with_selenium()
            else:
                self._fetch_qr_without_selenium()
        except Exception as e:
            self.root.after(0, lambda: self.log_login(f"获取二维码失败: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.progress.stop())
            self.root.after(0, lambda: self.login_btn.config(state="normal"))

    def _fetch_qr_with_selenium(self):
        try:
            self.root.after(0, lambda: self.log_login("正在启动浏览器..."))
            
            chrome_options = Options()
            chrome_options.add_argument('--headless')
            chrome_options.add_argument('--no-sandbox')
            chrome_options.add_argument('--disable-dev-shm-usage')
            chrome_options.add_argument('--disable-gpu')
            chrome_options.add_argument('--window-size=1920,1080')
            
            if Service:
                service = Service()
                if os.name == 'nt':
                    service.creation_flags = getattr(subprocess, 'CREATE_NO_WINDOW', 0x08000000)
                self.driver = webdriver.Chrome(service=service, options=chrome_options)
            else:
                self.driver = webdriver.Chrome(options=chrome_options)
            
            login_url = "https://passport.weibo.com/sso/signin?entry=wapsso&source=wapssowb&url=https%3A%2F%2Fm.weibo.cn%2Fp%2Ftabbar%3Fcontainerid%3D100803_-_recentvisit"
            self.root.after(0, lambda: self.log_login("正在访问登录页面..."))
            self.driver.get(login_url)
            
            time.sleep(3)
            
            try:
                qr_selectors = [
                    "img[src*='qr']", ".qrcode img", "#qrcode img", 
                    "img[alt*='二维码']", "img[alt*='QR']", ".W_login_qrcode img",
                    "img[class*='QRCode']"
                ]
                
                qr_element = None
                for selector in qr_selectors:
                    try:
                        qr_element = self.driver.find_element(By.CSS_SELECTOR, selector)
                        if qr_element:
                            break
                    except:
                        continue
                
                if qr_element:
                    qr_src = qr_element.get_attribute('src')
                    if qr_src:
                        self.root.after(0, lambda: self._display_qr_from_url(qr_src))
                        self.root.after(0, lambda: self.log_login("成功获取二维码，请扫码登录"))
                        self._start_login_monitoring()
                    else:
                        self.root.after(0, lambda: self.log_login("未找到二维码图片源"))
                else:
                    self.root.after(0, lambda: self.log_login("未找到二维码元素，可能页面结构已变化"))
                    self._show_manual_login_info()
                    
            except Exception as e:
                self.root.after(0, lambda: self.log_login(f"查找二维码失败: {str(e)}"))
                self._show_manual_login_info()
                
        except Exception as e:
            self.root.after(0, lambda: self.log_login(f"启动浏览器失败: {str(e)}"))
            self._fetch_qr_without_selenium()

    def _fetch_qr_without_selenium(self):
        self.root.after(0, lambda: self.log_login("使用简化模式，请手动登录"))
        self._show_manual_login_info()

    def _show_manual_login_info(self):
        login_url = "https://weibo.com/newlogin?tabtype=weibo&gid=102803&url=https%3A%2F%2Fweibo.com%2F"
        info_text = f"请在浏览器中打开以下链接进行登录:\n\n{login_url}\n\n登录完成后，点击'手动检查登录'按钮"
        
        self.root.after(0, lambda: self.qr_label.config(text=info_text, image=''))
        self.root.after(0, lambda: self.check_btn.config(state="normal"))
        self.root.after(0, lambda: self.log_login("请在浏览器中完成登录"))

    def _display_qr_from_url(self, qr_url):
        try:
            if qr_url.startswith('data:image'):
                header, data = qr_url.split(',', 1)
                image_data = base64.b64decode(data)
                image = Image.open(io.BytesIO(image_data))
            else:
                response = requests.get(qr_url, timeout=10)
                image = Image.open(io.BytesIO(response.content))
            
            image = image.resize((250, 250), Image.Resampling.LANCZOS)
            photo = ImageTk.PhotoImage(image)
            
            self.qr_label.config(image=photo, text="")
            self.qr_label.image = photo
            
        except Exception as e:
            self.log_login(f"显示二维码失败: {str(e)}")
            self._show_manual_login_info()

    def _start_login_monitoring(self):
        self.qr_check_running = True
        self.stop_btn.config(state="normal")
        self.qr_check_thread = threading.Thread(target=self._monitor_login, daemon=True)
        self.qr_check_thread.start()

    def _monitor_login(self):
        check_count = 0
        max_checks = 60
        
        while self.qr_check_running and check_count < max_checks:
            try:
                if self.driver:
                    current_url = self.driver.current_url
                    # 检查是否跳转到了weibo.com首页或m.weibo.cn，且不是登录页
                    is_logged_in = False
                    if 'weibo.com' in current_url and 'login' not in current_url and 'passport' not in current_url:
                        is_logged_in = True
                    elif 'm.weibo.cn' in current_url and 'passport' not in current_url:
                        is_logged_in = True
                        
                    if is_logged_in:
                        cookies = self.driver.get_cookies()
                        self.cookies = {cookie['name']: cookie['value'] for cookie in cookies}
                        self.session.cookies.update(self.cookies)
                        self.login_success = True
                        self.root.after(0, self._update_login_success)
                        self.save_cookies()
                        break
                
                check_count += 1
                time.sleep(5)
                
            except Exception as e:
                self.root.after(0, lambda: self.log_login(f"监控登录状态出错: {str(e)}"))
                break
        
        if check_count >= max_checks:
            self.root.after(0, lambda: self.log_login("登录监控超时，请手动检查"))
        
        self.qr_check_running = False
        self.root.after(0, lambda: self.stop_btn.config(state="disabled"))
        
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except:
                pass

    def stop_qr_check(self):
        self.qr_check_running = False
        self.stop_btn.config(state="disabled")
        self.log_login("已停止登录监控")
        
        if self.driver:
            try:
                self.driver.quit()
                self.driver = None
            except:
                pass

    def manual_check_login(self):
        self.log_login("正在手动检查登录状态...")
        self.check_btn.config(state="disabled")
        threading.Thread(target=self._manual_check, daemon=True).start()

    def _manual_check(self):
        try:
            test_url = "https://m.weibo.cn/api/config"
            response = self.session.get(test_url, timeout=10)
            
            if response.status_code == 200:
                data = response.json()
                if 'data' in data and 'login' in data['data'] and data['data']['login']:
                    self.login_success = True
                    self.cookies = dict(self.session.cookies)
                    self.root.after(0, self._update_login_success)
                    self.save_cookies()
                else:
                    self.root.after(0, lambda: self.log_login("尚未登录，请完成登录后重试"))
            else:
                self.root.after(0, lambda: self.log_login(f"检查登录状态失败: {response.status_code}"))
                
        except Exception as e:
            self.root.after(0, lambda: self.log_login(f"检查登录状态出错: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.check_btn.config(state="normal"))

    def _update_login_success(self):
        self.login_status_label.config(text="已登录", bootstyle="success")
        self.check_btn.config(state="disabled")
        self.log_login("登录成功！")
        # 刷新发送器状态
        self.load_cookies()

    def save_cookies(self):
        try:
            os.makedirs(os.path.dirname(self.cookie_file), exist_ok=True)
            
            cookie_data = {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "cookie_string": "; ".join([f"{k}={v}" for k, v in self.cookies.items()]),
                "cookie_dict": self.cookies,
                "detailed_cookies": [
                    {
                        "name": name,
                        "value": value,
                        "domain": "weibo.com",
                        "path": "/",
                        "secure": True,
                        "httponly": False
                    }
                    for name, value in self.cookies.items()
                ]
            }
            
            with open(self.cookie_file, 'w', encoding='utf-8') as f:
                json.dump(cookie_data, f, indent=2, ensure_ascii=False)
            
            self.log_login("Cookies已保存到本地文件")
            
        except Exception as e:
            self.log_login(f"保存cookies失败: {str(e)}")

    def clear_cookies(self):
        try:
            self.cookies = {}
            self.session.cookies.clear()
            self.login_success = False
            self.login_status_label.config(text="未登录", bootstyle="danger")
            
            if os.path.exists(self.cookie_file):
                os.remove(self.cookie_file)
                
            self.log_login("已清除所有Cookies")
            self.log_sender("Cookies已清除")
            self.status_label.config(text="状态: 未登录", bootstyle="danger")
            self.send_btn.config(state="disabled")
            
        except Exception as e:
            self.log_login(f"清除cookies失败: {str(e)}")

if __name__ == "__main__":
    root = ttk.Window(themename="cosmo")
    app = WeiboAssistantApp(root)
    root.mainloop()
