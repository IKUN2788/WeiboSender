import tkinter as tk
from tkinter import messagebox, scrolledtext, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
import requests
import json
import os
import threading
from datetime import datetime
from PIL import Image, ImageTk, ImageGrab
import io

class WeiboSenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("微博发送器 作者：@小庄-Python办公")
        self.root.geometry("800x700")
        
        # 设置图标
        icon_path = "../微博发送模板.ico"
        if os.path.exists(icon_path):
            try:
                self.root.iconbitmap(icon_path)
            except Exception as e:
                print(f"设置图标失败: {e}")
        
        # 初始化变量
        self.cookies = {}
        self.cookie_file = os.path.join("../cookie", "cookie.json")
        self.xsrf_token = ""
        self.image_paths = []  # 存储多个图片路径
        self.preview_photos = [] # 保持图片引用
        
        self.tags_file = "tags.json"
        self.common_tags = []
        self.load_tags()
        
        self.setup_menu()
        self.setup_ui()
        self.load_cookies()

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

    def load_tags(self):
        if os.path.exists(self.tags_file):
            try:
                with open(self.tags_file, 'r', encoding='utf-8') as f:
                    self.common_tags = json.load(f)
            except Exception as e:
                self.log(f"加载标签失败: {str(e)}")
                self.common_tags = ["生活手记", "日常分享", "程序员日常", "python自动化办公", "程序员"]
        else:
            self.common_tags = ["生活手记", "日常分享", "程序员日常", "python自动化办公", "程序员"]

    def save_tags(self):
        try:
            with open(self.tags_file, 'w', encoding='utf-8') as f:
                json.dump(self.common_tags, f, ensure_ascii=False, indent=2)
        except Exception as e:
            self.log(f"保存标签失败: {str(e)}")

    def setup_ui(self):
        # 主框架
        main_frame = ttk.Frame(self.root, padding="10")
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
        
        # 图片预览区 (使用Canvas实现简单的横向滚动效果)
        self.preview_container = ttk.Frame(content_frame)
        self.preview_container.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        self.image_label = ttk.Label(self.preview_container, text="未选择图片")
        self.image_label.pack(side=tk.LEFT)
        
        self.thumbs_frame = ttk.Frame(self.preview_container)
        self.thumbs_frame.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        self.clear_img_btn = ttk.Button(self.preview_container, text="清空图片", command=self.clear_images, bootstyle="danger-outline")
        # 初始不显示清空按钮
        
        # 图片控制栏
        img_ctrl_frame = ttk.Frame(content_frame)
        img_ctrl_frame.pack(side=tk.BOTTOM, fill=tk.X, pady=(5, 0))
        
        ttk.Button(img_ctrl_frame, text="选择图片", command=self.select_image, bootstyle="info-outline").pack(side=tk.LEFT, padx=5)
        ttk.Button(img_ctrl_frame, text="粘贴图片", command=self.paste_image, bootstyle="info-outline").pack(side=tk.LEFT, padx=5)
        ttk.Label(img_ctrl_frame, text="(支持多图/重复/剪贴板，最多18张)").pack(side=tk.LEFT, padx=5)

        # 第一行：手动添加
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
            
        # 文本框（Pack到剩余空间）
        self.content_text = scrolledtext.ScrolledText(content_frame, height=10)
        self.content_text.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        # 绑定粘贴事件
        self.content_text.bind('<Control-v>', self.on_paste)
        
        # 底部控制栏
        bottom_frame = ttk.Frame(main_frame)
        bottom_frame.pack(fill=tk.X)
        
        self.send_btn = ttk.Button(bottom_frame, text="发送微博", command=self.send_weibo, state="disabled", bootstyle="success")
        self.send_btn.pack(side=tk.RIGHT, padx=5)
        
        # 日志区
        log_frame = ttk.Labelframe(main_frame, text="日志", padding="5")
        log_frame.pack(fill=tk.X, pady=(10, 0))
        
        self.log_text = scrolledtext.ScrolledText(log_frame, height=6)
        self.log_text.pack(fill=tk.X)

    def log(self, message):
        timestamp = datetime.now().strftime("%H:%M:%S")
        self.log_text.insert(tk.END, f"[{timestamp}] {message}\n")
        self.log_text.see(tk.END)

    def add_tag(self, tag_text=None):
        if tag_text is None:
            tag_text = self.tag_entry.get().strip()
        
        if tag_text:
            # 自动处理 # 号
            if not tag_text.startswith("#"):
                tag_text = "#" + tag_text
            if not tag_text.endswith("#"):
                tag_text = tag_text + "#"
            
            # 插入到文本框
            self.content_text.insert(tk.INSERT, f"{tag_text} ")
            
            # 如果是手动输入的，清空输入框
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
        
        # 计算居中位置
        window_width = 300
        window_height = 400
        
        # 获取主窗口位置和大小
        self.root.update_idletasks()
        root_x = self.root.winfo_x()
        root_y = self.root.winfo_y()
        root_width = self.root.winfo_width()
        root_height = self.root.winfo_height()
        
        # 计算相对主窗口居中的坐标
        pos_x = root_x + (root_width - window_width) // 2
        pos_y = root_y + (root_height - window_height) // 2
        
        manage_win.geometry(f"{window_width}x{window_height}+{pos_x}+{pos_y}")
        
        # 设为模态窗口
        manage_win.transient(self.root)
        manage_win.grab_set()
        
        # 列表区域
        list_frame = ttk.Frame(manage_win, padding="5")
        list_frame.pack(fill=tk.BOTH, expand=True)
        
        self.tags_listbox = tk.Listbox(list_frame)
        self.tags_listbox.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        scrollbar = ttk.Scrollbar(list_frame, orient=tk.VERTICAL, command=self.tags_listbox.yview)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)
        self.tags_listbox.config(yscrollcommand=scrollbar.set)
        
        for tag in self.common_tags:
            self.tags_listbox.insert(tk.END, tag)
            
        # 底部控制区
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
            self.log("Cookie文件不存在，请先使用登录工具登录")
            self.status_label.config(text="状态: Cookie文件缺失", bootstyle="danger")
            return

        try:
            with open(self.cookie_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if 'cookie_dict' in data:
                    self.cookies = data['cookie_dict']
                    # 尝试获取 XSRF-TOKEN
                    self.xsrf_token = self.cookies.get('XSRF-TOKEN', '')
                    if not self.xsrf_token:
                        # 尝试从 cookie_string 中解析
                        cookie_str = data.get('cookie_string', '')
                        if 'XSRF-TOKEN=' in cookie_str:
                            self.xsrf_token = cookie_str.split('XSRF-TOKEN=')[1].split(';')[0]
                    
                    if self.cookies:
                        self.status_label.config(text="状态: Cookies已加载", bootstyle="success")
                        self.send_btn.config(state="normal")
                        self.log("Cookies加载成功")
                    else:
                        self.log("Cookie数据为空")
                else:
                    self.log("Cookie文件格式错误")
        except Exception as e:
            self.log(f"加载Cookies失败: {str(e)}")

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
                # 保存临时文件
                temp_dir = "../temp"
                if not os.path.exists(temp_dir):
                    os.makedirs(temp_dir)
                # 使用时间戳避免文件名冲突
                timestamp = datetime.now().strftime("%Y%m%d%H%M%S%f")
                temp_path = os.path.join(temp_dir, f"paste_{timestamp}.png")
                image.save(temp_path, "PNG")
                self.add_images([temp_path])
            else:
                messagebox.showinfo("提示", "剪贴板中没有图片")
        except Exception as e:
            self.log(f"粘贴图片失败: {str(e)}")

    def on_paste(self, event):
        # 检查剪贴板是否有图片
        try:
            image = ImageGrab.grabclipboard()
            if isinstance(image, Image.Image):
                self.paste_image()
                return "break"  # 阻止默认粘贴行为
        except:
            pass
        return None  # 允许默认粘贴文本

    def add_images(self, new_paths):
        current_count = len(self.image_paths)
        new_count = len(new_paths)
        
        if current_count + new_count > 18:
            messagebox.showwarning("提示", f"图片总数不能超过18张\n当前: {current_count}, 尝试添加: {new_count}")
            # 截取可以添加的部分
            allowed_count = 18 - current_count
            if allowed_count > 0:
                self.image_paths.extend(new_paths[:allowed_count])
                self.log(f"已添加前 {allowed_count} 张图片 (达到上限)")
        else:
            self.image_paths.extend(new_paths)
            self.log(f"已添加 {new_count} 张图片")
            
        self.refresh_image_preview()

    def refresh_image_preview(self):
        # 清除旧的预览
        for widget in self.thumbs_frame.winfo_children():
            widget.destroy()
        self.preview_photos.clear()
        
        if not self.image_paths:
            self.image_label.pack(side=tk.LEFT)
            self.clear_img_btn.pack_forget()
            return
            
        self.image_label.pack_forget()
        self.clear_img_btn.pack(side=tk.RIGHT, padx=5)
        
        # 显示所有图片预览
        for idx, path in enumerate(self.image_paths):
            try:
                img = Image.open(path)
                img.thumbnail((60, 60)) # 小缩略图
                photo = ImageTk.PhotoImage(img)
                self.preview_photos.append(photo)
                
                # 图片容器
                frame = ttk.Frame(self.thumbs_frame, borderwidth=1, relief="solid")
                frame.pack(side=tk.LEFT, padx=2, pady=2)
                
                lbl = ttk.Label(frame, image=photo)
                lbl.pack()
                
                # 如果图片太多，可能需要换行或者滚动，这里简单用pack flow
                # Tkinter的pack不支持自动换行，这里作为简化，如果超过一定数量可能显示不全
                # 但考虑到18张图，60px宽，总共约1080px，窗口宽600px，确实会超出。
                # 简单优化：如果超出，就不显示预览了，或者显示“+N”
                if idx > 8: # 简单限制显示数量防止撑爆界面
                    if idx == 9:
                        ttk.Label(self.thumbs_frame, text=f"... (+{len(self.image_paths)-9})").pack(side=tk.LEFT, padx=5)
                    continue
                    
            except Exception as e:
                self.log(f"预览失败: {os.path.basename(path)}")

    def clear_images(self):
        self.image_paths = []
        self.refresh_image_preview()
        self.log("已清空所有图片")

    def upload_single_image(self, file_path):
        try:
            url = "https://www.weibo.com/ajax/statuses/uploadPicture"
            
            headers = {
                "accept": "application/json, text/plain, */*",
                "origin": "https://www.weibo.com",
                "referer": "https://www.weibo.com",
                "user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36",
                "x-requested-with": "XMLHttpRequest",
                "x-xsrf-token": self.xsrf_token
            }
            
            files = {
                'pic': ('image.png', open(file_path, 'rb'), 'image/png')
            }
            
            response = requests.post(url, headers=headers, cookies=self.cookies, files=files)
            
            if response.status_code == 200:
                data = response.json()
                if 'pic_id' in data:
                    return data['pic_id']
                elif 'data' in data and 'pic_id' in data['data']:
                    return data['data']['pic_id']
                
            self.log(f"图片上传失败 ({os.path.basename(file_path)}): {response.text}")
            return None
            
        except Exception as e:
            self.log(f"上传图片出错 ({os.path.basename(file_path)}): {str(e)}")
            return None

    def upload_images(self):
        if not self.image_paths:
            return ""
            
        uploaded_ids = []
        total = len(self.image_paths)
        
        self.log(f"开始上传 {total} 张图片...")
        
        for i, path in enumerate(self.image_paths):
            self.log(f"正在上传第 {i+1}/{total} 张: {os.path.basename(path)}")
            pid = self.upload_single_image(path)
            if pid:
                uploaded_ids.append(pid)
            else:
                self.log(f"第 {i+1} 张图片上传失败，已跳过")
                
        if not uploaded_ids:
            return None
            
        self.log(f"成功上传 {len(uploaded_ids)}/{total} 张图片")
        return ",".join(uploaded_ids)

    def send_weibo(self):
        content = self.content_text.get("1.0", tk.END).strip()
        if not content and not self.image_paths:
            messagebox.showwarning("提示", "请输入微博内容或选择图片")
            return
            
        self.send_btn.config(state="disabled")
        threading.Thread(target=self._send_thread, args=(content,), daemon=True).start()

    def _send_thread(self, content):
        try:
            # 如果有图片，先上传图片
            pic_id_str = ""
            if self.image_paths:
                pic_id_str = self.upload_images()
                if not pic_id_str and self.image_paths: # 有图片但上传全失败
                    self.root.after(0, lambda: messagebox.showerror("错误", "图片上传失败，终止发送"))
                    return

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
                "need_transcode": "1",
                "pic_id": pic_id_str
            }
            
            self.log("正在发送微博...")
            response = requests.post(url, headers=headers, cookies=self.cookies, data=data)
            
            if response.status_code == 200:
                res_json = response.json()
                if 'ok' in res_json and res_json['ok'] == 1:
                    self.root.after(0, lambda: messagebox.showinfo("成功", "微博发送成功"))
                    self.root.after(0, lambda: self.log("发送成功"))
                    self.root.after(0, lambda: self.content_text.delete("1.0", tk.END))
                    self.root.after(0, self.clear_images)
                else:
                    self.root.after(0, lambda: self.log(f"发送失败: {response.text}"))
            else:
                self.root.after(0, lambda: self.log(f"请求失败: {response.status_code}"))
                
        except Exception as e:
            self.root.after(0, lambda: self.log(f"错误: {str(e)}"))
        finally:
            self.root.after(0, lambda: self.send_btn.config(state="normal"))

if __name__ == "__main__":
    root = ttk.Window(themename="cosmo")
    app = WeiboSenderApp(root)
    root.mainloop()
